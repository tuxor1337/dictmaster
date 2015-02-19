# -*- coding: utf-8 -*-

import re
import os
import sys

from urllib2 import unquote
from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import CancelableThread, remove_accents
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import WordFetcher
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
        word_file = popts
        if not os.path.exists(word_file):
            sys.exit("Provide full path to (existing) word list file!")
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = "Diccionario de la lengua española: 22a edición"
        fetcher = DraeFetcher(
            self.output_directory,
            url_pattern="http://lema.rae.es/drae/srv/search?val={word}",
            word_file=word_file,
            word_codec=("utf-8", "iso-8859-1"),
            postdata=POSTDATA,
            threadcnt=10
        )
        self._stages = [
            fetcher,
            DraeProcessor("div", self),
            Editor(plugin=self)
        ]

class DraeFetcher(WordFetcher):
    class FetcherThread(WordFetcher.FetcherThread):
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
                return "".join(doc(d).outerHtml().encode("utf-8") for d in doc(cont))
            if url != "":
                data = self.download_retry(url, self.postdata)
                return self.filter_data(data)
            else: return None

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
        for p in doc("p"):
            if doc(p).html() == None: doc(p).remove()
            else: doc(p).replaceWith(u" ‖ " + doc(p).html())
        doc("span.g").remove()

        for span in doc("span.b,span.n"):
            if doc(span).html() == None: doc(span).remove()
            else: doc(span).replaceWith(doc(span).html())
        for span in doc("span:not([style])"):
            if doc(span).html() == None: doc(span).remove()
            else: doc(span).replaceWith(doc(span).html())
        doc("*").removeAttr("class").removeAttr("title")
        return doc.html().strip()

