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
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.processor import HtmlContainerProcessor

# TODO: get full word list
# TODO: add index of indoeurop. roots: https://www.ahdictionary.com/word/indoeurop.html

POPTS_DEFAULT = ["thirdparty/wordlists/eng/ahdict.txt"]

class Plugin(BasePlugin):
    def __init__(self, dirname, popts=POPTS_DEFAULT):
        if len(popts) == 0 or not os.path.exists(popts[0]):
            sys.exit("Provide full path to (existing) word list file!")
        self.word_file = popts[0]
        super(Plugin, self).__init__(dirname)
        self.dictname = u"The American Heritage Dictionary of the English Language, Fifth Edition"
        self.stages['Fetcher'] = AhdictFetcher(self, threadcnt=12)
        self.stages['Processor'] = AhdictProcessor("td", self)

    def post_setup(self, cursor):
        words_to_db(self.word_file, cursor, ("utf-8", "utf-8"))

class AhdictFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data, uri):
            if data == None or len(data) < 2: return None
            data = data.decode("utf-8")
            if '<div id="results">' not in data \
            or '<div id="results">No word definition found</div>' in data:
                return None
            repl = [
                ["<!--end-->",""],
                # pronunciation
                ["","′"],
                ["","o͞o"],
                ["","ᴋʜ"] # AH uses ᴋʜ for x in IPA
            ]
            for r in repl: data = data.replace(r[0], r[1])
            regex = [
                [r'<div align="right">[^<]*<a[^>]*>[^<]*</a><script[^>]*>[^<]*</script></div>',""],
                [r'<div class="figure"><font[^>]*>[^<]*</font></div>',""],
                [r'<(img|a)[^>]*/>',""],
                [r'<a[^>]*(authorName=|indoeurop.html|\.wav")[^>]*>([^<]*)</a>',r"\2"],
                [r'<hr[^>]*><span class="copyright">[^<]*<br/>[^<]*</span>',""],
                [r'<(a|span)[^>]*>([ \n]*)</(span|a)>',r"\2"],
                [r' (name|target|title|border|cellspacing)="[^"]*"',r""],
                [r'<table width="100%">',"<table>"],
                [r"</?font[^>]*>",""],
                [r"([^ ])<(b|i|div)",r"\1 <\2"],
                [r"(b|i|div)>([^ ])",r"\1> \2"]
            ]
            for r in regex: data = re.sub(r[0], r[1], data)
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(data, parser=parser))
            return doc("#results").html()

        def parse_uri(self, uri):
            return "https://ahdictionary.com/word/search.html?q=%s"%uri

class AhdictProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        term = doc("b").eq(0).text().strip()
        regex = [
            [r"\xb7",""], # the centered dot
            [r" ([0-9]+)$",r"(\1)"]
        ]
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_definition(self, html, term):
        doc = pq(html)
        for a in doc("a:not([href])"): doc(a).replaceWith(doc(a).html())
        for a in doc("a"):
            if doc(a).text().strip() == "": doc(a).replaceWith(doc(a).text())
            elif "search.html" not in doc(a).attr("href"):
                doc(a).replaceWith(doc(a).html())
            else:
                href = "bword://%s" % doc(a).text().strip(". ").lower()
                doc(a).attr("href", href)
        doc("div.rtseg b").css("color","#069")
        doc("i").css("color","#940")
        doc("div.pseg > i").css("color","#900")
        doc("div.runseg > i").css("color","#900")
        for div in doc("div.ds-list"):
            doc(div).replaceWith(doc("<p/>").html(doc(div).html()).outerHtml())
        for div in doc("div.sds-list"): doc(div).replaceWith(doc(div).html())
        for span in doc("span"): doc(span).replaceWith(doc(span).html())
        doc("*").removeAttr("class")
        return doc.html().strip()

