# -*- coding: utf-8 -*-

import re
from pyquery import PyQuery as pq

from dictmaster.util import html_container_filter, CancelableThread
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Fetcher
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        self.url_list = []
        self.dictname = "Dictionnaires de l’Académie française : 8ème édition"
        fetcher = Fetcher(self.output_directory,
            urls=self.url_list,
            filter_fct=html_container_filter("body > table", charset="windows-1252")
        )
        postprocessor = AcadfranProcessor(self)
        editor = Editor(
            output_directory=self.output_directory,
            plugin=self
        )
        self._stages = [
            AcadfranUrlFetcher(self),
            fetcher,
            postprocessor,
            editor
        ]

BASE_URL = "http://atilf.atilf.fr/dendien/scripts/generic"
STEP_SIZE = 100

class AcadfranUrlFetcher(CancelableThread):
    def __init__(self, plugin):
        super(AcadfranUrlFetcher, self).__init__()
        self.plugin = plugin

    def progress(self):
        if self._canceled:
            return "Sleeping..."
        return "Collecting URLs..."

    def run(self):
        url = "%s/showps.exe?p=main.txt;host=interface_academie8.txt;java=no;" % BASE_URL
        session_id = self.download_retry(url).replace("\n"," ").replace("\r","")
        session_id = re.sub(r".*;s=([0-9]*);.*", r"\1", session_id)

        url = "%s/cherche.exe?680;s=%s;;" % (BASE_URL, session_id)
        postdata = 'var0=&var2=%2A&var3=%2A%21%21%2A&var5=%2A%21%21%2A'
        #{ "var0" : "", "var2" : "*", "var3" : "*!!*", "var5" : "*!!*" }
        wordcount, r_var = re.sub(
            r".*;t=([0-9]+);r=([0-9]+);.*", r"\1,\2",
            self.download_retry(url,postdata)
        ).split(",")
        wordcount, r_var = int(wordcount), int(r_var)

        for i, j in enumerate(range(0,wordcount,STEP_SIZE)):
            if self._canceled:
                return
            url = "%s/affiche.exe?%d;s=%s;d=%d;f=%d,t=%d,r=%d;" \
                % (BASE_URL, 120+i, session_id, j+1, j+STEP_SIZE, wordcount, r_var)
            self.plugin.url_list.append(url)

class AcadfranProcessor(HtmlContainerProcessor):
    def __init__(self, plugin):
        super(AcadfranProcessor, self).__init__("tr > td > div", plugin, charset="windows-1252")

    def do_html_term(self, doc):
        term = doc("B b font[color=blue]").eq(0).text().strip().lower()
        return term

    def do_html_definition(self, html, term):
        html.html(
            re.sub(r"^ *\([0-9]+\) *", "", html.html())
        )
        doc = pq(html)
        heading = html.find("B b font[color=blue]").parents("b").parents("b")
        doc(heading).replaceWith(
            doc("<p/>").html(doc(heading).html()).outerHtml()
        )
        html.find("i").attr("style", "color:#3A4")
        for b in html.find("b b"):
            doc(b).replaceWith(
                doc("<span/>").html(doc(b).html()).outerHtml()
            )
        return re.sub(r" *<br?/?> *$", "", html.html().strip())
