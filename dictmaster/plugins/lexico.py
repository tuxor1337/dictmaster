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
from string import ascii_lowercase as ALPHA
from pyquery import PyQuery as pq
from lxml import etree

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

from dictmaster.util import FLAGS
from dictmaster.replacer import *
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.urlfetcher import UrlFetcher
from dictmaster.stages.processor import HtmlAXProcessor

class Plugin(BasePlugin):
    dictname = u"Lexico English Dictionary Online (©Oxford)"

    def __init__(self, dirname, popts=[]):
        super(Plugin, self).__init__(dirname)
        fetcher_kwargs = dict(sleep=(240.0, 360.0), threadcnt=1)
        self.stages['UrlFetcher'] = LexicoUrlFetcher(self, **fetcher_kwargs)
        self.stages['Fetcher'] = LexicoFetcher(self, **fetcher_kwargs)
        self.stages['Processor'] = LexicoProcessor("div.entryHead", self)

    def post_setup(self, cursor):
        max_n_pages = 110
        alph_ext = "0" + ALPHA
        alph_pages = [f"{a}/{n}" for a in alph_ext for n in range(1, max_n_pages + 1)]
        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', [(ap, FLAGS["URL_FETCHER"]) for ap in alph_pages])

class LexicoUrlFetcher(UrlFetcher):
    class FetcherThread(UrlFetcher.FetcherThread):
        def filter_data(self, data, uri):
            if data is None or len(data) == 0:
                return []
            if not isinstance(data, str):
                data = data.decode("utf-8")
            if '<div class="error-page"' in data:
                return []
            d = pq(data)
            return [urllib2.quote(d(li).text()) for li in d("div.textBlock > ul > li")]

        def parse_uri(self, uri):
            return f"https://www.lexico.com/list/{uri}"

class LexicoFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data, uri):
            if data == None:
                return None
            data = data.decode("utf-8")
            if 'No exact matches found for' in data:
                return None
            container = "div.entryWrapper"
            doc = pq(data)
            doc("svg").remove()
            doc("h1").remove()
            doc("div.breadcrumbs").remove()
            doc("div.homographs").remove()
            doc("div.socials").remove()
            doc("a.speaker").remove()
            doc("a:empty").remove()
            if len(doc(container)) == 0: return None
            else: return doc(container).html()

        def parse_uri(self, uri):
            return f"https://www.lexico.com/definition/{uri}"

class LexicoProcessor(HtmlAXProcessor):
    def do_pre_html(self, data):
        regex = []
        for r in regex: data = re.sub(r[0], r[1], data)
        return data

    def do_html_term(self, doc):
        no = doc("h2.hwg sup")
        no = no.eq(0).text().strip() if len(no) > 0 else None
        term = doc(doc("h2.hwg > span").eq(0)).clone()
        term("sup").remove()
        term = term.text().strip()
        if no is not None:
            term = f"{term} ({no})"
        regex = []
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_definition(self, dt_html, html, term):
        doc = pq(pq(dt_html).html() + pq(html).html())
        doc("a[href='/']").remove()
        doc("a[href='/definition']").remove()
        doc("a[onclick]:not([href])").remove()
        doc("button").remove()
        doc("div.examples").remove()
        doc("div.synonyms").remove()
        doc("p.associatedTranslation").remove()
        doc("h3:empty").remove()

        doc_strip_els(doc, "p", block=True)

        doc_rewrap_els(doc, "ul.semb > li", "<p/>")
        doc_rewrap_els(doc, "ol.subSenses > li", "<p/>")
        doc_rewrap_els(doc, "h2", "<b/>", suffix=" ")
        doc_rewrap_els(doc, "h3.pronunciations", "<span/>", suffix=" ",
                       css=[("font-family", "monospace")])
        doc_rewrap_els(doc, "h3.phrases-title", "<p/>")
        doc_rewrap_els(doc, "strong.phrase", "<b/>",
                       css=[("font-family", "serif")])
        doc_rewrap_els(doc, "strong", "<b/>")
        doc_rewrap_els(doc, "em", "<i/>")
        doc_rewrap_els(doc, "div.ex", "<p/>")
        doc_rewrap_els(doc, "span.grammatical_note", "<i/>",
                       prefix="[", suffix="]", css=[("color", "#27a058")])
        doc_rewrap_els(doc, "span.sense-regions", "<i/>",
                       css=[("color", "#27a058")])
        doc_rewrap_els(doc, "span.inflection-text", "<span/>",
                       css=[("text-transform", "lowercase")])
        doc_rewrap_els(doc, "span.pos-inflections", "<b/>",
                       prefix=" (", suffix=")")
        doc_rewrap_els(doc, "span.form-groups", "<span/>",
                       prefix="(", suffix=")")
        doc_rewrap_els(doc, "span.pos", "<b/>",
                       css=[("color", "#f15a24"),
                            ("text-transform", "uppercase")])
        doc_rewrap_els(doc, "span.iteration,span.subsenseIteration", "<b/>",
                       suffix=" ")

        doc_replace_attr_re(doc, "a[href^='/definition/']", "href",
                            (r"/definition/(.*)", r"bword://\1"))

        # cleanup
        doc_strip_els(doc, "h3", block=True)
        doc_strip_els(doc, "header", block=True)
        doc_strip_els(doc, "section", block=True)
        doc_strip_els(doc, "ul.semb", block=True)
        doc_strip_els(doc, "ol.subSenses", block=True)
        doc_strip_els(doc, "div[id]", block=True)
        doc_strip_els(doc, "div.exg", block=True)
        doc_strip_els(doc, "div.hwg", block=True)
        doc_strip_els(doc, "div.variant", block=True)
        doc_strip_els(doc, "span:not([style])", block=False)
        doc("*").removeAttr("class")

        return doc.html()

