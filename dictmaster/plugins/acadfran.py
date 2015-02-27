# -*- coding: utf-8 -*-

import re
from pyquery import PyQuery as pq

from dictmaster.util import html_container_filter, FLAGS
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import Fetcher
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

BASE_URL = "http://atilf.atilf.fr/dendien/scripts/generic"
STEP_SIZE = 100

class Plugin(PluginThread):
    acadfran_vars = None
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = u"Dictionnaires de l’Académie française : 8ème édition"

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
        self.acadfran_vars = {
            "r": r_var,
            "sid": session_id,
            "cnt": wordcount
        }
        fetcher = AcadfranFetcher(self, self.acadfran_vars)
        self._stages = [
            fetcher,
            AcadfranProcessor("tr > td > div", self),
            Editor(self)
        ]
        PluginThread.run(self)

    def post_setup(self, cursor):
        wordcount = self.acadfran_vars["cnt"]
        cursor.executemany('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', [(i, FLAGS["RAW_FETCHER"]) for i in range(0,wordcount,STEP_SIZE)])

class AcadfranFetcher(Fetcher):
    class FetcherThread(Fetcher.FetcherThread): pass
    def __init__(self, plugin, vars):
        super(AcadfranFetcher, self).__init__(plugin)
        def parse_uri_override(fthread, uri):
            uri = int(uri)
            return "{}/affiche.exe?{};s={};d={};f={},t={},r={};".format(
                BASE_URL,
                120+uri/20,
                vars["sid"],
                uri+1, uri+STEP_SIZE,
                vars["cnt"],
                vars["r"]
            )
        self.FetcherThread.parse_uri = parse_uri_override
        self.FetcherThread.filter_data = html_container_filter(
            "body > table", charset="windows-1252"
        )

class AcadfranProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        term = doc("B b font[color=blue]").eq(0).text().strip().lower()
        return term

    def do_html_definition(self, html, term):
        html.html(
            re.sub(r"^ *\([0-9]+\) *", "", html.html())
        )
        doc = pq(html)
        heading = html.find("B b font[color=blue]").parents("b").parents("b")
        doc(heading).replaceWith("<p>%s</p>"%doc(heading).html())
        for b in html.find("b b"): doc(b).replaceWith(doc(b).html())
        return re.sub(r" *<br?/?> *$", "", html.html().strip())

