# -*- coding: utf-8 -*-

from xml.dom import Node
from xml.dom.pulldom import SAX2DOM
import lxml.sax, lxml.html

import re
from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.pthread import PluginThread
from dictmaster.fetcher import AlphanumFetcher
from dictmaster.postprocessor import HtmlABProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = "Online Etymology Dictionary, ©Douglas Harper/etymonline.com"
        fetcher = EtymonlineFetcher(
            self.output_directory,
            url_pattern="http://www.etymonline.com/index.php?l={alpha}&p={num}"
        )
        self._stages = [
            fetcher,
            EtymonlineProcessor(("dt", "dd"), self),
            Editor(plugin=self)
        ]

class EtymonlineFetcher(AlphanumFetcher):
    class FetcherThread(AlphanumFetcher.FetcherThread):
        def filter_data(self, data):
            if data == None or len(data) < 2 \
            or '<div id="dictionary">' not in data \
            or '<p>No matching terms found.</p>' in data:
                raise Exception("next_block")
            container = "div#dictionary dl"
            parser = etree.HTMLParser(encoding="iso-8859-1")
            doc = pq(etree.fromstring(data, parser=parser))
            if len(doc(container)) == 0: raise Exception("next_block")
            else: return doc(container).html().encode("utf-8")

class EtymonlineProcessor(HtmlABProcessor):
    def do_pre_html(self, data):
        data = data.replace("&#13;", "")
        regex = [
            [r'\[([^\]]+)\]\n</blockquote>', r'<p class="src">[\1]</p></blockquote>'],
            [r'([^=])"([^> ][^"]*[^ ])"', r'\1<span class="meaning">"\2"</span>']
        ]
        for r in regex: data = re.sub(r[0], r[1], data)
        return data

    def do_html_term(self, doc):
        term = doc("a").eq(0).text().strip()
        regex = [
            [r" +\([^)]+\)$",r""]
        ]
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_definition(self, html, term):
        doc = pq(html)
        for a in doc("a"):
            new_href = re.sub(
                r"^[^\?]+\?term=([^&]+)&.*$",
                r"bword://\1",
                doc(a).attr("href")
            )
            doc(a).attr("href", new_href)
        for sp in doc("span.foreign"):
            doc(sp).replaceWith("<i>%s</i>"%doc(sp).html())
        doc("span.meaning").css("color","#47A")
        for src in doc("blockquote p.src"):
            doc(src).css("font-style","normal") \
                .css("font-size","x-small").css("text-align","right")
            for span in doc(src).find("span.meaning"):
                doc(span).replaceWith(doc(span).text())
        doc("*").removeAttr("class")
        return "<dt>%s</dt><dd>%s</dd>" % (term, doc.html())

