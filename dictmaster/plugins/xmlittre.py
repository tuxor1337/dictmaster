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

import os
import re
import sqlite3

from pyquery import PyQuery as pq

from dictmaster.util import html_container_filter, FLAGS
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import ZipFetcher, Unzipper
from dictmaster.stages.processor import HtmlContainerProcessor

class Plugin(BasePlugin):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = u"XMLittré, ©littre.org"
        self.stages['Fetcher'] = ZipFetcher(self)
        self.stages['Unzipper'] = XmlittreUnzipper(self)
        self.stages['Processor'] = XmlittreProcessor("entree", self, auto_synonyms=False)

    def post_setup(self, cursor):
        url = "https://bitbucket.org/Mytskine/xmlittre-data/get/master.zip"
        cursor.execute('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', (url, FLAGS["ZIP_FETCHER"]))

class XmlittreUnzipper(Unzipper):
    def zfile_filter(self, zfilename): return zfilename[-4:] == ".xml"

class XmlittreProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        term = doc.attr("terme").lower()
        return term

    def do_html_definition(self, html, term):
        d = pq(html)
        for e in html.find("entete"):
            d(e).replaceWith(
                d("<p/>").html(d(e).html()).outerHtml()
            )
        for res in html.find(u"résumé"):
            for var in d(res).find("variante"):
                if not d(var).attr("num"):
                    d(var).replaceWith(d(var).html())
                else:
                    d(var).replaceWith(
                        d("<p/>").html(
                            d(var).attr("num") + u"° " + d(var).html()
                        ).outerHtml()
                    )
            d(res).replaceWith(
                d("<div/>").html(d(res).html()).outerHtml()
            )
        while len(html.find("variante")) > 0:
            for var in html.find("variante"):
                if not d(var).attr("num") or not d(var).attr("num").isdigit():
                    d(var).replaceWith(d(var).html())
                else:
                    num = d("<span/>").attr("style", \
                          "background-color:#464696;" \
                        + "color:#fff;" \
                        + "font-weight:bold;" \
                        + "padding:0.1ex 0.7ex;" \
                        + "margin:0 0.8ex 0 0;" \
                        ).text(d(var).attr("num"))
                    d(var).replaceWith(
                        d("<p/>").html(
                            d(num).outerHtml() + d(var).html()
                        ).outerHtml()
                    )
        while len(html.find("indent")) > 0:
            for ind in html.find("indent"):
                d(ind).replaceWith(
                    d("<p/>").html(d(ind).html()).outerHtml()
                )
        while len(html.find("rubrique")) > 0:
            for rubr in html.find("rubrique"):
                h = d("<h2/>").text(d(rubr).attr("nom"))
                d(rubr).replaceWith(
                    d("<div/>").html(
                        d(h).outerHtml() + d(rubr).html()
                    ).outerHtml()
                )
        for pron in html.find("prononciation"):
            if not d(pron).html():
                d(pron).replaceWith("")
            else:
                d(pron).replaceWith(
                    d("<i/>").html("(" + d(pron).html() + ")").outerHtml()
                )
        for nat in html.find("nature"):
            d(nat).replaceWith(
                d("<b/>").html(d(nat).html()).outerHtml()
            )
        for cit in html.find("cit"):
            src = '<p style="font-style:normal;text-align:right">['
            if d(cit).attr("aut"):
                src += '<span style="color:#005A00;font-variant:small-caps">' \
                    +  d(cit).attr("aut") + '</span>'
                if d(cit).attr("ref"):
                    src += ", "
            if d(cit).attr("ref"):
                src += '<span style="color:#30A030;font-style:italic">' \
                    +  d(cit).attr("ref") + '</span>'
            src += ']</p>'
            cit_html = d(cit).html() if d(cit).html() != None else ""
            d(cit).replaceWith(
                d("<blockquote/>").html(
                     cit_html + src
                ).outerHtml()
            )
        for ex in html.find("exemple"):
            d(ex).replaceWith(
                d("<i/>").html(d(ex).html()).outerHtml()
            )
        for a in html.find("a"):
            d(a).attr("href", "bword://%s" % d(a).attr("ref"))
            d(a).removeAttr("ref")
        for sem in html.find("semantique"):
            d(sem).replaceWith(
                d("<i/>").html(d(sem).html()).outerHtml()
            )
        for c in html.find("corps"):
            d(c).replaceWith(
                d("<div/>").html(d(c).html()).outerHtml()
            )
        return html.html().strip()

