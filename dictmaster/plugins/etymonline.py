# -*- coding: utf-8 -*-

from xml.dom import Node
from xml.dom.pulldom import SAX2DOM
import lxml.sax, lxml.html

import re
from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import html_container_filter
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
        postprocessor = EtymonlineProcessor(self)
        editor = Editor(output_directory=self.output_directory, plugin=self)
        self._stages = [
            fetcher,
            postprocessor,
            editor
        ]

class EtymonlineFetcher(AlphanumFetcher):
    class FetcherThread(AlphanumFetcher.FetcherThread):
        def filter_override(self, encoded_str):
            container = "div#dictionary dl"
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(encoded_str, parser=parser))
            if len(doc(container)) == 0:
                raise Exception("next_block")
            else:
                return doc(container).html().encode("utf-8")

class EtymonlineProcessor(HtmlABProcessor):
    def __init__(self, plugin):
        super(EtymonlineProcessor, self).__init__(("dt", "dd"), plugin, "iso-8859-1")

    def do_html_term(self, doc):
        term = doc("a").eq(0).text().strip()
        regex = [
            [r" +\([^)]+\)$",r""]
        ]
        for r in regex:
            term = re.sub(r[0], r[1], term)
        return term

    def do_html_definition(self, html, term):
        doc = pq(html)
        for a in html.find("a"):
            new_href = re.sub(
                r"^[^\?]+\?term=([^&]+)&.*$",
                r"bword://\1",
                doc(a).attr("href")
            )
            doc(a).attr("href", new_href)

        for span in html.find("span.foreign"):
            doc(span).attr("style","font-style:italic;color:#8B4513")

        d = _replace_quotes(html)
        d = _replace_blockquote_src(d, html)
        d("span.meaning").attr("style","color:#4682B4")
        for span in d("blockquote p.src"):
            d(span).attr("style","font-style:normal;font-size:x-small;text-align:right")
            d(span).find("span.meaning").removeAttr("style")
        return "<dt>%s</dt><dd>%s</dd>" % (term, d.html())

def _walkTextNodes(dom, fn):
    for node in dom.childNodes:
        if node.nodeType == Node.TEXT_NODE:
            node.replaceWholeText(fn(node.nodeValue))
        else:
            _walkTextNodes(node, fn)

def _processText(text):
    text = re.sub(r'"([^"]+)"', r'[span class=meaning]"\1"[/span]', text)
    return text

def _replace_quotes(pq_obj):
    handler = SAX2DOM()
    lxml.sax.saxify(lxml.html.fragment_fromstring(pq_obj.outerHtml()), handler)
    dom = handler.document
    _walkTextNodes(dom, _processText)
    dom = re.sub(r"\[/span\]",r"</span>",dom.toxml())
    dom = re.sub(r"\[span class=meaning\]", r'<span class="meaning">', dom)
    return pq(dom)

def _processBlockquote(text):
    text = re.sub(r'\[([^\]]+)\]', r'[p class=src][\1][/p]', text)
    return text

def _replace_blockquote_src(d, dd):
    for block in d("blockquote"):
        handler = SAX2DOM()
        lxml.sax.saxify(lxml.html.fragment_fromstring(d(block).outerHtml()), handler)
        dom = handler.document
        _walkTextNodes(dom, _processBlockquote)
        dom = re.sub(r"\[/p\]",r"</p>", dom.toxml())
        dom = re.sub(r"\[p class=src\]", r'<p class="src">', dom)
        d(block).replaceWith(dom)
    return d

