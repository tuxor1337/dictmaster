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
            if data is None or len(data) == 0:
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
    def do_pre_html(self, data):
        # For performance reasons, we manipulate via regular expressions, and avoid
        # DOM-manipulations if possible.
        repl = []
        for term in ["D", "versteck-"]:
            if f'<a name="{term}"' in data:
                repl.append((
                    '<div class="dwb-head"><span class="dwb-form"/></div>',
                    f'<div class="dwb-head"><span class="dwb-form">{term}</span></div>',
                ))
        repl += [
            (' +title="zum Eintrag im DWB-Quellenverzeichnis"', " "),
            (' +data-toggle="tooltip"', " "),
            (' +data-placement="bottom"', " "),
            ('<div class="dwb-sense-n"></div>', ""),
            (r" *\n *", r" "),
            (r'<i class="[^"]*bi-arrow-up-right[^"]*"/?>([^<]*</i>)?', ""),
            (r'<span class="(?:&#10;)? *dwb-italics dwb-hi">([^<]*)</span>', r"<i>\1</i>"),
            (r'<span class="(?:&#10;)? *dwb-title">([^<]*)</span>', r"<i>\1</i>"),
            (
                r'<span class="(?:&#10;)? *dwb-author"><a +href="[^"]*">([^<]*)</a></span>',
                r'<span style="font-variant: small-caps">\1</span>',
            ),
            (
                r'<span class="(?:&#10;)? *dwb-caps dwb-hi">([^<]*)</span>',
                r'<span style="font-variant: small-caps">\1</span>',
            ),
            (r'<div class="dwb-sense-n">([^<]+)</div>', r"<b>\1</b>"),
            (r'<a name="[^"]*"></a>', r""),
            (r'<a href="/wb/dwb/([^"]+)">([^<]+)</a>', r'<a href="bword://\1">\2</a>'),
        ]
        for pattern, subst in repl:
            data = re.sub(pattern, subst, data)

        return data

    def do_html_term(self, doc):
        term = doc("div.dwb-head span.dwb-form").eq(0).text().rstrip(",) ").lstrip("(*— ")
        if len(term) == 0:
            term = self._curr_row["uri"]
            print(f"\nWarning: Heading is missing for term {term}!")
            return term
        sup_nums = "¹²³⁴⁵⁶⁷⁸⁹"
        if term[0] in sup_nums:
            term = f"{term[1:]}({sup_nums.index(term[0]) + 1})"
        else:
            m = re.match(r"^([0-9]+)\) *(.+)", term)
            if m is not None:
                term = f"{m.group(2)}({m.group(1)})"
            elif re.match(r"[A-Za-zúüäö-]", term[0]) is None:
                print(term)
        return term

    def do_html_alts(self, dt_html, doc, term):
        alts = [term] + [
            doc(elt).text().rstrip(", ")
            for elt in doc("div.dwb-head span.dwb-form")
        ]
        alts += [a.replace("ú", "u") for a in alts]
        return sorted(set(alts))

    def do_html_definition(self, dt_html, html, term):
        doc = pq(html)

        # other parts of the entry that we do not include
        doc("p.label").remove()
        doc("div.dwb-toc").remove()
        doc("div.citation-help").remove()

        # italic style spans
        doc("i.bi-arrow-up-right").remove()
        doc_rewrap_els(doc, "span.dwb-italics", "<i/>")

        # paragraphs for alternative meanings and subordinate lemmas (e.g. composita)
        doc_rewrap_els(doc, "div.dwb-sense-n", "<b/>")
        doc_strip_els(
            doc, "div.dwb-sense-content > div.dwb-sense:first-child", block=False,
        )

        # heading and subheadings (.dwb-re, i.e. subordinate lemmas)
        doc("div.dwb-head > a").remove()
        doc_retag_els(
            doc, "div.dwb-re span.dwb-form", "b",
            css=[("font-variant", "small-caps")],
        )
        doc_retag_els(doc, "span.dwb-form", "b")

        # author names for sources/quotes
        doc_strip_els(doc, "span.dwb-author a", block=False)
        doc_rewrap_els(doc, "span.dwb-caps", "<span/>", css=[("font-variant", "small-caps")])
        doc_rewrap_els(doc, "span.dwb-author", "<span/>", css=[("font-variant", "small-caps")])

        # links to related articles
        regex = (r"^/wb/dwb/(.+)$", r"bword://\1")
        doc_replace_attr_re(doc, "a", "href", regex)

        # blockquotes
        doc_retag_els(doc, "div.dwb-cit > div.dwb-bibl", "p", css=[
            ("font-style", "normal"),
            ("font-size", "x-small"),
            ("text-align", "right"),
        ])
        doc_retag_els(doc, "div.dwb-cit", "blockquote")

        # cleanup
        doc("*").removeAttr("class")
        doc("*").removeAttr("title")

        return doc.html().strip()
