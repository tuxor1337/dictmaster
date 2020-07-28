# -*- coding: utf-8 -*-
#
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

from dictmaster.util import FLAGS
from dictmaster.replacer import *
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.urlfetcher import UrlFetcher
from dictmaster.stages.processor import HtmlContainerProcessor

class Plugin(BasePlugin):
    dictname = u"Online Etymology Dictionary, ©Douglas Harper/etymonline.com"

    def __init__(self, dirname, popts=[]):
        super(Plugin, self).__init__(dirname)
        self.stages['UrlFetcher'] = EtymonlineUrlFetcher(self)
        self.stages['Fetcher'] = EtymonlineFetcher(self)
        self.stages['Processor'] = EtymonlineProcessor("div.word--C9UPa", self)

    def post_setup(self, cursor):
        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', [(a, FLAGS["URL_FETCHER"]) for a in ALPHA])

class EtymonlineUrlFetcher(UrlFetcher):
    class FetcherThread(UrlFetcher.FetcherThread):
        def filter_data(self, data, uri):
            d = pq(data)
            a = d("li.ant-pagination-item a")[-1]
            new = d(a).attr("href")
            no = int(re.sub("^.*page=([0-9]+)&q=[a-z]$", r"\1", new))
            pattern = re.sub("^.*(page=)([0-9]+)(&q=[a-z])$", r"\1%d\3", new)
            return [pattern % i for i in range(1,no+1)]

        def parse_uri(self,uri):
            return "http://www.etymonline.com/search?q=%s"%uri

class EtymonlineFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data, uri):
            if data == None:
                return None
            data = data.decode("utf-8")
            if 'No results were found for' in data:
                return None
            container = "div.ant-col-xs-24"
            doc = pq(data)
            if len(doc(container)) == 0: return None
            else: return doc(container).html()

        def parse_uri(self, uri):
            return "http://www.etymonline.com/search?%s"%uri

class EtymonlineProcessor(HtmlContainerProcessor):
    def do_pre_html(self, data):
        data = data.replace("&#13;", "")
        data = data.replace("\xa0", " ")
        regex = [
            [r'\[([^\]]+)\]\n</blockquote>',
             r'<p class="src">[\1]</p></blockquote>'],
            [r'([^=])"([^> ][^"]*[^= ])"([^>])',
             r'\1<span class="meaning">"\2"</span>\3']
        ]
        for r in regex: data = re.sub(r[0], r[1], data)
        return data

    def do_html_term(self, doc):
        return doc("a.word__name--TTbAA").eq(0).text().strip()

    def do_html_alts(self, doc, term):
        regex = [
            [r" +\([^\)]+\)$",r""],
        ]
        for r in regex:
            term_stripped = re.sub(r[0], r[1], term)
        return [term, term_stripped]

    def do_html_definition(self, html, term):
        doc = pq(html)("object > section")
        doc("ins").remove()

        # links to related articles
        regex = (r"^[^\?]+\?term=([^&]+)&.*$", r"bword://\1")
        doc_replace_attr_re(doc, "a", "href", regex)

        # simple inline styles
        doc_rewrap_els(doc, "span.foreign", "<i/>")
        doc_rewrap_els(doc, "span.meaning", "<span/>", css=[("color","#47A")])

        # blockquotes
        doc_rewrap_els(doc, "blockquote p.src", "<p/>",
            css=[("font-style","normal"),
                 ("font-size","x-small"),
                 ("text-align","right"),])
        doc_strip_els(doc, "blockquote p.src span.meaning", block=False)

        # cleanup
        doc_rewrap_els(doc, "p", "<p/>", remove_empty=True)
        doc("*").removeAttr("class")

        return "<b>%s</b> %s" % (term, doc.html())

