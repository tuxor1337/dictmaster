# -*- coding: utf-8 -*-


import re
from string import lowercase as ALPHA
from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import FLAGS
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Fetcher, UrlFetcher
from dictmaster.postprocessor import HtmlABProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = u"Online Etymology Dictionary, ©Douglas Harper/etymonline.com"
        self._stages = [
            EtymonlineUrlFetcher(self),
            EtymonlineFetcher(self),
            EtymonlineProcessor(("dt", "dd"), self),
            Editor(self)
        ]

    def post_setup(self, cursor):
        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', [(a, FLAGS["URL_FETCHER"]) for a in ALPHA])

class EtymonlineUrlFetcher(UrlFetcher):
    class FetcherThread(UrlFetcher.FetcherThread):
        def filter_data(self, data):
            d = pq(data)
            hitlist = d("div.paging:first-child a")
            out = []
            for a in hitlist:
                out.append(re.sub(
                    "^.*(l=[a-z]&p=[0-9]+)&.*$",
                    r"\1",
                    d(a).attr("href")
                ))
            return out

        def parse_uri(self,uri):
            return "http://www.etymonline.com/index.php?l=%s"%uri

class EtymonlineFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data):
            if data == None \
            or '<div id="dictionary">' not in data \
            or '<p>No matching terms found.</p>' in data:
                return None
            container = "div#dictionary dl"
            parser = etree.HTMLParser(encoding="iso-8859-1")
            doc = pq(etree.fromstring(data, parser=parser))
            if len(doc(container)) == 0: return None
            else: return doc(container).html()

        def parse_uri(self, uri):
            return "http://www.etymonline.com/index.php?%s"%uri

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

