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

import logging
import os
import sys
import glob

from pyquery import PyQuery as pq
from lxml import etree

from pyglossary.glossary import Glossary

from dictmaster.util import FLAGS, mkdir_p
from dictmaster.plugin import BasePlugin
from dictmaster.stages.processor import Processor

class Plugin(BasePlugin):
    g_data = []
    def __init__(self, dirname, popts=[]):
        if len(popts) != 1 or not os.path.exists(popts[0]):
            patterns = ["*.bgl","*.BGL"]
            bgl_files = sum(map(glob.glob, patterns), [])
            if len(bgl_files) > 0:
                print("Assuming you mean %s" % bgl_files[0])
                popts = [bgl_files[0]]
            else:
                sys.exit("Provide full path to (existing) BGL file!")
        self.bgl_file = popts[0]
        super(Plugin, self).__init__(dirname)

    def post_setup(self, cursor):
        # this command should only be called once
        if Glossary.plugins == {}:
            Glossary.init()

        # suppress overly verbose WARNING log messages from pyglossary
        logging.getLogger("pyglossary").setLevel(logging.ERROR)

        g = Glossary()
        res_dirname = os.path.join(self.output_directory, "res")
        mkdir_p(res_dirname)
        g.read(self.bgl_file)
        self.g_data = []
        self.dictname = g.getInfo("bookname")

        proc_tasks = []
        for entry in g._data:
            if not entry.isData():
                self.g_data.append(entry)
                proc_tasks.append((len(self.g_data) - 1, FLAGS["MEMORY"]))
                continue
            if entry.getFileName() != "icon1.ico":
                # the icon is never used anyway
                entry.save(res_dirname)

        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', proc_tasks)
        self.stages['Processor'] = BglProcessor(self)

class BglProcessor(Processor):
    def data_from_memory(self):
        entry = self.plugin.g_data[int(self._curr_row["uri"])]
        self._curr_row["data"] = (
            entry.l_word,
            entry if entry.isData() else entry.defi,
            entry.defiFormat,
        )

    def process(self):
        terms, definition, format = self._curr_row["data"]

        if isinstance(terms, str):
            terms = [terms]
        term = terms[0]
        alts = terms[1:]

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
