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
        self.dictname = "Oxford Dictionaries Online - British & World English"
        fetcher = OxfordFetcher(
            self.output_directory,
            url_pattern="http://www.oxforddictionaries.com/definition/english/{word}",
            word_file=word_file,
            word_codec=("utf-8", "utf-8"),
            threadcnt=10
        )
        self._stages = [
            fetcher,
            OxfordProcessor("", self, singleton=True),
            Editor(plugin=self)
        ]

class OxfordFetcher(WordFetcher):
    class FetcherThread(WordFetcher.FetcherThread):
        def filter_data(self, data):
            if data == None or len(data) < 2 \
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
            return doc("div.entryPageContent").html().encode("utf-8")

class OxfordProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        term = doc("strong.pageTitle").eq(0).text().strip()
        regex = []
        for r in regex: term = re.sub(r[0], r[1], term)
        return term

    def do_html_alts(self, doc, term):
        alts = []
        for h in doc("section.subEntryBlock h4"):
            alts.append(doc(h).text().strip())
        return alts

    def do_html_definition(self, html, term):
        doc = pq(html)
        doc("img").remove()
        doc("script").remove()
        doc("h1").remove()
        doc("div.breadcrumb").remove()
        doc("div.etymology").remove()
        doc("div.responsive_hide_on_smartphone").remove()
        doc("div.responsive_hide_on_non_smartphone").remove()
        doc("div.audio_play_button").remove()
        doc("a.moreInformationSynonyms").remove()
        doc("div.entrySynList").remove()
        doc("div.am-default").remove()
        doc("li.dictionary_footer").remove()
        for h in doc("h3,strong"):
            doc(h).replaceWith("<p><b>%s</b></p>" % doc(h).html())
        for div in doc("div.moreInformation"):
            if doc(div).text() == None or doc(div).text().strip() == "": 
                doc(div).remove(); continue
            a = doc(div).children("a").eq(0)
            replacement = " <b>%s:</b> "%doc(a).html().strip()
            for li in doc(div).find("li"):
                replacement += "<i>\"%s\"</i>, "%doc(li).html()
            doc(div).replaceWith(replacement.strip(" ,"))
        for s in doc("section.etymology"):
            tmp = "".join(doc(p).html() for p in doc(s).find("p"))
            doc(s).html(tmp)
        for d in doc("dt"):
            replacement = "<b>%s</b><br />"%doc(d).find("h4").text()
            doc(d).find("div").remove()
            doc(d).replaceWith(replacement+doc(d).html())
        for d in doc("dd"):
            replacement = "".join(doc(div).html() for div in doc(d).find("div"))
            doc(d).replaceWith(replacement)
        for d in doc("dl"): doc(d).replaceWith(doc(d).html())
        for div in doc("div.msDict"):
            doc(div).replaceWith("<p>%s</p>" % doc(div).html())
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
        for p in doc("p"):
            if doc(p).text().strip() == "": doc(p).remove()
        doc("i.reg").css("color","#F82")
        doc("*").removeAttr("class")
        result = doc("header").html()
        result += "".join(doc(s).html() for s in doc("section"))
        return result.strip()

