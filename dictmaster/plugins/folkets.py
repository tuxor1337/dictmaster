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
import sys

from pyquery import PyQuery as pq

from dictmaster.util import FLAGS
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import Fetcher
from dictmaster.stages.processor import HtmlContainerProcessor

WORD_CLASS = {
    "en": {
        "pp": "preposition",
        "nn": "substantiv",
        "ab": "adverb",
        "jj": "adjektiv",
        "abbrev": u"förkortning",
        "pn": "pronomen",
        "vb": "verb",
        "in": "interjektion",
        "rg": "grundtal",
        "prefix": u"förled",
        "suffix": u"suffix",
        "ie": u"infinitivmärke",
        "article": "artikel",
        "pm": "egennamn",
        "kn": "konjunktion",
        "hp": u"frågande/relativt pronomen",
        "ps": "possessiv",
        "sn": "subjunktion",
        "pc": "particip",
        u"hjälpverb": u"hjälpverb",
        "latin": "latin",
        "ro": "ordningstal",
    },
    "sv": {
        "sn": "subordinating conjunction",
        "pp": "preposition",
        "nn": "noun",
        "ab": "adverb",
        "jj": "adjective",
        "abbrev": "abbreviation",
        "pn": "personal and indefinite pronoun",
        "vb": "verb",
        "in": "interjection",
        "rg": "cardinal number",
        "prefix": "prefix in compound",
        "kn": "conjunction",
        "ie": "infinitival marker",
        "article": "article",
        "pm": "proper noun",
        "suffix": "suffix",
        "hp": "wh-pronoun",
        "ps": "possessive pronoun",
        "pc": "participle",
        "ro": "ordinal number",
        "latin": "latin",
        u"hjälpverb": u"auxiliary verb",
    }
}

TAG_NAMES = {
    "en": {
        "example": "Exempel",
        "idiom": "Idiom",
        "phonetic": "Uttal",
        "definition": "Definition",
        "synonym": "Synonymer",
        "use": u"Användning",
        "derivation": "Avledningar",
        "paradigm": u"Böjningar",
        "explanation": u"Förklaring",
        "see": "Se",
        "grammar": "Grammatikkommentar",
        "variant": "Variantform",
        "related": "Relaterade ord",
        "compound": u"Sammansättningar",
    },
    "sv": {
        "example": "Example",
        "phonetic": "Pronunciation",
        "see": "See",
        "definition": "Definition",
        "idiom": "Idiom",
        "explanation": "Explanation",
        "synonym": "Synonyms",
        "derivation": "Derivations",
        "paradigm": "Inflections",
        "use": "Use",
        "grammar": "Grammar comment",
        "variant": "Variant",
        "related": "Related words",
        "compound": "Compounds",
    }
}

FLAG_IMG = { "sv": ['flag_18x12_sv.png', 'flag_18x12_en.png'] }
FLAG_IMG["en"] = FLAG_IMG["sv"][::-1]

POPTS_DEFAULT = ["Sv-En"]

class Plugin(BasePlugin):
    _folkets_lang = ""
    def __init__(self, dirname, popts=POPTS_DEFAULT):
        if len(popts) != 1 or popts[0] not in ["Sv-En", "En-Sv"]:
            sys.exit("Provide lang argument, either Sv-En or En-Sv!")
        self._folkets_lang = popts[0]
        super(Plugin, self).__init__(os.path.join(dirname, self._folkets_lang))
        self.dictname = u"Folkets lexikon %s, ©folkets-lexikon.csc.kth.se"
        self.dictname = self.dictname % self._folkets_lang
        self.stages['Fetcher'] = Fetcher(self)
        self.stages['Processor'] = FolketsProcessor("word", self)

    def post_setup(self, cursor):
        for flag_file in FLAG_IMG["sv"]:
            res_dirname = os.path.join(self.output_directory, "res")
            flag_path = os.path.join(res_dirname, flag_file)
            flag_url = "http://folkets-lexikon.csc.kth.se/folkets/grafik/"+flag_file
            if not os.path.exists(flag_path):
                data = self.download_retry(flag_url)
                with open(flag_path, "wb") as img_file:
                    img_file.write(data)
        url = u"http://folkets-lexikon.csc.kth.se/folkets/folkets_%s_public.xml"
        url = url % self._folkets_lang.lower().replace("-","_")
        cursor.execute('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', (url, FLAGS["RAW_FETCHER"]))

class FolketsProcessor(HtmlContainerProcessor):
    def do_html_term(self, doc):
        term = doc.attr("value")
        return term

    def do_html_definition(self, html, term):
        d = pq(html)
        lang = html.attr("lang")
        head = '<img src="%s" /> <b>%s</b>' % (FLAG_IMG[lang][0], term)
        if html.attr("class"):
            classes = [WORD_CLASS[lang][cl.strip()] for cl in html.attr("class").split(",")]
            head += " %s" % ", ".join(classes)
        if html.attr("comment"):
            head += " (<i>%s</i>)" % html.attr("comment")

        # article body
        art_html = ""

        # translations first:
        for tr in html.children("translation"):
            tr_html = '<img src="%s" /> <b>%s</b>' % (FLAG_IMG[lang][1], d(tr).attr("value"))
            if d(tr).attr("comment"):
                tr_html += " [<i>%s</i>]" % d(tr).attr("comment")
            art_html += d("<p/>").html(tr_html).outerHtml()
        html.children("translation").remove()

        tag_html_dict = dict()

        tag_html_dict["phonetic"] = []
        for ph in html.children("phonetic"):
            tag_html_dict["phonetic"].append("[%s]" % d(ph).attr("value"))
        html.find("phonetic").remove()

        tag_html_dict["paradigm"] = []
        for par in html.children("paradigm"):
            tag_html_dict["paradigm"] += [d(inf).attr("value") for inf in d(par).find("inflection")]
        html.children("paradigm").remove()

        for tag in ["synonym", "use", "definition", "grammar", "variant", \
                    "explanation", "example", "idiom", "derivation", \
                    "compound", "related"]:
            tag_html_dict[tag] = []
            for el in html.children(tag):
                el_html = d(el).attr("value")
                if d(el).find("translation"):
                    el_html += ' <span style="' \
                            +      'color:#4682B4;' \
                            +      'font-style:italic' \
                            +  '">%s</span>' \
                            % d(el).find("translation").attr("value")
                # ignore d(el).attr("inflection") for now...
                tag_html_dict[tag].append(el_html)
            html.children(tag).remove()

        tag_html_dict["see"] = []
        for see in html.children("see"):
            if d(see).attr("type") != "saldo" and ".swf" != d(see).attr("value")[-4:]:
                see_html = '<a href="bword://%(ref)s">%(ref)s</a>' % {
                    "ref": d(see).attr("value")
                }
                tag_html_dict["see"].append(see_html)
        html.children("see").remove()

        for tag in ["phonetic", "paradigm", "synonym", "use", "definition", \
                    "grammar", "variant", "explanation", "example", "idiom", \
                    "derivation", "compound", "related", "see"]:
            values = tag_html_dict[tag]
            if len(values) == 0:
                continue
            tag_html = ""
            if tag == "see":
                tag_html += "<b>%s</b> " % TAG_NAMES[lang][tag]
            else:
                tag_html += "<b>%s:</b> " % TAG_NAMES[lang][tag]
            tag_html += ", ".join(values)
            art_html += d("<p/>").html(tag_html).outerHtml()

        # don't know what to do with these:
        html.children("url").remove()

        # check if something hasn't been processed
        if html.html() and html.html().strip():
            print(html.html().strip())

        return d("<div/>").html(
            d("<p/>").html(head).outerHtml() + art_html
        ).outerHtml().strip()

