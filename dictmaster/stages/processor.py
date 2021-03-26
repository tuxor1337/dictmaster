# This file is part of dictmaster
# Copyright (C) 2018  Thomas Vogt
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import sqlite3

from dictmaster.util import CancelableThread, find_synonyms, FLAGS

from pyquery import PyQuery as pq
from lxml import etree

class Processor(CancelableThread):
    plugin = None
    auto_synonyms = True
    data = None

    _conn = None
    _c = None
    _curr_row = None
    _i = 0

    def __init__(self, plugin, auto_synonyms=True):
        super(Processor, self).__init__()
        self.plugin = plugin
        self.auto_synonyms = auto_synonyms

    def reset(self):
        conn = sqlite3.connect(self.plugin.output_db)
        c = conn.cursor()
        c.execute("DELETE FROM dict")
        c.execute("DELETE FROM synonyms")
        c.execute("""UPDATE raw
                     SET flag = flag & ~?
                     WHERE flag & ? > 0""", (FLAGS["PROCESSED"],FLAGS["PROCESSED"]))
        conn.commit()
        conn.close()

    def progress(self):
        if self._curr_row == None or self._canceled: return "Sleeping..."
        return "Processing... {}: {}".format(
            self._curr_row["uri"][-7:], self._i
        )

    def run(self):
        self._conn = sqlite3.connect(self.plugin.output_db)
        self._conn.text_factory = str
        self._conn.row_factory = sqlite3.Row
        self._c = self._conn.cursor()
        self._i = self._c.execute("SELECT COUNT(*) FROM dict").fetchone()[0]
        curs = self._conn.cursor()
        flag = FLAGS["PROCESSED"] | FLAGS["DUPLICATE"] \
            | FLAGS["ZIP_FETCHER"] | FLAGS["URL_FETCHER"]
        for row in curs.execute("SELECT * FROM raw WHERE flag&?==0", (flag,)):
            self._curr_row = dict(row)
            if self._curr_row["flag"] & FLAGS["FILE"]:
                with open(self._curr_row["uri"],"rb") as f:
                    self._curr_row["data"] = f.read()
            elif self._curr_row["flag"] & FLAGS["MEMORY"]:
                self.data_from_memory()
            self.process()
            if self._canceled:
                self._c.execute('''
                    DELETE FROM dict WHERE rawid=?
                ''', (self._curr_row["id"],))
                break
            self._c.execute('''
                UPDATE raw SET flag = flag | ? WHERE id=?
            ''', (FLAGS["PROCESSED"], self._curr_row["id"]))
        self._conn.commit()
        self._conn.close()

    def data_from_memory(self):
        self._curr_row["data"] = self.data[self._curr_row["uri"]]

    def process(self): pass

    def append(self, term, definition, alts=[]):
        term, definition = term.strip(), definition.strip()
        if term == "" or definition == "": return
        if len(alts) == 0:
            m = re.search(r"^(.*)\([0-9]+\)$", term)
            if m != None: alts = [m.group(1),m.group(1).lower()]
        if self.auto_synonyms:
            alts = find_synonyms(term,definition,alts)
        alts = [a for a in set(alts) if a != term]
        self._c.execute('''
            INSERT INTO dict(word,def,rawid)
            VALUES (?,?,?)
        ''', (term, definition, self._curr_row["id"]))
        tmp_id = self._c.lastrowid
        self._c.executemany('''
            INSERT INTO synonyms(wid,syn)
            VALUES (?,?)
        ''', [(tmp_id, a) for a in alts])
        self._i += 1

class DictfileProcessor(Processor):
    def __init__(self, plugin,
            fieldSplit="\t",
            subfieldSplit=None,
            subsubfieldSplit=None,
            flipCols=False
        ):
        super(DictfileProcessor, self).__init__(plugin)
        self.fieldSplit = fieldSplit
        self.subfieldSplit = subfieldSplit
        self.subsubfieldSplit = subsubfieldSplit
        self.flipCols = flipCols

    def process(self):
        data = self._curr_row["data"].decode("utf-8")
        for line in data.split("\n"):
            if self._canceled: break
            line = line.strip().replace(u"\u2028","")
            self.do_line(line)

    def do_line(self, line):
        entries = []
        if line.startswith("#") or line == "": return
        fields = line.split(self.fieldSplit)[:2]
        if len(fields) != 2:
            print("Invalid file structure.")
            print(line)
            return
        if self.flipCols: fields[0], fields[1] = fields[1], fields[0]
        subfields = [ [], [] ]
        if self.subfieldSplit != None:
            subfields[0] = fields[0].split(self.subfieldSplit)
            subfields[1] = fields[1].split(self.subfieldSplit)
            if len(subfields[0]) != len(subfields[1]):
                print("Invalid unbalanced entry.")
                print(line)
                return
        else: subfields = [[fields[0]], [fields[1]]]
        for i in range(len(subfields[0])):
            subfields[0][i] = subfields[0][i].strip()
            subfields[1][i] = subfields[1][i].strip()
            if len(subfields[0][i]) == 0 and len(subfields[1][i]) == 0:
                print("Empty pair.")
                print(line)
                continue
            if len(subfields[0][i]) == 0: subfields[0][i] = "__"
            if len(subfields[1][i]) == 0: subfields[1][i] = "__"
        term = subfields[0][0]
        if term == "__":
            try: term = subfields[0][1]
            except:
                print("What's this?")
                print(line)
                return
        if self.subsubfieldSplit != None:
            term = term.split(self.subsubfieldSplit)[0].strip()
        definition = ""
        alts = subfields[0][1:] if self.subsubfieldSplit == None else []
        for subfield in zip(subfields[0], subfields[1]):
            definition += "<dt>%s</dt><dd>%s</dd>" % (subfield[0], subfield[1])
            if self.subsubfieldSplit != None:
                syns = subfield[0].split(self.subsubfieldSplit)
                if syns[0] == term: syns = syns[1:]
                alts.extend([syn.strip() for syn in syns])
        term = re.sub(r" *(\{[^\}]*\}|\[[^\]]*\])", "", term)
        alts = [re.sub(r" *(\{[^\}]*\}|\[[^\]]*\])", "", alt) for alt in alts]
        Processor.append(self, term, definition, alts)

class HtmlProcessor(Processor):
    _charset = ""

    def __init__(self, plugin, charset="utf-8", auto_synonyms=True):
        super(HtmlProcessor, self).__init__(plugin, auto_synonyms)
        self._charset = charset

    def process(self):
        string = self._curr_row["data"]
        if string == None: return
        encoded_str = self.do_pre_html(string)
        if encoded_str.strip() == "": return
        parser = etree.HTMLParser(encoding=self._charset)
        doc = pq(etree.fromstring(encoded_str, parser=parser))
        self.do_html(doc)

    " Initialize these to trivial functions: "
    def do_pre_html(self, encoded_str): return encoded_str
    def do_html(self, doc): self.append(doc("dt").eq(0), doc("dd").eq(0))
    def do_html_term(self, dt): return ""
    def do_html_alts(self, dt, dd, term): return []
    def do_html_definition(self, dt, dd, term): return ""

    def append(self, dt, dd):
        term = self.do_html_term(dt)
        alts = self.do_html_alts(dt, dd, term)
        definition = self.do_html_definition(dt, dd, term)
        Processor.append(self, term, definition, alts)

class HtmlABProcessor(HtmlProcessor):
    AB = ("dt", "dd")

    def __init__(self, AB, plugin, charset="utf-8", auto_synonyms=True):
        super(HtmlABProcessor, self).__init__(plugin, charset, auto_synonyms)
        self.AB = AB

    def do_html(self, doc):
        dt = doc(self.AB[0])
        while len(dt) > 0:
            if self._canceled: break
            dt, dd = dt.eq(0), dt.nextAll(self.AB[1]).eq(0)
            self.append(doc(dt), doc(dd))
            dt = dd.nextAll(self.AB[0])

class HtmlAXProcessor(HtmlProcessor):
    def __init__(self, A, plugin, charset="utf-8", auto_synonyms=True):
        super(HtmlAXProcessor, self).__init__(plugin, charset, auto_synonyms)
        self.A = A

    def do_html(self, doc):
        dt = doc(self.A)
        while len(dt) > 0:
            if self._canceled: break
            dt = dt.eq(0)
            dt_html = dt.outer_html()
            next_dt = dt.nextAll(self.A)
            if len(next_dt) > 0:
                dt.remove()
                dd = next_dt.eq(0).prevAll()
                dd_html = ''.join(doc(d).outer_html() for d in dd)
                dd.remove()
            else:
                dd = dt.nextAll()
                dd_html = ''.join(doc(d).outer_html() for d in dd)
            self.append(pq(dt_html), pq(dd_html))
            dt = next_dt

class HtmlContainerProcessor(HtmlProcessor):
    container_tag = "div"
    singleton = False

    def __init__(self,
        container_tag,
        plugin,
        charset="utf-8",
        singleton=False,
        auto_synonyms=True
    ):
        super(HtmlContainerProcessor, self).__init__(plugin, charset, auto_synonyms)
        self.container_tag, self.singleton = container_tag, singleton

    def do_html(self, doc):
        if self.singleton and self.container_tag == "": contlist = [doc]
        else: contlist = doc(self.container_tag)
        for container in contlist:
            if self._canceled: break
            self.append(doc(container), doc(container))
            if self.singleton: break

