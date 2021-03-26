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

try:
    from urllib2 import unquote
except ImportError:
    from urllib.request import unquote

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import CancelableThread, remove_accents, words_to_db
from dictmaster.replacer import *
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.processor import HtmlContainerProcessor

BASE_URL = "https://dle.rae.es/srv"

POSTDATA = b"TS017111a7_id=3"\
         + b"&TS017111a7_cr=d537139570e4db3599d3d9b1c5baadaf:qrpr:kvYkKLVF:280794873"\
         + b"&TS017111a7_76=0"\
         + b"&TS017111a7_86=0"\
         + b"&TS017111a7_md=1"\
         + b"&TS017111a7_rf=0"\
         + b"&TS017111a7_ct=0"\
         + b"&TS017111a7_pd=0"

POPTS_DEFAULT = ["thirdparty/wordlists/esp/drae.txt"]

class Plugin(BasePlugin):
    dictname = u"Diccionario de la lengua española: 23a edición"

    def __init__(self, dirname, popts=POPTS_DEFAULT):
        if len(popts) == 0 or not os.path.exists(popts[0]):
            sys.exit("Provide full path to (existing) word list file!")
        self.word_file = popts[0]
        super(Plugin, self).__init__(dirname)
        self.stages['Fetcher'] = DraeFetcher(self, postdata=POSTDATA, threadcnt=10)
        self.stages['Processor'] = DraeProcessor("article", self)

    def post_setup(self, cursor):
        words_to_db(self.word_file, cursor, ("utf-8", "utf-8"))

class DraeFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data, curr_word):
            if data == None or len(data) < 2: return None
            data = data.decode("utf-8")
            cont = "div#a0 > article"
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(data, parser=parser))
            url = ""
            if len(doc(cont)) == 0:
                if len(doc("ul")) == 0: return None
                for a in doc("li a"):
                    curr = remove_accents(unquote(curr_word)).lower()
                    if len(curr) > 2: curr = curr.rstrip("s")
                    if curr in remove_accents(doc(a).text().lower()):
                        url = "%s/%s" % (BASE_URL, doc(a).attr("href"))
            elif len(doc(u"img[alt='Ver artículo enmendado']")) > 0:
                img = doc(u"img[alt='Ver artículo enmendado']")
                url = "%s/%s" % (BASE_URL, img.parent().attr("href"))
            else:
                return "".join(doc(d).outerHtml() for d in doc(cont))
            if url != "":
                data = self.download_retry(url, self.postdata)
                return self.filter_data(data, curr_word)
            else: return None

        def parse_uri(self, uri):
            return "%s/search?w=%s&m=form" % (BASE_URL, uri)

class DraeProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        term = doc("header.f").eq(0).text().strip(". ")
        return term

    def do_html_definition(self, dt_html, html, term):
        # Output is black/white and condensed as in
        # http://www.rae.es/sites/default/files/Articulos_de_muestra.pdf
        doc = pq(html)

        # links to conjugation tables etc.
        doc("a.e2").remove()

        # links to related articles
        fun = lambda el, val: "bword://%s" % doc(el).text().strip(". ")
        doc_replace_attr(doc, "a", "href", fun)

        # simple inline styles
        doc_rewrap_els(doc, "header", "<b/>")
        doc_rewrap_els(doc, "span.h,abbr.c", "<i/>")
        doc_rewrap_els(doc, "span.u", "<b/>")
        doc_rewrap_els(doc, "span.i1", "<span/>", css=[["font-variant","small-caps"]])

        # lemma placeholder
        doc_rewrap_els(doc, "u", "<b/>", regex=[[r".*","~"]])

        # correct paragraph enumeration
        for p in doc("p[class]"):
            pclass = doc(p).attr("class")[0]
            prevclass = doc(p).prev("p").attr("class")
            prevclass = " " if prevclass is None else prevclass[0]
            nextclass = doc(p).next("p").attr("class")
            nextclass = " " if nextclass is None else nextclass[0]
            if nextclass != pclass and prevclass != pclass:
                p_html = re.sub(r"^(1\.)", r"", doc(p).html())
            else:
                p_html = re.sub(r"^([0-9]+\.)", r"<b>\1</b>", doc(p).html())
            doc(p).html(p_html)

        # put etymology in parentheses
        ns = doc("p.n1,p.n2,p.n3,p.n5")
        if len(ns) > 0:
            n0 = ns[0]
            nl = ns[-1]
            doc(n0).html(" (" + doc(n0).html())
            doc(nl).html(doc(nl).html() + ") ")

        # inline paragraphs with corresponding marks
        doc_rewrap_els(doc, "p.n1", "<span/>", prefix=" ", suffix=" ")
        doc_rewrap_els(doc, "p.n2", "<span/>", prefix=" ", suffix=" ")
        doc_rewrap_els(doc, "p.n3", "<span/>", prefix=" ♦ ")
        doc_rewrap_els(doc, "p.n4", "<span/>", prefix=" ", suffix=" ")
        doc_rewrap_els(doc, "p.n5", "<span/>", prefix=" ♦ ")
        doc_rewrap_els(doc, "p.j", "<span/>", prefix=" ǁ ")
        doc_rewrap_els(doc, "p.j1", "<span/>", prefix=" ● ")
        doc_rewrap_els(doc, "p.j2", "<span/>", prefix=" ○ ")
        doc_rewrap_els(doc, "p.k5", "<b/>", prefix=" ■ ")
        doc_rewrap_els(doc, "p.k6 span.k1", "<span/>", css=[["font-weight","normal"]])
        doc_rewrap_els(doc, "p.k6", "<b/>", prefix=" □ ")
        doc_rewrap_els(doc, "p.k", "<b/>", prefix=" ǁ ")
        doc_rewrap_els(doc, "p.b", "<span/>", prefix="▶ ")
        doc_rewrap_els(doc, "p.l", "<b/>", prefix=", ")
        doc_rewrap_els(doc, "p.l2", "<span/>", prefix=" ")
        doc_rewrap_els(doc, "p.l3", "<b/>", prefix="<br />▶ ")
        doc_rewrap_els(doc, "p.m", "<span/>", prefix=" ")

        # clean up unnecessary stuff
        doc_strip_els(doc, "mark", block=False)
        doc_strip_els(doc, "abbr", block=False)
        doc_strip_els(doc, "span:not([style])", block=False)
        doc("*").removeAttr("class").removeAttr("title")
        result = doc.html()
        regex = [
            [r"ǁ\s*([^<\s])",r"\1"],
            [r"ǁ\s*<b>\s*1\.",r" <b>1."],
            [r"<b>\s*ǁ",r" ǁ <b>"],
            [r"\s*ǁ\s*$",r""],
        ]
        for r in regex: result = re.sub(r[0], r[1], result)
        return result.strip()

