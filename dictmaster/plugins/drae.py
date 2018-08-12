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
import os
import sys

from urllib2 import unquote
from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import CancelableThread, remove_accents, words_to_db
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Fetcher
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

POSTDATA = "TS014dfc77_id=3"\
    + "&TS014dfc77_cr=6df4b31271d91b172321d2080cefbee7:becd:943t352k:1270247778"\
    + "&TS014dfc77_76=0"\
    + "&TS014dfc77_86=0"\
    + "&TS014dfc77_md=1"\
    + "&TS014dfc77_rf=0"\
    + "&TS014dfc77_ct=0"\
    + "&TS014dfc77_pd=0"

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        if len(popts) == 0 or not os.path.exists(popts[0]):
            sys.exit("Provide full path to (existing) word list file!")
        self.word_file = popts[0]
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = u"Diccionario de la lengua española: 22a edición"
        self._stages = [
            DraeFetcher(self, postdata=POSTDATA, threadcnt=10),
            DraeProcessor("div", self),
            Editor(self)
        ]

    def post_setup(self, cursor):
        words_to_db(self.word_file, cursor, ("utf-8", "iso-8859-1"))

class DraeFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data):
            if data == None or len(data) < 2: return None
            cont = "body > div"
            repl = [ ["‖ ",""] ]
            for r in repl: data = data.replace(r[0], r[1])
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(data, parser=parser))
            url = ""
            if len(doc(cont)) == 0:
                if len(doc("ul")) == 0: return None
                for a in doc("li a"):
                    curr = remove_accents(
                        unquote(self._curr_word).decode("iso-8859-1")
                    ).lower()
                    if len(curr) > 2: curr = curr.rstrip("s")
                    if remove_accents(curr) in remove_accents(doc(a).text().lower()):
                        url = "http://lema.rae.es/drae/srv/%s"%doc(a).attr("href")
            elif len(doc(u"img[alt='Ver artículo enmendado']")) > 0:
                img = doc(u"img[alt='Ver artículo enmendado']")
                url = "http://lema.rae.es/drae/srv/%s" % img.parent().attr("href")
            else:
                return "".join(doc(d).outerHtml() for d in doc(cont))
            if url != "":
                data = self.download_retry(url, self.postdata)
                return self.filter_data(data)
            else: return None

        def parse_uri(self, uri):
            return "http://lema.rae.es/drae/srv/search?val=%s"%uri

class DraeProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        term = doc("p.p span.f b").eq(0).text().strip()
        return term

    def do_html_definition(self, html, term):
        doc = pq(html)
        doc("p.l").remove()
        doc("a").removeAttr("name")
        doc("a").removeAttr("target")
        for a in doc("a:not([href])"):
            doc(a).replaceWith(doc(a).html())
        for a in doc("a"):
            if doc(a).text().strip() == "":
                doc(a).replaceWith("")
            else:
                href = "bword://%s" % doc(a).text().strip(". ")
                doc(a).replaceWith(
                    doc("<a/>").attr("href", href)
                        .html(doc(a).html()).outerHtml()
                )
        """
        "Colorful version:"
        doc("span.d,span.f").css("color", "#00f")
        doc("span.a").css("color", "#080")
        doc("span.g").css("color", "#AAA")
        doc("span.j").css("color", "#F00")
        doc("span.k").css("color", "#800")
        doc("span.h").css("color", "#808")
        """
        "Black/white version"
        "http://www.rae.es/sites/default/files/Articulos_de_muestra.pdf"
        for p in doc("p.q"):
            if not doc(p).next("p").hasClass("q") \
            and not doc(p).prev("p").hasClass("q"):
                if len(doc(p).children("span.k")) > 0:
                    doc(doc(p).children("span.k").eq(0)).remove()
                elif len(doc(p).children("span.d")) > 0:
                    doc(doc(p).children("span.d").eq(0)).remove()
        for p in doc("p"):
            if doc(p).html() == None: doc(p).remove()
            elif doc(p).hasClass("q"): doc(p).replaceWith(doc(p).html() + u" ǁ ")
            else: doc(p).replaceWith(doc(p).html())
        doc("span.g").remove()
        for span in doc("span.b,span.n"):
            if doc(span).html() == None: doc(span).remove()
            else: doc(span).replaceWith(doc(span).html())
        for span in doc("span:not([style])"):
            if doc(span).html() == None: doc(span).remove()
            else: doc(span).replaceWith(doc(span).html())
        doc("*").removeAttr("class").removeAttr("title")
        result = doc.html()
        regex = [
            [u"ǁ □",u"□"],
            [u"ǁ\s*<b>\s*1\."," <b>1."],
            [u"\s*ǁ\s*$",""],
        ]
        for r in regex: result = re.sub(r[0], r[1], result)
        return result.strip()

