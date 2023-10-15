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
import glob
import shutil

from pyquery import PyQuery as pq

from dictmaster.util import FLAGS
from dictmaster.plugin import BasePlugin
from dictmaster.stages.fetcher import ZipFetcher
from dictmaster.stages.unzipper import Unzipper
from dictmaster.stages.processor import HtmlContainerProcessor, Processor

# webster alternatives:
#
# http://machaut.uchicago.edu/?resource=Webster%27s&word=.*&use1913=on
# the regex .* will give all entries separated by <hr />
#
# http://www.gutenberg.org/ebooks/673
# very similar to the artfl version

"""
Format information from dico source code (c and lex files)
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/ent.c
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/grk.c
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/idxgcide.l
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/markup.l
"""

entities = {
    "Cced": "Ç",
    "uum": "ü",
    "eacute": "é",
    "acir": "â",
    "aum": "ä",
    "agrave": "à",
    "aring": "å",
    "ccedil": "ç",
    "cced": "ç",
    "ecir": "ê",
    "eum": "ë",
    "egrave": "è",
    "ium": "ï",
    "icir": "î",
    "igrave": "ì",
    "Aum": "Ä",
    "Aring": "Å",
    "Eacute": "È",
    "ae": "æ",
    "AE": "Æ",
    "ocir": "ô",
    "oum": "ö",
    "ograve": "ò",
    "oacute": "ó",
    "Oacute": "Ó",
    "ucir": "û",
    "ugrave": "ù",
    "uacute": "ú",
    "yum": "ÿ",
    "Oum": "Ö",
    "Uum": "Ü",
    "pound": "£",
    "aacute": "á",
    "iacute": "í",
    "frac23": "⅔",
    "frac13": "⅓",
    "frac12": "½",
    "frac14": "¼",
    "?": "<?>", # Place-holder for unknown or illegible character.
    "hand": "☞",   # pointing hand (printer's u"fist")
    "sect": "§",
    "amac": "ā",
    "nsm": "ṉ",   # u"n sub-macron"
    "sharp": "♯",
    "flat": "♭",
    "th": "th",
    "imac": "ī",
    "emac": "ē",
    "dsdot": "ḍ",   # Sanskrit/Tamil d dot
    "nsdot": "ṇ",   # Sanskrit/Tamil n dot
    "tsdot": "ṭ",   # Sanskrit/Tamil t dot
    "ecr": "ĕ",
    "icr": "ĭ",
    "ocr": "ŏ",
    "OE": "Œ",
    "oe": "œ",
    "omac": "ō",
    "umac": "ū",
    "ocar": "ǒ",
    "aemac": "ǣ",
    "ucr": "ŭ",
    "acr": "ă",
    "ymac": "ȳ",
    "asl": "a",   # FIXME: a u"semilong" (has a macron above with a short
    "esl": "e",   # FIXME: e u"semilong"
    "isl": "i",   # FIXME: i u"semilong"
    "osl": "o",   # FIXME: o u"semilong"
    "usl": "u",   # FIXME: u u"semilong"
    "adot": "ȧ",   # a with dot above
    "edh": "ð",
    "thorn": "þ",
    "atil": "ã",
    "etil": "ẽ",
    "itil": "ĩ",
    "otil": "õ",
    "util": "ũ",
    "ntil": "ñ",
    "Atil": "Ã",
    "Etil": "Ẽ",
    "Itil": "Ĩ",
    "Otil": "Õ",
    "Util": "Ũ",
    "Ntil": "Ñ",
    "ndot": "ṅ",
    "rsdot": "ṛ",
    "yogh": "ȝ",
    "deg": "°",
    "middot": "•",
    "root": "√",
# Greek alphabet
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "zeta": "ζ",
    "eta": "η",
    "theta": "θ",
    "iota": "ι",
    "kappa": "κ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "xi": "ξ",
    "omicron": "ο",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "sigmat": "ς",
    "tau": "τ",
    "upsilon": "υ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "digamma": "ϝ",
    "ALPHA": "Α",
    "BETA": "Β",
    "GAMMA": "Γ",
    "DELTA": "Δ",
    "EPSILON": "Ε",
    "ZETA": "Ζ",
    "ETA": "Η",
    "THETA": "Θ",
    "IOTA": "Ι",
    "KAPPA": "Κ",
    "LAMBDA": "Λ",
    "MU": "Μ",
    "NU": "Ν",
    "XI": "Ξ",
    "OMICRON": "Ο",
    "PI": "Π",
    "RHO": "Ρ",
    "SIGMA": "Σ",
    "TAU": "Τ",
    "UPSILON": "Υ",
    "PHI": "Φ",
    "CHI": "Χ",
    "PSI": "Ψ",
    "OMEGA": "Ω",
# Italic letters
    "AIT": "A",
    "BIT": "B",
    "CIT": "C",
    "DIT": "D",
    "EIT": "E",
    "FIT": "F",
    "GIT": "G",
    "HIT": "H",
    "IIT": "I",
    "JIT": "J",
    "KIT": "K",
    "LIT": "L",
    "MIT": "M",
    "NOT": "N",
    "OIT": "O",
    "PIT": "P",
    "QIT": "Q",
    "RIT": "R",
    "SIT": "S",
    "TIT": "T",
    "UIT": "U",
    "VIT": "V",
    "WIT": "W",
    "XIT": "X",
    "YIT": "Y",
    "ZIT": "Z",
    "ait": "a",
    "bit": "b",
    "cit": "c",
    "dit": "d",
    "eit": "e",
    "fit": "f",
    "git": "g",
    "hit": "h",
    "iit": "i",
    "jit": "j",
    "kit": "k",
    "lit": "l",
    "mit": "m",
    "not": "n",
    "oit": "o",
    "pit": "p",
    "qit": "q",
    "rit": "r",
    "sit": "s",
    "tit": "t",
    "uit": "u",
    "vit": "v",
    "wit": "w",
    "xit": "x",
    "yit": "y",
    "zit": "z",
# FIXME: Vowels with a double dot below. There`s nothing suitable in the Unicode
    "add": "a",
    "udd": "u",
    "ADD": "A",
    "UDD": "U",
# Accents
    "prime": "´",
    "bprime": "˝",
    "mdash": "—",
    "divide": "÷",
# Quotes
    "lsquo": "‘",
    "ldquo": "“",
    "rdquo": "”",
    "dagger": "†",
    "dag": "†",
    "Dagger": "‡",
    "ddag": "‡",
    "para": "§",
    "gt": ">",
    "lt": "<",
    "rarr": "→",
    "larr": "←",
    "schwa": "ə",
    "br": "\n",
    "and": "and",
    "or": "or",
    "sec": "˝"
}

xlit = [
    ["'A", "Ἀ"],
    ["'A,", "ᾈ"],
    ["'A^", "Ἆ"],
    ["'A`", "Ἄ"],
    ["'A~", "Ἂ"],
    ["'A~,", "ᾊ"],
    ["'A~,", "ᾌ"],
    ["'A~,", "ᾎ"],
    ["'E", "Ἐ"],
    ["'E`", "Ἔ"],
    ["'E~", "Ἒ"],
    ["'H", "Ἠ"],
    ["'H,", "ᾘ"],
    ["'H^", "Ἦ"],
    ["'H`", "Ἤ"],
    ["'H~", "Ἢ"],
    ["'H~,", "ᾚ"],
    ["'H~,", "ᾜ"],
    ["'H~,", "ᾞ"],
    ["'I", "Ἰ"],
    ["'I^", "Ἶ"],
    ["'I`", "Ἴ"],
    ["'I~", "Ἲ"],
    ["'O", "Ὀ"],
    ["'O`", "Ὄ"],
    ["'O~", "Ὂ"],
    ["'W", "Ὠ"],
    ["'W,", "ᾨ"],
    ["'W^", "Ὦ"],
    ["'W`", "Ὤ"],
    ["'W~", "Ὢ"],
    ["'W~,", "ᾪ"],
    ["'W~,", "ᾬ"],
    ["'W~,", "ᾮ"],
    ["'`O", "Ὄ"],
    ["'a", "ἀ"],
    ["'a,", "ᾀ"],
    ["'a^", "ἆ"],
    ["'a^,", "ᾆ"],
    ["'a`", "ἄ"],
    ["'a`,", "ᾄ"],
    ["'a~", "ἂ"],
    ["'a~,", "ᾂ"],
    ["'e", "ἐ"],
    ["'e`", "ἔ"],
    ["'e~", "ἒ"],
    ["'h", "ἠ"],
    ["'h,", "ᾐ"],
    ["'h^", "ἦ"],
    ["'h^,", "ᾖ"],
    ["'h`", "῎η"],
    ["'h`,", "ᾔ"],
    ["'h~", "ἢ"],
    ["'h~,", "ᾒ"],
    ["'i", "ἰ"],
    ["'i^", "ἶ"],
    ["'i`", "ἴ"],
    ["'i~", "ἲ"],
    ["'o", "ὀ"],
    ["'o`", "ὄ"],
    ["'o~", "ὂ"],
    ["'r", "ῤ"],
    ["'u", "ὐ"],
    ["'u^", "ὖ"],
    ["'u`", "ὔ"],
    ["'u~", "ὒ"],
    ["'w", "ὠ"],
    ["'w,", "ᾠ"],
    ["'w^", "ὦ"],
    ["'w^,", "ᾦ"],
    ["'w`", "ὤ"],
    ["'w`,", "ᾤ"],
    ["'w~", "ὢ"],
    ["'w~,", "ᾢ"],
    ["'y", "ὐ"],
    ["'y^", "ὖ"],
    ["'y`", "ὔ"],
    ["'y~", "ὒ"],
    ["A", "Α"],
    ["A", "Α"],
    ["A,", "ᾼ"],
    ["A`", "Ά"],
    ["A~", "Ἁ"],
    ["B", "Β"],
    ["CH", "Χ"],
    ["Ch", "Χ"],
    ["D", "Δ"],
    ["E", "Ε"],
    ["E", "Ε"],
    ["E`", "Έ"],
    ["E~", "Ἑ"],
    ["F", "Φ"],
    ["G", "Γ"],
    ["H", "Η"],
    ["H", "Η"],
    ["H,", "ῌ"],
    ["H`", "Ή"],
    ["H~", "Ἡ"],
    ["I", "Ι"],
    ["I", "Ι"],
    ["I`", "Ί"],
    ["I~", "Ἱ"],
    ["K", "Κ"],
    ["L", "Λ"],
    ["M", "Μ"],
    ["N", "Ν"],
    ["O", "Ο"],
    ["O", "Ο"],
    ["O`", "Ό"],
    ["O~", "Ὁ"],
    ["P", "Π"],
    ["PS", "Ψ"],
    ["Ps", "Ψ"],
    ["Q", "Θ"],
    ["R", "Ρ"],
    ["S", "Σ"],
    ["T", "Τ"],
    ["U", "Υ"],
    ["U", "Υ"],
    ["U`", "Ύ"],
    ["U~", "Ὑ"],
    ["W", "Ω"],
    ["W", "Ω"],
    ["W,", "ῼ"],
    ["W`", "Ώ"],
    ["W~", "Ὡ"],
    ["X", "Ξ"],
    ["Y", "Υ"],
    ["Y", "Υ"],
    ["Y`", "Ύ"],
    ["Y~", "Ὑ"],
    ["Z", "Ζ"],
    ["\"A", u"Ὰ"],
    ["\"A,", u"ᾉ"],
    ["\"A^", u"Ἇ"],
    ["\"A^,", u"ᾏ"],
    ["\"A`", u"Ἅ"],
    ["\"A`,", u"ᾍ"],
    ["\"A~", u"Ἃ"],
    ["\"A~,", u"ᾋ"],
    ["\"E", u"Ὲ"],
    ["\"E`", u"Ἕ"],
    ["\"E~", u"Ἓ"],
    ["\"H", u"Ὴ"],
    ["\"H,", u"ᾙ"],
    ["\"H^", u"Ἧ"],
    ["\"H^,", u"ᾟ"],
    ["\"H`", u"Ἥ"],
    ["\"H`,", u"ᾝ"],
    ["\"H~", u"Ἣ"],
    ["\"H~,", u"ᾛ"],
    ["\"I", u"Ὶ"],
    ["\"I^", u"Ἷ"],
    ["\"I`", u"Ἵ"],
    ["\"I~", u"Ἳ"],
    ["\"O", u"Ὸ"],
    ["\"O`", u"Ὅ"],
    ["\"O~", u"Ὃ"],
    ["\"R", u"Ῥ"],
    ["\"U", u"Ὺ"],
    ["\"U^", u"Ὗ"],
    ["\"U`", u"Ὕ"],
    ["\"U~", u"Ὓ"],
    ["\"W", u"Ὼ"],
    ["\"W,", u"ᾩ"],
    ["\"W^", u"Ὧ"],
    ["\"W^,", u"ᾯ"],
    ["\"W`", u"Ὥ"],
    ["\"W`,", u"ᾭ"],
    ["\"W~", u"Ὣ"],
    ["\"W~,", u"ᾫ"],
    ["\"Y", u"Ὺ"],
    ["\"Y^", u"Ὗ"],
    ["\"Y`", u"Ὕ"],
    ["\"Y~", u"Ὓ"],
    ["\"a", u"ἁ"],
    ["\"a,", u"ᾁ"],
    ["\"a^", u"ἇ"],
    ["\"a^,", u"ᾇ"],
    ["\"a`", u"ἄ"],
    ["\"a`", u"ἅ"],
    ["\"a`,", u"ᾅ"],
    ["\"a~", u"ἂ"],
    ["\"a~", u"ἃ"],
    ["\"a~,", u"ᾃ"],
    ["\"e", u"ἑ"],
    ["\"e`", u"ἕ"],
    ["\"e~", u"ἓ"],
    ["\"h", u"ἡ"],
    ["\"h,", u"ᾑ"],
    ["\"h^", u"ἧ"],
    ["\"h^,", u"ᾗ"],
    ["\"h`", u"ἤ"],
    ["\"h`", u"ἥ"],
    ["\"h`,", u"ᾕ"],
    ["\"h~", u"ἣ"],
    ["\"h~,", u"ᾓ"],
    ["\"i", u"ἱ"],
    ["\"i^", u"ἷ"],
    ["\"i`", u"ἵ"],
    ["\"i~", u"ἳ"],
    ["\"o", u"ὁ"],
    ["\"o`", u"ὅ"],
    ["\"o~", u"ὃ"],
    ["\"r", u"ῥ"],
    ["\"", u"ὑ"],
    ["\"u^", u"ὗ"],
    ["\"u`", u"ὕ"],
    ["\"u~", u"ὓ"],
    ["\"w", u"ὡ"],
    ["\"w,", u"ᾡ"],
    ["\"w^", u"ὣ"],
    ["\"w^", u"ὧ"],
    ["\"w^,", u"ᾧ"],
    ["\"w`", u"ὥ"],
    ["\"w`,", u"ᾥ"],
    ["\"w~,", u"ᾣ"],
    ["\"y", u"ὑ"],
    ["\"y^", u"ὗ"],
    ["\"y`", u"ὕ"],
    ["\"y~", u"ὓ"],
    ["a", "α"],
    ["a,", "ᾳ"],
    ["a^", "ᾶ"],
    ["a^,", "ᾷ"],
    ["a`", "ά"],
    ["a`,", "ᾴ"],
    ["a~", "ὰ"],
    ["a~,", "ᾲ"],
    ["b", "β"],
    ["ch", "χ"],
    ["d", "δ"],
    ["e", "ε"],
    ["e`", "έ"],
    ["e~", "ὲ"],
    ["f", "φ"],
    ["g", "γ"],
    ["h", "η"],
    ["h,", "ῃ"],
    ["h^", "ῆ"],
    ["h^,", "ῇ"],
    ["h`", "ή"],
    ["h`,", "ῄ"],
    ["h~", "ὴ"],
    ["h~,", "ῂ"],
    ["i", "ι"],
    ["i:", "ϊ"],
    ["i:^", "ῗ"],
    ["i:`", "ῒ"],
    ["i:`", "ΐ"],
    ["i^", "ῖ"],
    ["i^:", "ῗ"],
    ["i`", "ί"],
    ["i`:", "ῒ"],
    ["i`:", "ΐ"],
    ["i~", "ὶ"],
    ["k", "κ"],
    ["l", "λ"],
    ["m", "μ"],
    ["n", "ν"],
    ["o", "ο"],
    ["o`", "ό"],
    ["o~", "ὸ"],
    ["p", "π"],
    ["ps", "ψ"],
    ["q", "θ"],
    ["r", "ρ"],
    ["s", "σ"],
    ["t", "τ"],
    ["u", "υ"],
    ["u:", "ϋ"],
    ["u:^", "ῧ"],
    ["u:`", "ΰ"],
    ["u:~", "ῢ"],
    ["u^", "ῦ"],
    ["u^:", "ῧ"],
    ["u`", "ύ"],
    ["u`:", "ΰ"],
    ["u~", "ὺ"],
    ["u~:", "ῢ"],
    ["w", "ω"],
    ["w,", "ῳ"],
    ["w^", "ῶ"],
    ["w^,", "ῷ"],
    ["w`", "ώ"],
    ["w`,", "ῴ"],
    ["w~", "ὼ"],
    ["w~,", "ῲ"],
    ["x", "ξ"],
    ["y", "υ"],
    ["y:", "ϋ"],
    ["y:^", "ῧ"],
    ["y:`", "ΰ"],
    ["y:~", "ῢ"],
    ["y^", "ῦ"],
    ["y^:", "ῧ"],
    ["y`", "ύ"],
    ["y`:", "ΰ"],
    ["y~", "ὺ"],
    ["y~:", "ῢ"],
    ["z", "ζ" ]
]
class Plugin(BasePlugin):
    dictname = "GNU Collaborative International Dictionary of English"
    enumerate = False

    def __init__(self, dirname, popts=[]):
        super().__init__(dirname)
        self.stages['Fetcher'] = ZipFetcher(self)
        self.stages['Unzipper'] = GcideUnzipper(self)
        self.stages['Processor'] = GcideProcessor("p", self, charset="windows-1252")

    def post_setup(self, cursor):
        url = "ftp://ftp.halifax.rwth-aachen.de/gnu/gcide/gcide-latest.zip"
        cursor.execute('''
            INSERT INTO raw (uri, flag)
            VALUES (?,?)
        ''', (url, FLAGS["ZIP_FETCHER"]))

class GcideUnzipper(Unzipper):
    def zfile_filter(self, zfilename): return zfilename[-6:-1] == "CIDE."

class GcideProcessor(HtmlContainerProcessor):
    _last_container = None
    def append(self, dt, dd):
        term = self.do_html_term(dt)
        alts = self.do_html_alts(dd, term)
        definition = self.do_html_definition(dd, term)
        if not term.strip():
            if self._last_container == None:
                 return
            term, olddef, oldalts = self._last_container
            definition = olddef + self.do_html_definition(dd, term)
            alts.extend(oldalts)
        elif self._last_container != None:
            Processor.append(self, *self._last_container)
        self._last_container = (term, definition, alts)

    def process(self):
        HtmlContainerProcessor.process(self)
        if self._last_container != None:
            Processor.append(self, *self._last_container)

    def do_html_alts(self, dt_html, dd, term):
        d = pq(dd)
        alts = []
        regex = [[r"[\"`\*']",""]]
        for hw in d.find("hw"):
            candidate = d(hw).text().strip().lower()
            for r in regex:
                candidate = re.sub(r[0],r[1],candidate)
            candidate = candidate.strip()
            if candidate != term and candidate != "":
                alts.append(candidate)
        return alts

    def do_pre_html(self, encoded_str):
        data = encoded_str.decode("windows-1252")
        regex = [
            #[r"\x92", r"'"], # cp1252
            [r"<!",r"<!--"],
            [r"!>",r"-->"],
            [r"<--",r"<!--"],
            [r"(?i)<([a-z?][a-z0-9]*)/", r"<entity>\1</entity>"],
            [r"(?i)\\'([0-9a-f]{2})", r"<unicode>\1</unicode>"],
            [r"(?i)(\[?)<(/?)source>(\]?)", r"\3<\2source>\1"],
            [r"(?i)( \})?<(/?)mhw>(\{ )?", r""],
            [r"(?i)<(/?)(def|rj|note|cs|mcol|col|syn|ety|cref|cd|vmorph|amorph|plu|ecol|specif|wordforms|usage)>", r""],
            [r"(?i)<(/?)(qex|sn|sd)>", r"<\1b>"],
            [r"(?i)<(/?)(qau|au)>", r"<\1small>"],
            [r"(?i)<(/?)(ex|xex|it|ptcl|contr|ant)>", r"<\1i>"],
            # Sorting out yet unknown tags
            #    [r"(?i)<(/?)()>", r"[\1\2]"],
            [r"(?i)<as>(as( in the phrases)?,? ?)", r"\1<as>"],
            [r"(?i)<ent>[^<]*</ent>", r""]
        ]
        for r in regex:
            data = re.sub(r[0], r[1], data)
        return data.encode("windows-1252")

    def do_html_term(self, doc):
        term = doc("hw").eq(0).text().strip()
        regex = [
            [r"[\"`\*']",""]
        ]
        for r in regex:
            term = re.sub(r[0], r[1], term)
        return term.lower()

    def do_html_definition(self, dt_html, html, term):
        try:
            if not html.html():
                return ""
        except:
            print(html)
            sys.exit()

        d = pq(html)
        for e in html.find("entity"):
            val = d(e).text()
            replace = ""
            if val in entities:
                replace = entities[val]
            d(e).replaceWith(replace)

        for u in html.find("unicode"):
            val = int(d(u).text(),16)
            replace = chr(val)
            d(u).replaceWith(replace)

        for g in html.find("grk"):
            val = greek_translit(d(g).text())
            d(g).replaceWith(val)

        for hw in html.find("hw"):
            hw_html = re.sub(r"[\"`\*']","",d(hw).html())
            d(hw).replaceWith(
                d("<b/>").css("color", "#00b")
                    .html(hw_html).outerHtml()
            )

        for wf in html.find("wf"):
            wf_html = re.sub(r"[\"`\*']","",d(wf).html())
            d(wf).replaceWith(
                d("<span/>").css("color", "#00b")
                    .html(wf_html).outerHtml()
            )

        for pr in html.find("pr"):
            pr_html = re.sub(r"[\"`\*']","",d(pr).html())
            d(pr).replaceWith(
                d("<i/>").html(pr_html).outerHtml()
            )

        for q in html.find("q"):
            d(q).replaceWith(
                d("<i/>").css("color", "#33f")
                    .html(d(q).html()).outerHtml()
            )

        for pos in html.find("pos,pluf"):
            d(pos).replaceWith(
                d("<i/>").css("color", "#a00")
                    .html(d(pos).html()).outerHtml()
            )

        for m in html.find("mark,fld,conjf,plw,adjf,altname,sig,usedfor"):
            d(m).replaceWith(
                d("<span/>").css("color", "#00b")
                    .html(d(m).html()).outerHtml()
            )

        for a in html.find("as"):
            d(a).replaceWith(
                d("<span/>").css("color", "33a")
                    .html(d(a).html()).outerHtml()
            )

        for ets in html.find("ets,spn,gen,stype"):
            d(ets).replaceWith(
                d("<span/>").css("color", "#8B4513")
                    .html(d(ets).html()).outerHtml()
            )

        for er in html.find("er"):
            href = d(er).text().strip()
            if href == "":
                d(er).replaceWith("")
            else:
                """
                Word groups are not indexed, hence it makes sense to link to the
                first part of a compound only.
                """
                href = href.split(" ")[0]
                d(er).replaceWith(
                    d("<a/>").attr("href", "bword://%s" % href)
                        .html(d(er).html()).outerHtml()
                )

        for src in html.find("source"):
            """
            replacement = d("<p/>").css("text-align","right")
                .css("font-size","x-small")
                .html(d(src).html()).outerHtml()
            """
            "Including the sources unnecessarily blows up everything."
            replacement = ""
            d(src).replaceWith(replacement)

        output = "<p>%s</p>" % html.html().strip()
        return output

def gcide_grk_to_utf8(grk_str):
    found_len = 0
    found_xlit = None

    if grk_str == "s":
        return (1, "ς")

    for p in xlit:
        i = 0
        while i < min(len(grk_str),len(p[0])) and p[0][i] == grk_str[i]:
            i += 1

        if i < len(p[0]):
            if found_len > 0 and i == 0:
                break
            continue

        if i > found_len:
            found_len = i
            found_xlit = p

    if found_len:
        return (found_len, found_xlit[1])
    return (None, None)


def greek_translit(grk_str):
    result = ""
    n = 0
    while len(grk_str) > n:
        gr_len, greek = gcide_grk_to_utf8(grk_str[n:])

        if greek:
            result += greek
            n += gr_len
        else:
            result += grk_str[n]
            n += 1
    return result

