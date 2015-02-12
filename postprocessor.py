# -*- coding: utf-8 -*-

import sys
import os
import shutil
import importlib
import zipfile

import re
import codecs

import threading
import time

from pyquery import PyQuery as pq
from lxml import etree

from pyglossary.glossary import Glossary
from editor import glossEditor
from util import mkdir_p

THREAD_CNT = 3
DEF_VERBOSITY = True

class ppThread(object):
    def __init__(self, threadno, plugin, file_list, dirname):
        self.threadno = threadno
        self.output = []
        self.dirname = dirname
        self.plugin = plugin
        self.userscript = importlib.import_module("plugins.%s.custom" % self.plugin["name"])
        self.files = file_list
        self.verbose = DEF_VERBOSITY

    def run(self):
        for i in range(self.threadno, len(self.files), THREAD_CNT):
            f = self.files[i]
            if self.verbose:
                sys.stdout.write("\r\033[%dC%s %06d:" \
                    % (
                        self.threadno*23 + 1,
                        u"{:<7}".format(f.decode("utf-8")[0:7]),
                        len(self.output)
                      )
                )
            sys.stdout.flush()
            if "html" in self.plugin["format"]:
                self.output.extend(self._do_html(
                    "%s/%s" % (self.dirname, f)
                ))
            elif "bgl" in self.plugin["format"]:
                self.output.extend(self._do_bgl(
                    "%s/%s" % (self.dirname, f)
                ))
            elif "dictfile" in self.plugin["format"]:
                self.output.extend(self._do_dictfile(
                    "%s/%s" % (self.dirname, f)
                ))

    def _do_print_progress_term(self, datalen, term):
        if datalen % 25 == 0 and self.verbose:
            sys.stdout.write("\r\033[%dC%s" \
                % (self.threadno*23 + 16, u"{:<6}".format(term[0:6])))
            sys.stdout.flush()

    def _do_data_append(self, term, definition, data, alts=[]):
        if len(alts) == 0:
            m = re.search(r"^(.*)\([0-9]+\)$", term)
            if m != None:
                alts = [m.group(1),m.group(1).lower()]
        data.append((term, definition, {'alts': alts }))
        self._do_print_progress_term(len(data)-1, term)

    def _do_bgl(self, filename):
        data = []
        g = Glossary()
        g.read(filename, verbose=0)
        if "dictname" not in self.plugin:
            self.plugin["dictname"] = g.getInfo("bookname")
        dirname = "%s_files" % filename
        if os.path.exists(dirname):
            res_dirname = "data/%s/res" % self.plugin["name"]
            if os.path.exists(res_dirname):
                shutil.rmtree(res_dirname)
            shutil.move(dirname, res_dirname)
        for d in g.data:
            term, definition, alts = d
            term = term.decode("utf-8")
            if "alts" in alts:
                alts = alts["alts"]
                for i in range(len(alts)):
                    alts[i] = alts[i].decode("utf-8")
            else:
                alts = None
            definition = self._do_bgl_definition(definition, term)
            self._do_data_append(
                term, definition, data, alts
            )
        return data

    def _do_bgl_definition(self, definition, term):
        bgldef_opts = self.plugin["format"]["bgl"]["definition"]
        if "bytereplace" in bgldef_opts:
            for r in bgldef_opts["bytereplace"]:
                definition = definition.replace(r[0],r[1])

        definition = definition.decode("utf-8")
        if "regex" in bgldef_opts:
            for r in bgldef_opts["regex"]:
                definition = re.sub(r[0],r[1], definition)

        if "no_font_tags" in bgldef_opts:
            encoded_str = definition.encode("utf-8")
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(encoded_str, parser=parser))
            for font_el in doc("font"):
                replacement = doc("<span/>").html(doc(font_el).html())
                if doc(font_el).attr("color"):
                    replacement.css("color", doc(font_el).attr("color"))
                if doc(font_el).attr("face"):
                    replacement.css("font-family", doc(font_el).attr("face"))
                if doc(font_el).attr("size"):
                    fontsize = doc(font_el).attr("size")
                    if fontsize[0] in "+-":
                        fontsize = float(fontsize.strip("+")) + 2
                    else:
                        fontsize = float(fontsize)
                    fontsize = int(min(7, max(fontsize,1))-1)
                    replacement.css("font-size",
                        ["0.8","1","1.3","1.5","2","2.7","4"][fontsize]+"em")
                doc(font_el).replaceWith(replacement.outerHtml())
            definition = doc.outerHtml()

        if "userscript" in bgldef_opts:
            definition = self.userscript.process_bgl_definition(definition, term)

        return definition

    def _do_dictfile(self, filename):
        dictfile_opts = self.plugin["format"]["dictfile"]
        data = []
        with open(filename, "r") as dictfile:
            for line in dictfile.readlines():
                line = line.decode("utf-8").strip().replace(u"\u2028","")
                self._do_dictfile_append(line, data)
        return data

    def _do_dictfile_append(self, line, data):
        dictfile_opts = self.plugin["format"]["dictfile"]
        entries = []

        if "userscript" in dictfile_opts:
            entries = self.userscript.process_dictfile_line(line)
        else:
            entries = self._do_dictfile_line(line)

        for entry in entries:
            self._do_data_append(
                entry["term"], entry["definition"],
                data, entry["alts"]
            )

    def _do_dictfile_line(self, line):
        dictfile_opts = self.plugin["format"]["dictfile"]
        entries = []
        if line.startswith("#") or line == "":
            return entries

        fields = line.split(dictfile_opts["fieldSplit"])[:2]
        if len(fields) != 2:
            print("Invalid file structure.")
            print line
            return entries

        if "flipCols" in dictfile_opts and dictfile_opts["flipCols"]:
            fields[0], fields[1] = fields[1], fields[0]

        subfields = [ [], [] ]
        if "subfieldSplit" in dictfile_opts:
            subfields[0] = fields[0].split(dictfile_opts["subfieldSplit"])
            subfields[1] = fields[1].split(dictfile_opts["subfieldSplit"])
            if len(subfields[0]) != len(subfields[1]):
                print("Invalid unbalanced entry.")
                print(line)
                return entries
        else:
            subfields[0] = [fields[0]]
            subfields[1] = [fields[1]]

        for i in range(len(subfields[0])):
            subfields[0][i] = subfields[0][i].strip()
            subfields[1][i] = subfields[1][i].strip()
            if len(subfields[0][i]) == 0 and len(subfields[1][i]) == 0:
                print("Empty pair.")
                print(line)
                continue
            if len(subfields[0][i]) == 0:
                subfields[0][i] = "__"
            if len(subfields[1][i]) == 0:
                subfields[1][i] = "__"

        term = subfields[0][0]
        if term == "__":
            try:
                term = subfields[0][1]
            except:
                print("What's this?")
                print(line)
                return entries
        if "subsubfieldSplit" in dictfile_opts:
            syns = term.split(dictfile_opts["subsubfieldSplit"])
            term = syns[0].strip()
        definition = ""
        alts = subfields[0][1:] if "subsubfieldSplit" not in dictfile_opts else []
        for subfield in zip(subfields[0], subfields[1]):
            definition += "<dt>%s</dt><dd>%s</dd>" % (subfield[0], subfield[1])
            if "subsubfieldSplit" in dictfile_opts:
                syns = subfield[0].split(dictfile_opts["subsubfieldSplit"])
                if syns[0] == term:
                    syns = syns[1:]
                alts.extend([syn.strip() for syn in syns])
        term = re.sub(r" *(\{[^\}]*\}|\[[^\]]*\])", "", term)
        alts = [re.sub(r" *(\{[^\}]*\}|\[[^\]]*\])", "", alt) for alt in alts]
        entries.append({
            "term": term,
            "definition": definition,
            "alts": alts
        })

        return entries

    def _do_html(self,filename):
        html_opts = self.plugin["format"]["html"]
        data = []
        with open(filename, "r") as html_file:
            encoded_str = html_file.read()
            if "pre_parser" in html_opts and "regex" in html_opts["pre_parser"]:
                for regex in html_opts["pre_parser"]["regex"]:
                    encoded_str = re.sub(regex[0],regex[1], encoded_str)
            if "codec" in html_opts:
                parser = etree.HTMLParser(encoding=html_opts["codec"])
            else:
                parser = etree.HTMLParser()
            doc = pq(etree.fromstring(encoded_str, parser=parser))
            if "alternating" in html_opts:
                a = html_opts["alternating"]["a"]
                b = html_opts["alternating"]["b"]
                dt = doc(a)
                while len(dt) > 0:
                    dt, dd = dt.eq(0), dt.nextAll(b).eq(0)
                    self._do_html_data_append(dt, dd, data)
                    dt = dt.nextAll(a)
            elif "container_iter" in html_opts:
                for container in doc(html_opts["container_iter"]):
                    self._do_html_data_append(
                        doc(container), doc(container), data
                    )
            elif "singleton" in html_opts:
                if html_opts["singleton"] != "":
                    container = doc(html_opts["singleton"])
                else:
                    container = doc
                self._do_html_data_append(
                    doc(container), doc(container), data
                )
        return data

    def _do_html_data_append(self, dt, dd, data):
        html_opts = self.plugin["format"]["html"]
        term = self._do_html_element(dt, html_opts["term"])
        alts = self._do_html_alts(dd, term)
        definition = ""
        if not term.strip():
            if len(data) == 0:
                return
            if "greedy" in html_opts:
                term, definition, oldalts = data.pop()
                alts.extend(oldalts["alts"] if oldalts["alts"] else [])
        definition += self._do_html_element(dd, html_opts["definition"], term)
        self._do_data_append(term, definition, data, alts)

    def _do_html_alts(self, dd, term):
        html_opts = self.plugin["format"]["html"]
        d = pq(dd)
        alts = []
        if "alts" in html_opts:
            for tag,regex in html_opts["alts"]:
                for hw in d.find(tag):
                    candidate = d(hw).text().strip()
                    if "alts_lower" in html_opts:
                        candidate = candidate.lower()
                    for r in regex:
                        candidate = re.sub(r[0],r[1],candidate)
                    candidate = candidate.strip()
                    if candidate != term and candidate != "":
                        alts.append(candidate)
        return alts

    def _do_html_element(self, html, rule, term=""):
        result = ""
        if "attr" in rule:
            if "target" not in rule["attr"]:
                target = html
            else:
                try:
                    target = html.find(rule["attr"]["target"])
                except:
                    print html.html()
                    sys.exit()
            result = target.attr(rule["attr"]["key"]).strip()

        if "text_content" in rule:
            if rule["text_content"] == "":
                target = html
            else:
                target = html.find(rule["text_content"]).eq(0)
            result = target.text().strip()
            html = result

        if "userscript" in rule:
            result = self.userscript.process_html_element(html, term)

        if "regex" in rule:
            for regex in rule["regex"]:
                result = re.sub(regex[0], regex[1], result)

        if "lower" in rule:
            result = result.lower()
        return result

class Postprocessor(object):
    def __init__(self, plugin):
        self.plugin = plugin
        self.userscript = importlib.import_module("plugins.%s.custom" % self.plugin["name"])
        self.data = []

    def run(self):
        dirname = "data/%s/raw" % self.plugin["name"]
        if "zip" in self.plugin["format"]:
            if os.path.exists(dirname):
                shutil.rmtree(dirname)
            zdirname = "data/%s/zip" % self.plugin["name"]
            for zfile in os.listdir(zdirname):
                z = zipfile.ZipFile("%s/%s" % (zdirname, zfile))
                for n in z.namelist():
                    dest = os.path.join(dirname, n)
                    destdir = os.path.dirname(dest)
                    mkdir_p(destdir)
                    if not os.path.isdir(dest):
                        zdata = z.read(n)
                        f = open(dest, 'w')
                        f.write(zdata)
                        f.close()
                z.close()
            if "userscript" in self.plugin["format"]["zip"]:
                self.userscript.post_unzip(dirname)

        file_list = sorted(os.listdir(dirname))
        pptList = []
        for j in range(THREAD_CNT):
            ppt = ppThread(j, self.plugin, file_list, dirname)
            pptList.append(ppt)
            t = threading.Thread(target=ppt.run)
            t.daemon = True
            t.start()

        while threading.active_count() > 1:
            time.sleep(0.2)

        for ppt in pptList:
            self.data.extend(ppt.output)

        sys.stdout.write("\r\n")

    def editor(self):
        g = Glossary()
        g.data = self.data
        if "dictname" in self.plugin:
            g.setInfo("bookname", self.plugin["dictname"])
        ed = glossEditor(g, self.plugin, "data/%s/db.sqlite" % self.plugin["name"])
        return ed

