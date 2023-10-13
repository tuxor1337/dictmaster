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

import json
import re
from string import ascii_lowercase as ALPHA
import urllib.parse

from lxml import etree
from pyquery import PyQuery as pq
import sqlite3

from dictmaster.util import FLAGS, words_to_db
from dictmaster.replacer import *
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.urlfetcher import UrlFetcher
from dictmaster.stages.processor import HtmlContainerProcessor


class Plugin(BasePlugin):
    dictname = "Deutsches Wörterbuch von Jacob Grimm und Wilhelm Grimm (¹DWB)"

    def __init__(self, dirname, popts=[]):
        super().__init__(dirname)
        self.stages['UrlFetcher'] = DwbUrlFetcher(self)
        self.stages['Fetcher'] = DwbFetcher(self)
        self.stages['Processor'] = DwbProcessor("div.dwb-entry", self)

    def post_setup(self, cursor):
        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', [
            ("https://www.dwds.de/dwds_static/wb/dwb-headwords.json", FLAGS["URL_FETCHER"]),
        ])

class DwbUrlFetcher(UrlFetcher):
    class FetcherThread(UrlFetcher.FetcherThread):
        def filter_data(self, data, uri):
            data = json.loads(data)
            wordlist = {}
            for w in data.keys():
                m = re.match(r"^https://www\.dwds\.de/wb/dwb/([^/]+)#(.*)$", data[w])
                assert m is not None
                wid = m.group(2)
                if wid in wordlist:
                    continue
                else:
                    wordlist[wid] = m.group(1)
            return list(wordlist.values())

class DwbFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data, uri):
            if data is None or data == "":
                return None
            data = data.decode("utf-8")
            container = "div.col-md-7"
            doc = pq(data)
            if len(doc(container)) == 0:
                return None
            else:
                return doc(container).html()

        def parse_uri(self, uri):
            return f"https://www.dwds.de/wb/dwb/{uri}"

class DwbProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        return doc("div.dwb-head span.dwb-form").eq(0).text().rstrip(", ")

    def do_html_alts(self, dt_html, doc, term):
        return [term] + [
            doc(elt).text().rstrip(", ")
            for elt in doc("div.dwb-head span.dwb-form")
        ]

    def do_html_definition(self, dt_html, html, term):
        doc = pq(html)
        doc = doc(doc("div.dwb-sense > div.dwb-sense-content").eq(0))

        # italic style spans
        doc("i.bi-arrow-up-right").remove()
        doc_rewrap_els(doc, "span.dwb-italics", "<i/>")

        # paragraphs for alternative meanings
        doc_rewrap_els(doc, "div.dwb-sense-n", "<b/>")
        doc_strip_els(doc, "div.dwb-sense > div.dwb-sense-content", block=False)
        doc_strip_els(doc, "div.dwb-sense:first-child", block=False)
        doc_rewrap_els(doc, "div.dwb-sense", "<div/>")

        # author names for sources/quotes
        doc_strip_els(doc, "span.dwb-author a", block=False)
        doc_rewrap_els(doc, "span.dwb-author", "<span/>", css=[("font-variant", "small-caps")])

        # links to related articles
        regex = (r"^/wb/dwb/(.+)$", r"bword://\1")
        doc_replace_attr_re(doc, "a", "href", regex)

        # blockquotes
        doc_rewrap_els(doc, "div.dwb-cit > div.dwb-bibl", "<p/>", css=[
            ("font-style", "normal"),
            ("font-size", "x-small"),
            ("text-align", "right"),
        ])
        doc_rewrap_els(doc, "div.dwb-cit", "<blockquote/>")

        # cleanup
        doc("*").removeAttr("class")
        doc("*").removeAttr("title")

        return f"<b>{term},</b> {doc.html().strip()}"
