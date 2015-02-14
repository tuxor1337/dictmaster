# -*- coding: utf-8 -*-

import re
import sys
import os

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import mkdir_p
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Fetcher, UrlFetcher
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

ZENO_OPTS = {
    "Pape-1880": {
        "dictname": "Pape: Handwörterbuch der griechischen Sprache",
        "non-articles": ["hrung","Pape"],
        "wordcount": 100000
    },
    "Georges-1913": {
        "dictname": "Georges: Ausführliches lateinisch-deutsches Handwörterbuch",
        "non-articles": ["Verzeichnis", "Vorrede", "Ausgaben", "Georges"],
        "wordcount": 56000
    },
    "Georges-1910": {
        "dictname": "Georges: Kleines deutsch-lateinisches Handwörterbuch",
        "non-articles": ["Verzeichnis", "Vorrede", "Ausgaben", "Georges", "Vorwort"],
        "wordcount": 27000
    },
}

ZENO_URL = "http://www.zeno.org"

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        zeno_key = popts
        if zeno_key not in ZENO_OPTS:
            sys.exit("Zeno key not supported, try: {}".format(ZENO_OPTS.keys()))
        super(Plugin, self).__init__(popts, os.path.join(dirname,zeno_key))
        self.dictname = ZENO_OPTS[zeno_key]["dictname"]
        self.url_list = []
        url_fetcher = ZenoUrlFetcher(self,
            "%s/Kategorien/T/%s?s=%%d" % (ZENO_URL, zeno_key),
            ZENO_OPTS[zeno_key]["wordcount"]
        )
        fetcher = ZenoFetcher(self.output_directory, urls=self.url_list)
        postprocessor = ZenoProcessor(self, ZENO_OPTS[zeno_key]["non-articles"])
        editor = Editor(
            output_directory=self.output_directory,
            plugin=self
        )
        self._stages = [
            url_fetcher,
            fetcher,
            postprocessor,
            editor
        ]

class ZenoFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def fetchUrl(self, url):
            Fetcher.FetcherThread.fetchUrl(self, ZENO_URL + url)
        def filter_data(self, data):
            container = "div.zenoCOMain"
            encoded_str = data.decode("iso-8859-1").encode("utf-8")
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(encoded_str, parser=parser))
            if len(doc(container)) == 0:
                return None
            else:
                return doc(container).html().encode("utf-8")

class ZenoUrlFetcher(UrlFetcher):
    class FetcherThread(UrlFetcher.FetcherThread): pass
    def __init__(self, plugin, url_pattern, wordcount):
        super(ZenoUrlFetcher, self).__init__(plugin)
        self.urls = range(0,wordcount,20)
        def fetchUrl_override(fthread, url):
            fthread._i += 1
            if fthread.offset > (fthread._i-1)*20:
                return ""
            url = url_pattern % url
            d = pq(fthread.download_retry(url))
            hitlist = d("span.zenoSRHitTitle")
            if len(hitlist) == 0:
                fthread._canceled = True
                return None
            output = ""
            for hit in hitlist:
                url = d(hit).find("a").attr("href")
                output += "%s\n" % url
            fthread.write_file(None, output)
            return output
        self.FetcherThread.fetchUrl = fetchUrl_override

class ZenoProcessor(HtmlContainerProcessor):
    def __init__(self, plugin, nonarticles):
        super(ZenoProcessor, self).__init__("", plugin, singleton=True)
        self.nonarticles = nonarticles

    def do_html_term(self, html):
        doc = pq(html)
        term = doc("h2.zenoTXul").eq(0).text().strip()
        if term == "":
            h3 = doc("h3").text()
            if not h3:
                h3 = doc("h2").text()
            if not all(x not in h3 for x in self.nonarticles):
                return ""
            else:
                print(html)
                sys.exit()
        term = re.sub(r" *\[([0-9]+)\] *$", r"(\1)", term.replace(";",""))
        return term

    def do_html_definition(self, html, term):
        doc = pq(html)
        doc.remove("a.zenoTXKonk[title='Faksimile']")
        for div in doc("div.zenoIMBreak"):
            doc(div).replaceWith(
                doc("<p/>").html(doc(div).find("div a").html()).outerHtml()
            )
        for div in doc("div.zenoIMBreak"):
            doc(div).replaceWith(
                doc("<p/>").html(doc(div).find("div a").html()).outerHtml()
            )
        doc.remove("div")
        for a in doc("a"):
            doc(a).replaceWith(
                doc("<span/>").html(doc(a).html()).outerHtml()
            )
        for font_el in doc("font"):
            replacement = doc("<span/>").html(doc(font_el).html())
            if font_el.attr("color"):
                replacement.css("color", font_el.attr("color"))
            doc(font_el).replaceWith(replacement.outerHtml())
        for i_el in doc("i"):
            doc(i_el).css("color", "#494")
        for b_el in doc("b"):
            doc(b_el).css("color", "#0B0")
        self._download_res(doc)
        result = ""
        for para in doc.find("p"):
            if doc(para).html():
                result += "%s<br />" % doc(para).html()
        return result

    def _download_res(self, doc):
        for img in doc.find("img"):
            url = "%s%s" % (ZENO_URL, doc(img).attr("src"))
            basename = url.split('/')[-1]
            data = self.download_retry(url)
            res_dirname = os.path.join(self.plugin.output_directory, "res")
            mkdir_p(res_dirname)
            with open(os.path.join(res_dirname,basename), "w") as img_file:
                img_file.write(data)
            doc(img).attr("src", basename)
        definition = doc.html()

