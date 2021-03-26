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
from dictmaster.stages.processor import HtmlContainerProcessor

class Plugin(BasePlugin):
    dictname = u"Foclóir Gaeilge-Béarla (Ó Dónaill, 1977)"

    def __init__(self, dirname, popts=[]):
        super(Plugin, self).__init__(dirname)
        self.stages['UrlFetcher'] = FocloirUrlFetcher(self)
        self.stages['Fetcher'] = FocloirFetcher(self)
        self.stages['Processor'] = FocloirProcessor("div.entry", self)

    def post_setup(self, cursor):
        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', [(a, FLAGS["URL_FETCHER"]) for a in ALPHA])

class FocloirUrlFetcher(UrlFetcher):
    class FetcherThread(UrlFetcher.FetcherThread):
        def filter_data(self, data, uri):
            data = data.decode("utf-8")
            d = pq(data)
            return [urllib2.quote(d(a).text()) for a in d("span.abcItem > a")]

        def parse_uri(self,uri):
            return "https://www.teanglann.ie/en/fgb/_%s"%uri

class FocloirFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data, uri):
            if data == None:
                return None
            data = data.decode("utf-8")
            if 'No matches found.' in data:
                return None
            container = "div.exacts"
            doc = pq(data)
            if len(doc(container)) == 0: return None
            else: return doc(container).html()

        def parse_uri(self, uri):
            return "https://www.teanglann.ie/en/fgb/%s"%uri

class FocloirProcessor(HtmlContainerProcessor):
    def do_pre_html(self, data):
        regex = [
            [r'[\s]*:([^\s])', r': \1']
        ]
        for r in regex: data = re.sub(r[0], r[1], data)
        return data

    def do_html_term(self, doc):
        term = doc("span.title").eq(0).text().strip()
        no = doc("span.title + span.x")
        if len(no) > 0:
            term = "%s (%s)" % (term, no.eq(0).text().strip())
        regex = [
            [r", *$",r""]
        ]
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_definition(self, dt_html, html, term):
        doc = pq(html)

        # links to related articles
        fun = lambda el, val: "bword://%s" % doc(el).text().strip(". ")
        doc_replace_attr(doc, "span.clickable", "onclick", fun, force=True)
        doc_rewrap_els(doc, "span.s.clickable", "<a/>", transfer_attr=[("onclick","href")])

        # simple inline styles
        doc_rewrap_els(doc, "span.title", "<b/>", css=[("color", "#930")])
        doc_rewrap_els(doc, "span.x", "<sup/>")
        doc_rewrap_els(doc, "span.b", "<b/>")
        doc_rewrap_els(doc, "span.i", "<i/>")
        doc_rewrap_els(doc, "span.l", "<i/>")
        doc_rewrap_els(doc, "span.g", "<i/>", css=[("color","#060")])

        # cleanup
        doc_strip_els(doc, "span:not([style])", block=False)
        doc("*").removeAttr("class")

        return doc.html()

