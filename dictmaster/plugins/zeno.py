# -*- coding: utf-8 -*-

import re
import sys
import os

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import html_container_filter, mkdir_p, CancelableThread
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Fetcher
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

ZENO_OPTS = {
    "Pape-1880": {
        "dictname": "Pape: Handwörterbuch der griechischen Sprache",
        "non-articles": ["hrung","Pape"]
    },
    "Georges-1913": {
        "dictname": "Georges: Ausführliches lateinisch-deutsches Handwörterbuch",
        "non-articles": ["Verzeichnis", "Vorrede", "Ausgaben", "Georges"]
    },
    "Georges-1910": {
        "dictname": "Georges: Kleines deutsch-lateinisches Handwörterbuch",
        "non-articles": ["Verzeichnis", "Vorrede", "Ausgaben", "Georges", "Vorwort"]
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
            "%s/Kategorien/T/%s?s=%%d" % (ZENO_URL, zeno_key)
        )
        fetcher = Fetcher(self.output_directory,
            urls=self.url_list,
            filter_fct=zeno_filter("div.zenoCOMain", "iso-8859-1")
        )
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

def zeno_filter(container, charset="utf-8", err_msg="rejected"):
    def tmp_func(data):
        encoded_str = data.decode(charset).encode("utf-8")
        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(encoded_str, parser=parser))
        if len(doc(container)) == 0:
            raise Exception(err_msg)
        else:
            return doc(container).html().encode("utf-8")
    return tmp_func

class ZenoUrlFetcherThread(CancelableThread):
    def __init__(self, no, url_pattern):
        super(ZenoUrlFetcherThread, self).__init__()
        self.url_pattern = url_pattern
        self.output = []
        self.threadno = no

    def progress(self):
        if self._canceled:
            return "Sleeping..."
        return "{}:{}".format(self.threadno, len(self.output))

    def run(self):
        step = 20
        startnum = step*self.threadno
        while True:
            if self._canceled:
                return
            url = self.url_pattern % startnum
            d = pq(self.download_retry(url))
            hitlist = d("span.zenoSRHitTitle")
            if len(hitlist) == 0:
                break
            for hit in hitlist:
                url = d(hit).find("a").attr("href")
                self.output.append("%s%s" % (ZENO_URL, url))
            startnum += 10*step

class ZenoUrlFetcher(CancelableThread):
    def __init__(self, plugin, url_pattern):
        super(ZenoUrlFetcher, self).__init__()
        self.plugin = plugin
        self._subthreads = [None]*10
        self.url_pattern = url_pattern

    def progress(self):
        if self._canceled or self._subthreads[0] == None:
            return "Sleeping..."
        prog = "Collecting URLs... "
        for i in range(len(self._subthreads)):
            prog += "%s " % self._subthreads[i].progress()[:13]
        return prog

    def init_subthreads(self):
        for i in range(len(self._subthreads)):
            self._subthreads[i] = ZenoUrlFetcherThread(
                no=i,
                url_pattern=self.url_pattern
            )

    def run(self):
        raw_dirname = os.path.join(self.plugin.output_directory, "raw")
        if len(os.listdir(raw_dirname)) > 0:
            self.cancel()

        if self._canceled:
            return

        self.init_subthreads()
        for i in range(len(self._subthreads)):
            self._subthreads[i].start()

        for i in range(len(self._subthreads)):
            self._subthreads[i].join()
            self.plugin.url_list.extend(self._subthreads[i].output)

    def cancel(self):
        CancelableThread.cancel(self)
        if self._subthreads[0] != None:
            for i in range(len(self._subthreads)):
                self._subthreads[i].cancel()

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

