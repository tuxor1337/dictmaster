# -*- coding: utf-8 -*-

import re
import os

from pyquery import PyQuery as pq

from dictmaster.util import html_container_filter
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import WordFetcher
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

# TODO: enmiendas articulos, cf.
#   https://github.com/vibragiel/glotologia/blob/master/enmiendas_drae/enmiendas-drae.py

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        word_file = popts if popts != "" else "words.txt"
        self.dictname = "Diccionario de la lengua española: 22a edición"
        postdata = "TS014dfc77_id=3"\
            + "&TS014dfc77_cr=6df4b31271d91b172321d2080cefbee7:becd:943t352k:1270247778"\
            + "&TS014dfc77_76=0"\
            + "&TS014dfc77_86=0"\
            + "&TS014dfc77_md=1"\
            + "&TS014dfc77_rf=0"\
            + "&TS014dfc77_ct=0"\
            + "&TS014dfc77_pd=0"
        fetcher = WordFetcher(self.output_directory,
            url_pattern="http://lema.rae.es/drae/srv/search?val={word}",
            word_file=word_file,
            word_codec=("utf-8", "iso-8859-1"),
            filter_fct=html_container_filter("html"),
            postdata=postdata
        )
        postprocessor = DraeProcessor(self)
        editor = Editor(
            output_directory=self.output_directory,
            plugin=self
        )
        self._stages = [
            fetcher,
            postprocessor,
            editor
        ]

class DraeProcessor(HtmlContainerProcessor):
    def __init__(self, plugin):
        super(DraeProcessor, self).__init__("body > div", plugin)

    def do_html_term(self, doc):
        term = doc("p.p span.f b").eq(0).text().strip()
        return term

    def do_html_definition(self, html, term):
        doc = pq(html)
        html.find("a").removeAttr("name")
        html.find("a").removeAttr("target")
        for a in html.find("a:not([href])"):
            doc(a).replaceWith(doc(a).html())
        for a in html.find("a"):
            if doc(a).text().strip() == "":
                doc(a).replaceWith("")
            else:
                href = "bword://%s" % doc(a).text().strip(". ")
                doc(a).replaceWith(
                    doc("<a/>").attr("href", href)
                        .html(doc(a).html()).outerHtml()
                )
        html.find("span.d,span.f").css("color", "#00f")
        html.find("span.a").css("color", "#080")
        html.find("span.g").css("color", "#AAA")
        html.find("span.j").css("color", "#F00")
        html.find("span.k").css("color", "#800")
        html.find("span.h").css("color", "#808")
        for span in html.find("span.b,span.n"):
            doc(span).replaceWith(doc(span).html())

        for span in html.find("span:not([style])"):
            doc(span).replaceWith(doc(span).html())
        html.find("*").removeAttr("class").removeAttr("title")
        return html.html().strip()

