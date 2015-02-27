# -*- coding: utf-8 -*-

import os
import sys

from pyquery import PyQuery as pq
from lxml import etree

from pyglossary.glossary import Glossary

from dictmaster.util import FLAGS
from dictmaster.pthread import PluginThread
from dictmaster.postprocessor import Processor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    g_data = []
    def __init__(self, popts, dirname):
        self.bgl_file = popts
        if not os.path.exists(self.bgl_file):
            sys.exit("Provide full path to (existing) BGL file!")
        super(Plugin, self).__init__(popts, dirname)

    def run(self):
        g = Glossary()
        res_dirname = os.path.join(self.output_directory, "res")
        g.read(self.bgl_file, verbose=0, resPath=res_dirname)
        self.g_data = g.data
        self.dictname = g.getInfo("bookname").decode("utf-8")
        processor = BglProcessor(self)
        processor.data = self.g_data
        self._stages = [processor, Editor(self)]
        PluginThread.run(self)

    def post_setup(self, cursor):
        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', [(i, FLAGS["MEMORY"]) for i in range(len(self.g_data))])

class BglProcessor(Processor):
    def data_from_memory(self):
        self._curr_row["data"] = self.data[int(self._curr_row["uri"])]

    def process(self):
        term, definition, alts = self._curr_row["data"]
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
