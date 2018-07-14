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

DICTNAMES = {
    "1": u"Wörterbuch der deutschen Gegenwartssprache",
    "2": u"Etymologisches Wörterbuch © Dr. Wolfgang Pfeifer",
}

def list_panel_ids():
    return "Currently, the following panel IDs (resp. dictionaries) are supported:\n" \
        + "\n".join(["%s (%s)" % i for i in DICTNAMES.items()])

class Plugin(PluginThread):
    panelid = None

    def __init__(self, popts, dirname):
        if len(popts) != 2:
            sys.exit("Error: The DWDS plugin expects exactly two plugin params: "
                +"a word list file and a panel ID.\n" + list_panel_ids())
        self.word_file, self.panelid  = popts
        if not os.path.exists(self.word_file):
            sys.exit("Provide full path to (existing) word list file!")
        if self.panelid not in DICTNAMES:
            sys.exit(u"Panel ID {} is not supported. {}".format(
                self.panelid, list_panel_ids()
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
            or '<h1 class="dwdswb-ft-lemmaansatz' not in data \
            or 'Kein Eintrag zu <span' in data:
                return None
            data = " ".join(data.split())
            repl = [ ]
            for r in repl: data = data.replace(r[0], r[1])
            regex = [
                [r"<!--.*?-->", ""],
            ]
            for r in regex: data = re.sub(r[0], r[1], data)
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(data, parser=parser))
            return doc("div.row:nth-child(2) div.col-md-12").html()

    def __init__(self, plugin):
        super(DWDSFetcher, self).__init__(plugin, threadcnt=10)
        self.FetcherThread.parse_uri = lambda fthread, uri: \
            "https://www.dwds.de/wb/%s" % (uri,)

class DWDSProcessor(HtmlContainerProcessor):
    def __init__(self, plugin):
        super(DWDSProcessor, self).__init__("", plugin, singleton=True)
        self.do_html_definition = getattr(self, "do_html_definition_%s"%plugin.panelid)
        self.do_html_alts = getattr(self, "do_html_alts_%s"%plugin.panelid)

    def do_html_term(self, doc):
        term = doc("h1.dwdswb-ft-lemmaansatz b").eq(0).text().strip()
        regex = [ ]
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_alts_1(self, html, term): return []

    def do_html_alts_2(self, html, term):
        doc = pq(html)("h2#etymwb > div").eq(0)
        alts = doc("div.etymwb-entry").prev("div")
        alts = sum([doc(a).text().split(u"·") for a in alts], [])
        alts = [a.strip() for a in alts]
        regex = [
            [r" ([0-9]+)$",r""],
        ]
        for r in regex: alts = [re.sub(r[0],r[1],a) for a in alts]
        return alts

    def do_html_definition_1(self, html, term):
        doc = pq(html)
        doc("button,img,audio,script,nav,ul.nav,h2").remove()
        doc("div.dwdswb-quelle").remove()
        doc("span.automatic-trennung").remove()
        doc("span.hyphinput").remove()
        doc("div.etymwb-quelle").remove()
        for div in doc("div.glyphicon"):
            doc(div).replaceWith("&gt;")
        for div in doc("div.dwdswb-ft-blocks"):
            for d in doc(div).find("div.dwdswb-ft-block"):
                replacement = doc(d).html()
                t = doc(d).find("span.dwdswb-ft-blocklabel").text()
                if t == "Wortbildung":
                    replacement = None
                elif t == "Worttrennung":
                    doc(d).find("span.dwdswb-ft-blocklabel") \
                        .replaceWith("; <i>Worttrennung:</i>")
                    replacement = doc(d).html()
                doc(d).replaceWith("" if replacement == None else replacement)
            doc(div).replaceWith(doc(div).html())
        doc("span.dwdswb-ft-blocklabel").remove()
        for div in doc("div.dwdswb-block-label,span.dwdswb-fundstelle-autor"):
            doc(div).replaceWith(
                doc("<span/>").css("font-variant","small-caps")
                    .html(doc(div).html()).outerHtml()
            )
        for div in doc("div.dwdswb-kompetenzbeispiel,div.dwdswb-beleg"):
            doc(div).replaceWith(doc(div).html() + "; ")
        for span in doc("span.dwdswb-stichwort,h1"):
            doc(span).replaceWith(
                doc("<b/>").html(doc(span).html()).outerHtml()
            )
        for span in doc("span.dwdswb-paraphrase"):
            doc(span).replaceWith(
                doc("<i/>").html(doc(span).html()).outerHtml()
            )
        for span in doc("span.dwdswb-einschraenkung"):
            doc(span).replaceWith(
                doc("<i/>").css("color","#0087C2")
                    .html(doc(span).html()).outerHtml()
                    .replace(u"»",'<b style="font-style:normal;">')
                    .replace(u"«",'</b>')
            )
        for span in doc("div.dwdswb-lesart-n"):
            doc(span).replaceWith(
                doc("<b/>").css("color","#0087C2")
                    .html(doc(span).html()).outerHtml()
            )
        for span in doc("span.dwdswb-definition"):
            doc(span).replaceWith(
                doc("<span/>").css("color","#0087C2")
                    .html(doc(span).html()).outerHtml()
            )
        for span in doc("span.dwdswb-bedeutungsebene,span.dwdswb-fachgebiet,"\
                       +"span.dwdswb-stilebene,span.dwdswb-stilfaerbung"):
            doc(span).replaceWith(
                doc("<b/>").css("color","#595")
                    .html(doc(span).html()).outerHtml()
            )
        for span in doc("span.dwdswb-fundstelle"):
            doc(span).replaceWith(
                doc("<b/>").css("color","#777")
                    .html(doc(span).html()).outerHtml()
            )
        for span in doc("span.dwdswb-fundstelle-titel"):
            doc(span).replaceWith(
                ", " + doc("<i/>").html(doc(span).html()).outerHtml()
            )
        for span in doc("span.dwdswb-fundstelle-stelle"):
            doc(span).replaceWith(", " + doc(span).html())
        for span in doc("span.dwdswb-grammatik"):
            doc(span).replaceWith(
                doc("<span/>").css("color","#800")
                    .html(doc(span).html()).outerHtml()
            )
        for span in doc("span.dwdswb-definition-spezifizierung"):
            doc(span).replaceWith(
                doc("<b/>").css("color","#800")
                    .html(doc(span).html()).outerHtml()
            )
        for a in doc("a:not([href])"):
            replacement = doc(a).html()
            doc(a).replaceWith("" if replacement == None else replacement)
        for a in doc("a"):
            if doc(a).text().strip() == "": doc(a).replaceWith(doc(a).text())
            else:
                href = "bword://%s" % doc(a).text().strip(". ").lower()
                doc(a).attr("href", href)
        for div in doc("div[role=tabpanel]"):
            doc(div).replaceWith(
                doc("<p/>").html(doc(div).html()).outerHtml()
            )
        naked = [
            "span.dwdswb-ft-blocktext",
            "span.hyphenation",
            "span.dwdswb-definitionen",
            "span.dwdswb-belegtext",
            "span.dwdswb-diasystematik",
            "span#relation-block-1",
            "span.dwdswb-verweis",
            "div.dwdswb-artikel",
            "div.dwdswb-lesart",
            "div.dwdswb-lesart-content",
            "div.dwdswb-lesart-def",
            "div.dwdswb-ft",
            "div.dwdswb-lesarten",
            "div.dwdswb-verwendungsbeispiele",
            "div.dwdswb-verweise",
            "div.dwdswb-formangabe",
            "div.more-block",
            "div.tab-content",
        ]
        for lbl in naked:
            old_html = ""
            while old_html != doc.html():
                old_html = doc.html()
                el = doc(lbl).eq(0)
                replacement = doc(el).html()
                doc(el).replaceWith("" if replacement == None else " " + replacement)
        old_html = ""
        while old_html != doc.html():
            old_html = doc.html()
            for el in doc("div,span"):
                txt = doc(el).text().strip()
                if txt in ["","Aussprache"]: doc(el).remove()
        doc("*").removeAttr("class").removeAttr("id") \
            .removeAttr("onclick").removeAttr("data-id")
        html = " ".join(doc("body").html().strip().split())
        regex = [
            [u"↗",r""],
            [r" +",r" "],
        ]
        for r in regex: html = re.sub(r[0],r[1],html)
        return html

    def do_html_definition_2(self, html, term):
        doc = pq(html)("h2#etymwb > div").eq(0)
        for div in doc("div.etymwb-entry"):
            doc(div).replaceWith(
                doc("<p/>").html(doc(div).html()).outerHtml()
            )
        doc("div").remove()
        doc("hr").remove()
        for span in doc("span.etymwb-mentioned"):
            doc(span).replaceWith(
                doc("<i/>").html(doc(span).text()).outerHtml()
            )
        for span in doc("span.etymwb-gramgrp"):
            doc(span).replaceWith(
                doc("<i/>").html(doc(span).text()).outerHtml()
            )
        for span in doc("span.etymwb-author"):
            doc(span).replaceWith(
                doc("<span/>").css("font-variant","small-caps")
                    .html(doc(span).text()).outerHtml()
            )
        for span in doc("span.etymwb-orth"):
            doc(span).replaceWith(
                doc("<b/>").html(doc(span).html()).outerHtml()
            )
        for span in doc("span.etymwb-bibl,span.etymwb-headword"):
            doc(span).replaceWith(doc(span).html())
        for a in doc("a"):
            if doc(a).text().strip() == "": doc(a).replaceWith(doc(a).text())
            else:
                href = "bword://%s" % doc(a).text().strip(". ").lower()
                doc(a).attr("href", href)
        doc("*").removeAttr("class").removeAttr("id")
        html = " ".join(doc.html().strip().split())
        repl = [
            [u"↗",""],
        ]
        for r in repl: html = html.replace(r[0], r[1])
        return html
