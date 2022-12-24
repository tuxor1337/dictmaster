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

from dictmaster.replacer import doc_replace_els
from dictmaster.util import FLAGS, mkdir_p
from dictmaster.plugin import BasePlugin
from dictmaster.stages.processor import Processor

class Plugin(BasePlugin):
    g_data = []
    def __init__(self, dirname, popts=[]):
        if len(popts) != 1 or not os.path.exists(popts[0]):
            bgl_files = sum(map(glob.glob, ["*.bgl", "*.BGL"]), [])
            if len(bgl_files) > 0:
                print("Assuming you mean %s" % bgl_files[0])
                popts = [bgl_files[0]]
            else:
                sys.exit("Provide full path to (existing) BGL file!")
        self.bgl_file = popts[0]
        super().__init__(dirname)

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
        self.set_name(g.getInfo("title"), cursor=cursor)

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

        definition = self.do_bgl_definition(definition, term, alts)
        alts = self.do_bgl_alts(definition, term, alts)
        term = self.do_bgl_term(definition, term, alts)
        self.append(term, definition, alts)

    def do_bgl_definition(self, definition, term, alts):
        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(definition, parser=parser))

        def _replace_font_el(el, doc=doc):
            replacement = doc("<span/>").html(doc(el).html())
            if doc(el).attr("color"):
                replacement.css("color", doc(el).attr("color"))
            if doc(el).attr("face"):
                replacement.css("font-family", doc(el).attr("face"))
            if doc(el).attr("size"):
                fontsize_str = doc(el).attr("size")
                fontsize_float = (
                    float(fontsize_str.strip("+")) + 2
                    if fontsize_str[0] in "+-"
                    else float(fontsize_str)
                )
                fontsize_em = [
                    "0.8", "1", "1.3", "1.5", "2", "2.7", "4"
                ][int(min(7, max(fontsize_float, 1)) - 1)]
                replacement.css("font-size", f"{fontsize_em}em")
            return replacement
        doc_replace_els(doc, "font", _replace_font_el)

        return doc.outerHtml()

    def do_bgl_alts(self, definition, term, alts):
        return alts

    def do_bgl_term(self, definition, term, alts):
        return term
