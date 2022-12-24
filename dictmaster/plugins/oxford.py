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
import os
import sys

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import words_to_db
from dictmaster.replacer import *
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.processor import HtmlAXProcessor

POPTS_DEFAULT = ["thirdparty/wordlists/eng/oxford.txt"]

class Plugin(BasePlugin):
    dictname = "Oxford Dictionaries Online - British & World English"

    def __init__(self, dirname, popts=POPTS_DEFAULT):
        if len(popts) == 0 or not os.path.exists(popts[0]):
            sys.exit("Provide full path to (existing) word list file!")
        self.word_file = popts[0]
        super().__init__(dirname)
        self.stages['Fetcher'] = OxfordFetcher(self, threadcnt=10)
        self.stages['Processor'] = OxfordProcessor(".entryHead", self)

    def post_setup(self, cursor):
        words_to_db(self.word_file, cursor, ("utf-8", "utf-8"),)

class OxfordFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data, uri):
            if data == None: return None
            data = data.decode("utf-8")
            if 'class="entryHead' not in data: return None
            data = " ".join(data.split())
            repl = [ ]
            for r in repl: data = data.replace(r[0], r[1])
            regex = [
                [r"<![^>]*>", ""]
            ]
            for r in regex: data = re.sub(r[0], r[1], data)
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(data, parser=parser))
            doc = doc("div.entryWrapper")
            doc("svg,audio").remove()
            doc("div.socials,div.socials-mobile,div.breadcrumbs").remove()
            return doc.html()

        def parse_uri(self, uri):
            return "https://www.oxforddictionaries.com/definition/english/%s"%uri

class OxfordProcessor(HtmlAXProcessor):
    def do_html_term(self, doc):
        term = doc("h2 > span").eq(0).text().strip()
        regex = [
            [r"\s([0-9]+)$",r"(\1)"]
        ]
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_definition(self, doc, term):
        doc("script").remove()
        doc("div.examples").remove()
        doc("div.synonyms").remove()
        doc("span.pronunciations").remove()
        doc_replace_attr_re(doc, "a", "href",
                            [r"/definition/(.*)",r"bword://\1"])
        doc_rewrap_els(doc, "span.sense-regions,span.sense-registers", "<i/>",
            css=[["color","#27a058"]], textify=True,
            prefix=" ", suffix=" ")
        doc_rewrap_els(doc, "span.grammatical_note", "<i/>",
            css=[["color","#27a058"]], textify=True,
            prefix=" [", suffix="] ")
        doc_rewrap_els(doc, "span.form-groups", "<span/>",
            prefix=" (", suffix=") ")
        doc_rewrap_els(doc, "span.iteration,span.subsenseIteration", "<b/>",
            textify=True, suffix=" ")
        doc_rewrap_els(doc, "span.pos", "<b/>",
            css=[["text-transform","uppercase"],
                 ["color","#f15a24"]])
        doc_rewrap_els(doc, "span.transitivity", "<span/>",
            css=[["color","#304E70"]], textify=True, prefix=" ", suffix=" ")
        doc_rewrap_els(doc, "li", "<p/>")
        naked = [
            "div[class]",
            "div[id]",
            "ul",
            "ol",
            "section",
            "a.ipaLink",
            "h2",
            "h3.pos",
        ]
        for query in naked: doc_strip_els(doc, query)
        doc_rewrap_els(doc, "h3", "<p/>")
        doc(":empty").remove()
        doc("*").removeAttr("id").removeAttr("class")
        return doc.html()
