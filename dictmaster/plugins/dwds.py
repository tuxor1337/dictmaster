# -*- coding: utf-8 -*-

import re
import os
import sys

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import html_container_filter, words_to_db
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Fetcher
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

PANEL_IDS = ["5","32"]
DICTNAMES = {
    "5": u"Etymologisches Wörterbuch © Dr. Wolfgang Pfeifer",
    "32": u"Digitales Wörterbuch der deutschen Sprache",
}

class Plugin(PluginThread):
    panelid = None

    def __init__(self, popts, dirname):
        if len(popts) != 2:
            sys.exit("Error: Expected exactly two plugin params: "
                +"a word list file and a panel id.")
        self.word_file, self.panelid  = popts
        if not os.path.exists(self.word_file):
            sys.exit("Provide full path to (existing) word list file!")
        if self.panelid not in PANEL_IDS:
            sys.exit("Panel ID {} is not supported. Try one of {}.".format(
                self.panelid, ", ".join(PANEL_IDS)
            ))
        super(Plugin, self).__init__(popts, os.path.join(dirname, self.panelid))
        self.dictname = DICTNAMES[self.panelid]
        self._stages = [
            DWDSFetcher(self),
            DWDSProcessor(self),
            Editor(plugin=self)
        ]

    def post_setup(self, cursor):
        words_to_db(self.word_file, cursor, ("utf-8", "utf-8"))

class DWDSFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data):
            if data == None or len(data) < 2 \
            or '<div id="ddc_panel_' not in data \
            or '<p style="text-align: center;">Kein Eintrag vorhanden</p>' in data:
                return None
            data = " ".join(data.split())
            repl = [ ]
            for r in repl: data = data.replace(r[0], r[1])
            regex = [
                [r'<div class="mobile_extra_content"> </div>', ""],
                [r' <div[^>]*> Quelle: WDG \| Artikeltyp: Vollartikel </div> ', ""],
                [r"<!--.*?-->", ""]
            ]
            for r in regex: data = re.sub(r[0], r[1], data)
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(data, parser=parser))
            return doc("div.content_panel > div").html()

    def __init__(self, plugin):
        super(DWDSFetcher, self).__init__(plugin, threadcnt=10)
        self.FetcherThread.parse_uri = lambda fthread, uri: \
            "http://m.dwds.de/loadpanel/?panel_id=%s&qu=%s"%(plugin.panelid,uri)

class DWDSProcessor(HtmlContainerProcessor):
    def __init__(self, plugin):
        super(DWDSProcessor, self).__init__("", plugin, singleton=True)
        self.do_html_definition = getattr(self, "do_html_definition_%s"%plugin.panelid)
        self.do_html_alts = getattr(self, "do_html_alts_%s"%plugin.panelid)

    def do_html_term(self, doc):
        term = doc("span.wb_lzga").eq(0).text().strip()
        regex = []
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_alts_5(self, html, term):
        doc = pq(html)
        return [doc(a).text() for a in doc("span.wb_lzga_min a")]

    def do_html_alts_32(self, html, term): return []

    def do_html_definition_5(self, html, term):
        doc = pq(html)("div.wb_container_zone_s")
        for a in doc("a"):
            if doc(a).text().strip() == "": doc(a).replaceWith(doc(a).text())
            else:
                href = "bword://%s" % doc(a).text().strip(". ").lower()
                doc(a).attr("href", href)
        doc("*").removeAttr("class").removeAttr("id")
        return " ".join(doc.html().strip().split())

    def do_html_definition_32(self, html, term):
        doc = pq(html)
        doc("img,audio,script").remove()
        doc("div.wb_zone_v").remove()
        doc("span.wb_lzga").remove()
        doc("div[style='float:right;']").remove()
        doc("div.hidden_data_32").remove()
        doc("span.wb_gram").css("color","#800")
        for b in doc("span.wb_bp"):
            doc(b).replaceWith("<b>%s</b>"%doc(b).html())
        for div in doc("div.base_panel_header"):
            for d in doc(div).find("div"):
                doc(d).replaceWith(doc(d).html())
            doc(div).replaceWith("<p>%s</p>"%doc(div).html())
        for div in doc("div.wb_container_zone_s"): doc(div).replaceWith(doc(div).html())
        for div in doc("div.shown_data_32"): doc(div).replaceWith(doc(div).html())
        for div in doc("div.dwdswb2_snippet"):
            doc(div).replaceWith('<p><i>%s</i></p>'%doc(div).text())
        for div in doc("div.wb_zone_s"):
            num = doc(div).find("div").eq(0)
            doc(num).replaceWith(
                doc("<b/>").css("background-color","#dde")
                    .css("padding","0px 4px")
                    .css("border-top","1px #fff solid")
                    .html(doc(num).text()).outerHtml()
            )
            doc(div).replaceWith("<div>%s</div>"%doc(div).html())
        for a in doc("a:not([href])"):
            replacement = doc(a).html()
            doc(a).replaceWith("" if replacement == None else replacement)
        for a in doc("a"):
            if doc(a).text().strip() == "": doc(a).replaceWith(doc(a).text())
            else:
                href = "bword://%s" % doc(a).text().strip(". ").lower()
                doc(a).attr("href", href)
        for div in doc("div"):
            if doc(div).text().strip() == "": doc(div).remove()
        for span in doc("span"):
            txt = doc(span).text().strip()
            if txt in ["","Aussprache"]: doc(span).remove()
        doc("*").removeAttr("class").removeAttr("id").removeAttr("onclick")
        return " ".join(doc("body > div").html().strip().split())

