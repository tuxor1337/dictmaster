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
import os
import sys

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import words_to_db
from dictmaster.replacer import *
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.processor import HtmlContainerProcessor

DICTNAMES = {
    "1": u"Wörterbuch der deutschen Gegenwartssprache",
    "2": u"Etymologisches Wörterbuch © Dr. Wolfgang Pfeifer",
}

POPTS_DEFAULT = ["thirdparty/wordlists/deu/dwds.txt","1"]

def list_panel_ids():
    return "Currently, the following panel IDs (resp. dictionaries) are supported:\n" \
        + "\n".join(["%s (%s)" % i for i in DICTNAMES.items()])

class Plugin(BasePlugin):
    panelid = None

    def __init__(self, dirname, popts=POPTS_DEFAULT):
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
        super(Plugin, self).__init__(os.path.join(dirname, self.panelid))
        self.dictname = DICTNAMES[self.panelid]
        self.stages['Fetcher'] = DWDSFetcher(self)
        self.stages['Processor'] = DWDSProcessor(self)

    def post_setup(self, cursor):
        words_to_db(self.word_file, cursor, ("utf-8", "utf-8"))

class DWDSFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data, uri):
            if data == None or len(data) < 2: return None
            data = data.decode("utf-8")
            if '<h1 class="dwdswb-ft-lemmaansatz' not in data \
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

    def do_html_alts_1(self, dt_html, html, term): return []

    def do_html_alts_2(self, dt_html, html, term):
        doc = pq(html)("h2#etymwb > div").eq(0)
        alts = doc("div.etymwb-entry").prev("div")
        alts = sum([doc(a).text().split(u"·") for a in alts], [])
        alts = [a.strip() for a in alts]
        regex = [
            [r" ([0-9]+)$",r""],
        ]
        for r in regex: alts = [re.sub(r[0],r[1],a) for a in alts]
        return alts

    def do_html_definition_1(self, dt_html, html, term):
        doc = pq(html)
        doc("button,img,audio,script,nav,ul.nav,h2").remove()
        doc("div.dwdswb-quelle,div.gb-quelle,div.wp-quelle").remove()
        doc("div.dwdswb-illustration").remove()
        doc("div.modal").remove()
        doc("p.bg-warning").remove()
        doc("div.dwds-gb-list").remove()
        doc("div.citation-help").remove()
        doc("span.automatic-trennung").remove()
        doc("span.hyphinput").remove()
        doc("div.etymwb-quelle").remove()

        doc_replace_els(doc, "div.glyphicon", lambda el: "&gt;")

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

        doc_rewrap_els(doc, "div.dwdswb-block-label,span.dwdswb-fundstelle-autor",
                       "<span/>", css=[["font-variant","small-caps"]])
        doc_strip_els(doc, "div.dwdswb-kompetenzbeispiel,div.dwdswb-beleg",
                      suffix="; ")
        doc_rewrap_els(doc, "span.dwdswb-stichwort,h1", "<b/>")
        doc_rewrap_els(doc, "span.dwdswb-paraphrase", "<i/>")
        doc_rewrap_els(doc, "span.dwdswb-einschraenkung", "<i/>",
                       css=[["color","#0087C2"]],
                       regex=[["»",'<b style="font-style:normal;">'],
                              ["«",'</b>']])
        doc_rewrap_els(doc, "div.dwdswb-lesart-n", "<b/>",
                       css=[["color","#0087C2"]])
        doc_rewrap_els(doc, "span.dwdswb-definition", "<span/>",
                       css=[["color","#0087C2"]])
        doc_rewrap_els(doc, "span.dwdswb-bedeutungsebene,span.dwdswb-fachgebiet,"\
                            +"span.dwdswb-stilebene,span.dwdswb-stilfaerbung",
                       "<b/>", css=[["color","#595"]])
        doc_rewrap_els(doc, "span.dwdswb-fundstelle", "<b/>",
                       css=[["color","#777"]])
        doc_rewrap_els(doc, "span.dwdswb-fundstelle-titel", "<i/>", prefix=", ")
        doc_strip_els(doc, "span.dwdswb-fundstelle-stelle", prefix=", ", block=False)
        doc_rewrap_els(doc, "span.dwdswb-grammatik", "<span/>",
                       css=[["color","#800"]])
        doc_rewrap_els(doc, "span.dwdswb-definition-spezifizierung", "<b/>",
                       css=[["color","#800"]])

        # links to related articles
        doc_strip_els(doc, "a:not([href])")
        doc_strip_els(doc, "a:empty")
        fun = lambda el, val: "bword://%s" % doc(el).text().strip(". ").lower()
        doc_replace_attr(doc, "a", "href", fun)

        doc_rewrap_els(doc, "div[role=tabpanel]", "<p/>")
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
        for lbl in naked: doc_strip_els(doc, lbl)

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
            [r"\s*;\s*$",r""],
            [r"\s+;\s+",r"; "],
        ]
        for r in regex: html = re.sub(r[0],r[1],html)
        return html

    def do_html_definition_2(self, html, term):
        doc = pq(html)("h2#etymwb > div")
        if len(doc) == 0: return ""
        doc = doc.eq(0)
        doc_rewrap_els(doc, "div.etymwb-entry", "<p/>")
        doc("div").remove()
        doc("hr").remove()
        doc_rewrap_els(doc, "span.etymwb-mentioned", "<i/>")
        doc_rewrap_els(doc, "span.etymwb-gramgrp", "<i/>")
        doc_rewrap_els(doc, "span.etymwb-author", "<span/>",
                       css=[["font-variant","small-caps"]], textify=True)
        doc_rewrap_els(doc, "span.etymwb-orth", "<b/>")
        doc_strip_els(doc, "span.etymwb-bibl,span.etymwb-headword", block=False)

        # links to related articles
        doc_strip_els(doc, "a:not([href])")
        doc_strip_els(doc, "a:empty")
        fun = lambda el, val: "bword://%s" % doc(el).text().strip(". ").lower()
        doc_replace_attr(doc, "a", "href", fun)

        doc("*").removeAttr("class").removeAttr("id")
        html = " ".join(doc.html().strip().split())
        repl = [
            [u"↗",""],
        ]
        for r in repl: html = html.replace(r[0], r[1])
        return html
