# -*- coding: utf-8 -*-

import re
import os
import sys

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import html_container_filter
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import WordFetcher
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

# TODO: get full word list

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        word_file = popts
        if not os.path.exists(word_file):
            sys.exit("Provide full path to (existing) word list file!")
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = "Digitales Wörterbuch der deutschen Sprache"
        fetcher = DWDSFetcher(
            self.output_directory,
            url_pattern="http://m.dwds.de/loadpanel/?panel_id=32&qu={word}",
            word_file=word_file,
            word_codec=("utf-8", "utf-8"),
            threadcnt=10
        )
        self._stages = [
            fetcher,
            DWDSProcessor("", self, singleton=True),
            Editor(plugin=self)
        ]

class DWDSFetcher(WordFetcher):
    class FetcherThread(WordFetcher.FetcherThread):
        def filter_data(self, data):
            if data == None or len(data) < 2 \
            or '<div id="ddc_panel_32"' not in data \
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
            return doc("div#ddc_panel_32").html().encode("utf-8")

class DWDSProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        term = doc("span.wb_lzga").eq(0).text().strip()
        regex = []
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_definition(self, html, term):
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
            elif "definition/english/" not in doc(a).attr("href"):
                doc(a).replaceWith(doc(a).html())
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

