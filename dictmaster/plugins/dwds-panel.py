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
    "147": "Digitales Wörterbuch der deutschen Sprache",
    "148": "Etymologisches Wörterbuch © Dr. Wolfgang Pfeifer",
}

POPTS_DEFAULT = ["thirdparty/wordlists/deu/dwds.txt","147"]

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
            sys.exit("Panel ID {} is not supported. {}".format(
                self.panelid, list_panel_ids()
            ))
        super().__init__(os.path.join(dirname, self.panelid))
        self.dictname = DICTNAMES[self.panelid]
        self.stages['Fetcher'] = DWDSFetcher(self)
        self.stages['Processor'] = DWDSProcessor(self)

    def post_setup(self, cursor):
        self.set_name(self.dictname, cursor=cursor)
        words_to_db(self.word_file, cursor, ("utf-8", "utf-8"))

class DWDSFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data, uri):
            if data == None or len(data) < 2:
                 return None
            data = data.decode("utf-8")
            if '<div id="ddc_panel_' not in data \
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
        super().__init__(plugin, threadcnt=10)
        self.FetcherThread.parse_uri = lambda fthread, uri: \
            "http://eins.dwds.de/panel/get/%s/?qu=%s"%(plugin.panelid,uri)

class DWDSProcessor(HtmlContainerProcessor):
    def __init__(self, plugin):
        super().__init__("", plugin, singleton=True)
        self.do_html_definition = getattr(self, "do_html_definition_%s"%plugin.panelid)
        self.do_html_alts = getattr(self, "do_html_alts_%s"%plugin.panelid)

    def do_html_term(self, doc):
        term = doc("span.wb_lzga").eq(0).text().strip()
        regex = [
            [r" ([0-9]+)$",r"(\1)"]
        ]
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_alts_147(self, dt_html, html, term): return []

    def do_html_alts_148(self, dt_html, html, term):
        doc = pq(html)
        regex = [
            [r" ([0-9]+)$",r"(\1)"],
            ["\xb2","(2)"],
            ["\xb3","(3)"]
        ]
        alts = [doc(a).text() for a in doc("span.wb_lzga_min a")]
        for r in regex: alts = [re.sub(r[0],r[1],a) for a in alts]
        for a in alts+[term]:
            m = re.search(r"^(.*)\([0-9]+\)$", a)
            if m != None:
                 alts.extend([m.group(1),m.group(1).lower()])
        return alts

    def do_html_definition_147(self, dt_html, html, term):
        doc = pq(html)
        doc("img,audio,script,embed").remove()
        doc("span.wb_lzga").remove()
        doc("div[style='float:right;']").remove()
        doc("div.hidden_data_32").remove()
        doc("*").removeAttr("style")
        doc("span.wb_gram").css("color","#800")

        doc_rewrap_els(doc, "span.wb_bp", "<b/>")
        doc_strip_els(doc, "div.base_panel_header div")
        doc_rewrap_els(doc, "div.base_panel_header", "<p/>")
        doc_strip_els(doc, "div.wb_container_zone_s")
        doc_strip_els(doc, "div.shown_data_32")
        doc_rewrap_els(doc, "div.dwdswb2_snippet", "<p/>",
                       prefix="<i>", suffix="</i>", textify=True)
        doc_rewrap_els(doc, "div.wb_zone_s p", "<span/>",
                       css=[["background-color", "#dde"          ],
                            ["padding",          "0px 4px"       ],
                            ["border-top",       "1px #fff solid"]])
        doc_strip_els(doc, "div.wb_zone_s div")

        # links to related articles
        doc_strip_els(doc, "a:not([href])")
        doc_strip_els(doc, "a:empty")
        fun = lambda el, val: "bword://%s" % doc(el).text().strip(". ").lower()
        doc_replace_attr(doc, "a", "href", fun)

        old_html = ""
        while old_html != doc.html():
            old_html = doc.html()
            for el in doc("div,span,p"):
                txt = doc(el).text().strip()
                if txt in ["","Aussprache"]:
                     doc(el).remove()

        # Only preserve "related words" section if it's the only section
        if doc("div.wb_zone_v").prevAll().text().strip() != "":
            doc("div.wb_zone_v").remove()

        doc("*").removeAttr("class").removeAttr("id").removeAttr("onclick")
        html = doc("body > div").html()
        html = "" if html is None else html
        return " ".join(html.strip().split())

    def do_html_definition_148(self, html, term):
        doc = pq(html)("div.wb_container_zone_s")
        for a in doc("a"):
            if doc(a).text().strip() == "":
                 doc(a).replaceWith(doc(a).text())
            else:
                href = "bword://%s" % doc(a).text().strip(". ").lower()
                doc(a).attr("href", href)
        doc("*").removeAttr("class").removeAttr("id")
        return " ".join(doc.html().strip().split())

