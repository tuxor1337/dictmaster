# -*- coding: utf-8 -*-
#
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

from dictmaster.util import html_container_filter, words_to_db
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.processor import HtmlContainerProcessor

class Plugin(BasePlugin):
    def __init__(self, popts, dirname):
        if len(popts) == 0 or not os.path.exists(popts[0]):
            sys.exit("Provide full path to (existing) word list file!")
        self.word_file = popts[0]
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = u"Oxford Dictionaries Online - British & World English"
        self.stages['Fetcher'] = OxfordFetcher(self, threadcnt=10)
        self.stages['Processor'] = OxfordProcessor("div.entryPageContent", self)

    def post_setup(self, cursor):
        words_to_db(self.word_file, cursor, ("utf-8", "utf-8"),)

class OxfordFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread):
        def filter_data(self, data):
            if data == None \
            or '<div class="entryPageContent">' not in data:
                return None
            data = " ".join(data.split())
            repl = [ ]
            for r in repl: data = data.replace(r[0], r[1])
            regex = [
                [r"<![^>]*>", ""]
            ]
            for r in regex: data = re.sub(r[0], r[1], data)
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(data, parser=parser))
            return doc("div.responsive_cell_center").html()

        def parse_uri(self, uri):
            return "http://www.oxforddictionaries.com/definition/english/%s"%uri

class OxfordProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        term = doc(".pageTitle").eq(0).text().strip()
        regex = [
            [r"\s([0-9]+)$",r"(\1)"]
        ]
        for r in regex: term = re.sub(r[0], r[1], term)
        print(term)
        return term

    def do_html_alts(self, doc, term):
        return [doc(h).text().strip() for h in doc("section.subEntryBlock h4")]

    def do_html_definition(self, html, term):
        doc = pq(html)
        doc("img").remove()
        doc("script").remove()
        doc("h1").remove()
        doc("div.senses").remove()
        doc("div.breadcrumb").remove()
        doc("div.etymology").remove()
        doc("div.responsive_hide_on_smartphone").remove()
        doc("div.responsive_hide_on_non_smartphone").remove()
        doc("div.audio_play_button").remove()
        doc("a.moreInformationSynonyms").remove()
        doc("div.entrySynList").remove()
        doc("div.am-default").remove()
        doc("i.icon-top-word").remove()
        doc("a.back-to-top").remove()
        doc("li.dictionary_footer").remove()
        doc(".pageTitle").remove()
        for div in doc("div.top1000"):
            doc(div).replaceWith(
                doc("<span/>").css("color","#0BE")
                .html(doc(div).html()).outerHtml()+" "
            )
        for div in doc("div.headpron"):
            doc(div).replaceWith(
                doc("<span/>").css("color","#A00")
                .html(doc(div).html().replace("Pronunciation:",""))
                .outerHtml()+" "
            )
        for s in doc("span.headlinebreaks"):
            doc(s).replaceWith("<b>%s</b>"%doc(s).find(".linebreaks").text())
        for s in doc("strong.wordForm"):
            doc(s).replaceWith("<b>%s</b> " % doc(s).html())
        for s in doc("span.partOfSpeech"):
            doc(s).replaceWith(
                doc("<b/>").css("color","#777")
                .css("text-transform","uppercase")
                .html(doc(s).html()).outerHtml()
            )
        for s in doc("em.transivityStatement, em.languageGroup"):
            doc(s).replaceWith(
                doc("<span/>").css("color","#F82")
                .html(doc(s).html()).outerHtml()
            )
        for h in doc("h3"):
            doc(h).replaceWith("<br/><b>%s:</b> " % doc(h).html())
        for h in doc("strong"):
            doc(h).replaceWith("<b>%s</b> " % doc(h).html())
        doc("div.moreInformation").remove()
        for d in doc("dt"):
            replacement = "<b>%s</b> "%doc(d).find("h4").text()
            doc(d).find("div").remove()
            doc(d).replaceWith(replacement+doc(d).html())
        for d in doc("dd"):
            replacement = "".join(doc(div).html() for div in doc(d).find("div"))
            doc(d).replaceWith(replacement)
        for d in doc("dl"): doc(d).replaceWith(doc(d).html())
        for div in doc("div.msDict"):
            doc(div).replaceWith(doc(div).html())
        for span in doc("span.iteration"):
            doc(span).replaceWith("<b>%s</b> "%doc(span).text().strip())
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
        for p in doc("p,section"):
            if doc(p).text().strip() == "": doc(p).remove()
        doc("i.reg").css("color","#F82")
        doc("*").removeAttr("class")
        result = doc("header").html()
        result = result if result != None else ""
        result += " ".join(doc(s).html() for s in doc("section"))
        result = re.sub(r"</?(div|p)[^>]*>"," ",result)
        return result.strip()

