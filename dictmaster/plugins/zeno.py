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
import sys
import os

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import FLAGS
from dictmaster.replacer import *
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.urlfetcher import UrlFetcher
from dictmaster.stages.processor import HtmlContainerProcessor

ZENO_OPTS = {
    "Pape-1880": {
        "dictname": u"Pape: Handwörterbuch der griechischen Sprache",
        "non-articles": ["hrung","Pape"],
        "wordcount": 98910
    },
    "Georges-1913": {
        "dictname": u"Georges: Ausführliches lateinisch-deutsches Handwörterbuch",
        "non-articles": ["Verzeichnis", "Vorrede", "Ausgaben", "Georges"],
        "wordcount": 54866
    },
    "Georges-1910": {
        "dictname": u"Georges: Kleines deutsch-lateinisches Handwörterbuch",
        "non-articles": ["Verzeichnis", "Vorrede", "Ausgaben", "Georges", "Vorwort"],
        "wordcount": 26634
    },
}

ZENO_KEYS = ", ".join(ZENO_OPTS.keys())
ZENO_URL = "http://www.zeno.org"

POPTS_DEFAULT = ["Georges-1913"]

class Plugin(BasePlugin):
    def __init__(self, dirname, popts=POPTS_DEFAULT):
        if len(popts) != 1:
            sys.exit("Provide a supported Zeno key: {}".format(ZENO_KEYS))
        self.zeno_key = popts[0]
        if self.zeno_key not in ZENO_OPTS:
            sys.exit("Zeno key not supported, try: {}".format(ZENO_KEYS))
        super(Plugin, self).__init__(os.path.join(dirname, self.zeno_key))
        self.dictname = ZENO_OPTS[self.zeno_key]["dictname"]
        url_fetcher = ZenoUrlFetcher(self,
            "%s/Kategorien/T/%s?s=%%d" % (ZENO_URL, self.zeno_key)
        )
        processor = ZenoProcessor("", self, singleton=True)
        processor.nonarticles = ZENO_OPTS[self.zeno_key]["non-articles"]
        self.stages['UrlFetcher'] = url_fetcher
        self.stages['Fetcher'] = ZenoFetcher(self)
        self.stages['Processor'] = processor

    def post_setup(self, cursor):
        wordcount = ZENO_OPTS[self.zeno_key]["wordcount"]
        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', [(i, FLAGS["URL_FETCHER"]) for i in range(0, wordcount, 20)])

class ZenoUrlFetcher(UrlFetcher):
    class FetcherThread(UrlFetcher.FetcherThread):
        _retry403 = True
        _retry404 = True

        def filter_data(self, data, uri):
            d = pq(data)
            hitlist = d("span.zenoSRHitTitle")
            if len(hitlist) == 0: return []
            links = [d(hit).find("a").attr("href") for hit in hitlist]
            return [uri for uri in links if "/A/" in uri]

    def __init__(self, plugin, url_pattern):
        super(ZenoUrlFetcher, self).__init__(plugin)
        def parse_uri_override(fthread, uri): return url_pattern % int(uri)
        self.FetcherThread.parse_uri = parse_uri_override

class ZenoFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        _retry403 = True
        _retry404 = True

        def parse_uri(self, uri):
            return ZENO_URL + uri

        def filter_data(self, data, uri):
            if data == None: return None
            container = "div.zenoCOMain"
            data = data.decode("iso-8859-1")
            data = data.replace("<b/>", "")
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(data.encode("utf-8"), parser=parser))
            if len(doc(container)) == 0:
                return None
            else:
                doc("script").remove()
                return doc(container).html()

    def init_queue(self):
        Fetcher.init_queue(self)
        self._queue.reload_duplicates = True

class ZenoProcessor(HtmlContainerProcessor):
    nonarticles = []
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
        term = re.sub(r"\s*\[([0-9]+)\]\s*$", r"(\1)",
            re.sub(r"\s*\[\*\]\s*$", "", term.replace(";",""))
        )
        return term

    def do_html_definition(self, dt_html, html, term):
        doc = pq(html)
        doc.remove("a.zenoTXKonk[title='Faksimile']")
        doc.remove("div.zenoCOAdRight")

        for div in doc("a"):
            if "/I/" not in doc(div).attr("href"):
                print("a", term, doc(div).attr("href"))
        doc_rewrap_els(doc, "a", "<span/>")

        for div in doc("div"):
            print("div", term)
        doc.remove("div")

        color = "#47A"
        if self.plugin.zeno_key != "Pape-1880":
            doc_rewrap_els(doc, "b", "<span class='tmp_bold' />")
            doc_rewrap_els(doc, "span.tmp_bold", "<b/>", css=[("color", color)])

        i_color = "#000" if self.plugin.zeno_key == "Pape-1880" else color
        doc_rewrap_els(doc, "i", "<span class='tmp_italic' />")
        doc_rewrap_els(doc, "span.tmp_italic", "<i/>", css=[("color", i_color)])

        self._download_res(doc)
        result = ""
        for para in doc.find("p"):
            if doc(para).html():
                result += "%s<br />" % doc(para).html()
        if self.plugin.zeno_key == "Pape-1880":
            result = f'<span style="color: {color}">{result}</span>'
        return result

    def _download_res(self, doc):
        for img in doc.find("img"):
            url = "%s%s" % (ZENO_URL, doc(img).attr("src"))
            basename = url.split('/')[-1]
            data = self.download_retry(url)
            res_dirname = os.path.join(self.plugin.output_directory, "res")
            basename = basename.split("?")[0]
            with open(os.path.join(res_dirname, basename), "wb") as img_file:
                img_file.write(data)
            doc(img).attr("src", basename)

