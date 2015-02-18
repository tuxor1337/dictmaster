# -*- coding: utf-8 -*-

import os
import re
import shutil

from dictmaster.util import CancelableThread
from pyglossary.glossary import Glossary

from pyquery import PyQuery as pq
from lxml import etree

class Processor(CancelableThread):
    input_directory = ""
    output = []
    plugin = None

    _curr_f = ""

    def __init__(self, plugin):
        super(Processor, self).__init__()
        self.input_directory = os.path.join(plugin.output_directory, "raw")
        self.plugin = plugin

    def progress(self):
        if self._curr_f == "" or self._canceled: return "Sleeping..."
        return "Processing... {}: {}".format(
            os.path.basename(self._curr_f),
            len(self.output)
        )

    def run(self):
        for f in sorted(os.listdir(self.input_directory)):
            self._curr_f = os.path.join(self.input_directory, f)
            self.process()
            if self._canceled: break
        self.plugin.data = self.output

    def process(self):
        with open(self._curr_f, "r") as dictfile:
            for line in dictfile.readlines():
                term, definition = line.decode("utf-8").split("=")
                self.append(term.strip(), definition.strip())

    def append(self, term, definition, alts=[]):
        term, definition = term.strip(), definition.strip()
        if term == "" or definition == "": return
        if len(alts) == 0:
            m = re.search(r"^(.*)\([0-9]+\)$", term)
            if m != None: alts = [m.group(1),m.group(1).lower()]
        self.output.append((term, definition, {'alts': alts }))

class BglProcessor(Processor):
    def __init__(self, plugin, bgl_file):
        super(BglProcessor, self).__init__(plugin)
        self._curr_f = bgl_file

    def run(self):
        self.process()
        self.plugin.data = self.output

    def process(self):
        g = Glossary()
        res_dirname = os.path.join(self.plugin.output_directory, "res")
        g.read(self._curr_f, verbose=0, resPath=res_dirname)
        if self.plugin.dictname == None:
            self.plugin.dictname = g.getInfo("bookname")
        for d in g.data:
            if self._canceled: break
            term, definition, alts = d
            term = term.decode("utf-8")
            if "alts" in alts: alts = [a.decode("utf-8") for a in alts["alts"]]
            else: alts = None
            definition = self.do_bgl_definition(definition, term)
            self.append(term, definition, alts)

    def do_bgl_definition(self, definition, term):
        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(definition, parser=parser))
        for font_el in doc("font"):
            replacement = doc("<span/>").html(doc(font_el).html())
            if doc(font_el).attr("color"):
                replacement.css("color", doc(font_el).attr("color"))
            if doc(font_el).attr("face"):
                replacement.css("font-family", doc(font_el).attr("face"))
            if doc(font_el).attr("size"):
                fontsize = doc(font_el).attr("size")
                if fontsize[0] in "+-": fontsize = float(fontsize.strip("+"))+2
                else: fontsize = float(fontsize)
                fontsize = int(min(7, max(fontsize,1))-1)
                replacement.css("font-size",
                    ["0.8","1","1.3","1.5","2","2.7","4"][fontsize]+"em")
            doc(font_el).replaceWith(replacement.outerHtml())
        return doc.outerHtml()

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
        with open(self._curr_f, "r") as dictfile:
            for line in dictfile.readlines():
                if self._canceled: break
                line = line.decode("utf-8").strip().replace(u"\u2028","")
                self.do_line(line)

    def do_line(self, line):
        entries = []
        if line.startswith("#") or line == "": return
        fields = line.split(self.fieldSplit)[:2]
        if len(fields) != 2:
            print("Invalid file structure.")
            print line
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
        else: subfields = [fields[0], fields[1]]
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

    def __init__(self, plugin, charset="utf-8"):
        super(HtmlProcessor, self).__init__(plugin)
        self._charset = charset

    def process(self):
        with open(self._curr_f, "r") as html_file:
            string = html_file.read()
            encoded_str = self.do_pre_html(string)
            if encoded_str.strip() == "": return
            parser = etree.HTMLParser(encoding=self._charset)
            doc = pq(etree.fromstring(encoded_str, parser=parser))
            self.do_html(doc)

    " Initialize these to trivial functions: "
    def do_pre_html(self, encoded_str): return encoded_str
    def do_html(self, doc): self.append(doc("dt").eq(0), doc("dd").eq(0))
    def do_html_term(self, dt): return ""
    def do_html_alts(self, dd, term): return []
    def do_html_definition(self, dd, term): return ""

    def append(self, dt, dd):
        term = self.do_html_term(dt)
        alts = self.do_html_alts(dd, term)
        definition = self.do_html_definition(dd, term)
        Processor.append(self, term, definition, alts)

class HtmlABProcessor(HtmlProcessor):
    AB = ("dt", "dd")

    def __init__(self, AB, plugin, charset="utf-8"):
        super(HtmlABProcessor, self).__init__(plugin, charset)
        self.AB = AB

    def do_html(self, doc):
        dt = doc(self.AB[0])
        while len(dt) > 0:
            if self._canceled: break
            dt, dd = dt.eq(0), dt.nextAll(self.AB[1]).eq(0)
            HtmlProcessor.append(self, doc(dt), doc(dd))
            dt = dt.nextAll(self.AB[0])

class HtmlContainerProcessor(HtmlProcessor):
    container_tag = "div"
    singleton = False

    def __init__(self, container_tag, plugin, charset="utf-8", singleton=False):
        super(HtmlContainerProcessor, self).__init__(plugin, charset)
        self.container_tag, self.singleton = container_tag, singleton

    def do_html(self, doc):
        if self.singleton and self.container_tag == "": contlist = [doc]
        else: contlist = doc(self.container_tag)
        for container in contlist:
            if self._canceled: break
            self.append(doc(container), doc(container))
            if self.singleton: break

