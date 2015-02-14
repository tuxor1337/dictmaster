# -*- coding: utf-8 -*-

import os
import re
import glob
import shutil

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import html_container_filter, mkdir_p
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import ZipFetcher, Unzipper
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

wfb_categories = [
    "Introduction",
    "Geography",
    "People and Society",
    "Government",
    "Economy",
    "Energy",
    "Communications",
    "Transportation",
    "Military",
    "Transnational Issues"
]

excluded_subcats = [
    "Map references",
    "Area - comparative"
]

ctry_shorts = {
    "Aruba": "aa",
    "Antigua and Barbuda": "ac",
    "United Arab Emirates": "ae",
    "Afghanistan": "af",
    "Algeria": "ag",
    "Azerbaijan": "aj",
    "Albania": "al",
    "Armenia": "am",
    "Andorra": "an",
    "Angola": "ao",
    "American Samoa": "aq",
    "Argentina": "ar",
    "Australia": "as",
    "Ashmore and Cartier Islands": "at",
    "Austria": "au",
    "Anguilla": "av",
    "Akrotiri": "ax",
    "Antarctica": "ay",
    "Bahrain": "ba",
    "Barbados": "bb",
    "Botswana": "bc",
    "Bermuda": "bd",
    "Belgium": "be",
    "Bahamas, The": "bf",
    "Bangladesh": "bg",
    "Belize": "bh",
    "Bosnia and Herzegovina": "bk",
    "Bolivia": "bl",
    "Burma": "bm",
    "Benin": "bn",
    "Belarus": "bo",
    "Solomon Islands": "bp",
    "Navassa Island": "bq",
    "Brazil": "br",
    "Bhutan": "bt",
    "Bulgaria": "bu",
    "Bouvet Island": "bv",
    "Brunei": "bx",
    "Burundi": "by",
    "Canada": "ca",
    "Cambodia": "cb",
    "Curacao": "cc",
    "Chad": "cd",
    "Sri Lanka": "ce",
    "Congo, Republic of the": "cf",
    "Congo, Democratic Republic of the": "cg",
    "China": "ch",
    "Chile": "ci",
    "Cayman Islands": "cj",
    "Cocos (Keeling) Islands": "ck",
    "Cameroon": "cm",
    "Comoros": "cn",
    "Colombia": "co",
    "Northern Mariana Islands": "cq",
    "Coral Sea Islands": "cr",
    "Costa Rica": "cs",
    "Central African Republic": "ct",
    "Cuba": "cu",
    "Cabo Verde": "cv",
    "Cook Islands": "cw",
    "Cyprus": "cy",
    "Denmark": "da",
    "Djibouti": "dj",
    "Dominica": "do",
    "Jarvis Island": "dq",
    "Dominican Republic": "dr",
    "Dhekelia": "dx",
    "Ecuador": "ec",
    "European Union": "ee",
    "Egypt": "eg",
    "Ireland": "ei",
    "Equatorial Guinea": "ek",
    "Estonia": "en",
    "Eritrea": "er",
    "El Salvador": "es",
    "Ethiopia": "et",
    "Czech Republic": "ez",
    "Finland": "fi",
    "Fiji": "fj",
    "Falkland Islands (Islas Malvinas)": "fk",
    "Micronesia, Federated States of": "fm",
    "Faroe Islands": "fo",
    "French Polynesia": "fp",
    "Baker Island": "fq",
    "France": "fr",
    "French Southern and Antarctic Lands": "fs",
    "Gambia, The": "ga",
    "Gabon": "gb",
    "Georgia": "gg",
    "Ghana": "gh",
    "Gibraltar": "gi",
    "Grenada": "gj",
    "Guernsey": "gk",
    "Greenland": "gl",
    "Germany": "gm",
    "Guam": "gq",
    "Greece": "gr",
    "Guatemala": "gt",
    "Guinea": "gv",
    "Guyana": "gy",
    "Gaza Strip": "gz",
    "Haiti": "ha",
    "Hong Kong": "hk",
    "Heard Island and McDonald Islands": "hm",
    "Honduras": "ho",
    "Howland Island": "hq",
    "Croatia": "hr",
    "Hungary": "hu",
    "Iceland": "ic",
    "Indonesia": "id",
    "Isle of Man": "im",
    "India": "in",
    "British Indian Ocean Territory": "io",
    "Clipperton Island": "ip",
    "Iran": "ir",
    "Israel": "is",
    "Italy": "it",
    "Cote d'Ivoire": "iv",
    "Iraq": "iz",
    "Japan": "ja",
    "Jersey": "je",
    "Jamaica": "jm",
    "Jan Mayen": "jn",
    "Jordan": "jo",
    "Johnston Atoll": "jq",
    "Kenya": "ke",
    "Kyrgyzstan": "kg",
    "Korea, North": "kn",
    "Kingman Reef": "kq",
    "Kiribati": "kr",
    "Korea, South": "ks",
    "Christmas Island": "kt",
    "Kuwait": "ku",
    "Kosovo": "kv",
    "Kazakhstan": "kz",
    "Laos": "la",
    "Lebanon": "le",
    "Latvia": "lg",
    "Lithuania": "lh",
    "Liberia": "li",
    "Slovakia": "lo",
    "Palmyra Atoll": "lq",
    "Liechtenstein": "ls",
    "Lesotho": "lt",
    "Luxembourg": "lu",
    "Libya": "ly",
    "Madagascar": "ma",
    "Macau": "mc",
    "Moldova": "md",
    "Mongolia": "mg",
    "Montserrat": "mh",
    "Malawi": "mi",
    "Montenegro": "mj",
    "Macedonia": "mk",
    "Mali": "ml",
    "Monaco": "mn",
    "Morocco": "mo",
    "Mauritius": "mp",
    "Midway Islands": "mq",
    "Mauritania": "mr",
    "Malta": "mt",
    "Oman": "mu",
    "Maldives": "mv",
    "Mexico": "mx",
    "Malaysia": "my",
    "Mozambique": "mz",
    "New Caledonia": "nc",
    "Niue": "ne",
    "Norfolk Island": "nf",
    "Niger": "ng",
    "Vanuatu": "nh",
    "Nigeria": "ni",
    "Netherlands": "nl",
    "Norway": "no",
    "Nepal": "np",
    "Nauru": "nr",
    "Suriname": "ns",
    "Nicaragua": "nu",
    "New Zealand": "nz",
    "South Sudan": "od",
    "Southern Ocean": "oo",
    "Paraguay": "pa",
    "Pitcairn Islands": "pc",
    "Peru": "pe",
    "Paracel Islands": "pf",
    "Spratly Islands": "pg",
    "Pakistan": "pk",
    "Poland": "pl",
    "Panama": "pm",
    "Portugal": "po",
    "Papua New Guinea": "pp",
    "Palau": "ps",
    "Guinea-Bissau": "pu",
    "Qatar": "qa",
    "Serbia": "ri",
    "Marshall Islands": "rm",
    "Saint Martin": "rn",
    "Romania": "ro",
    "Philippines": "rp",
    "Puerto Rico": "rq",
    "Russia": "rs",
    "Rwanda": "rw",
    "Saudi Arabia": "sa",
    "Saint Pierre and Miquelon": "sb",
    "Saint Kitts and Nevis": "sc",
    "Seychelles": "se",
    "South Africa": "sf",
    "Senegal": "sg",
    "Saint Helena, Ascension, and Tristan da Cunha": "sh",
    "Slovenia": "si",
    "Sint Maarten": "sk",
    "Sierra Leone": "sl",
    "San Marino": "sm",
    "Singapore": "sn",
    "Somalia": "so",
    "Spain": "sp",
    "Saint Lucia": "st",
    "Sudan": "su",
    "Svalbard": "sv",
    "Sweden": "sw",
    "South Georgia and South Sandwich Islands": "sx",
    "Syria": "sy",
    "Switzerland": "sz",
    "Saint Barthelemy": "tb",
    "Trinidad and Tobago": "td",
    "Thailand": "th",
    "Tajikistan": "ti",
    "Turks and Caicos Islands": "tk",
    "Tokelau": "tl",
    "Tonga": "tn",
    "Togo": "to",
    "Sao Tome and Principe": "tp",
    "Tunisia": "ts",
    "Timor-Leste": "tt",
    "Turkey": "tu",
    "Tuvalu": "tv",
    "Taiwan": "tw",
    "Turkmenistan": "tx",
    "Tanzania": "tz",
    "Uganda": "ug",
    "United Kingdom": "uk",
    "United States Pacific Island Wildlife Refuges": "um",
    "Ukraine": "up",
    "United States": "us",
    "Burkina Faso": "uv",
    "Uruguay": "uy",
    "Uzbekistan": "uz",
    "Saint Vincent and the Grenadines": "vc",
    "Venezuela": "ve",
    "British Virgin Islands": "vi",
    "Vietnam": "vm",
    "Virgin Islands": "vq",
    "Holy See (Vatican City)": "vt",
    "Namibia": "wa",
    "West Bank": "we",
    "Wallis and Futuna": "wf",
    "Western Sahara": "wi",
    "Wake Island": "wq",
    "Samoa": "ws",
    "Swaziland": "wz",
    "Indian Ocean": "xo",
    "Arctic Ocean": "xq",
    "World": "xx",
    "Yemen": "ym",
    "Zambia": "za",
    "Atlantic Ocean": "zh",
    "Zimbabwe": "zi",
    "Pacific Ocean": "zn"
}

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = "The World Factbook 2014"
        fetcher = ZipFetcher(
            self.output_directory,
            urls=[
                "https://www.cia.gov/library/publications/download/download-2014/geos.zip",
                "https://www.cia.gov/library/publications/download/download-2014/graphics.zip"
            ]
        )
        postprocessor = FactbookProcessor(self)
        editor = Editor(
            output_directory=self.output_directory,
            plugin=self,
            auto_synonyms=False
        )
        self._stages = [
            fetcher,
            FactbookUnzipper(self.output_directory),
            postprocessor,
            editor
        ]

    def setup_dirs(self):
        PluginThread.setup_dirs(self)
        mkdir_p(os.path.join(self.output_directory, "zip"))

class FactbookUnzipper(Unzipper):
    def run(self):
        Unzipper.run(self)
        dirname = self.unzip_directory
        for repodir in os.listdir(dirname):
            path = os.path.join(dirname, repodir)
            if repodir == "geos":
                for filename in glob.glob("%s/*.html" % path):
                    filename = os.path.basename(filename)
                    src = os.path.join(path, filename)
                    dest = os.path.join(dirname, filename)
                    out_html = ""
                    with open(src, "r") as f:
                        encoded_str = f.read()
                        parser = etree.HTMLParser(encoding="utf-8")
                        doc = pq(etree.fromstring(encoded_str, parser=parser))
                        out_html = doc("div#wfb_data > table > tr").eq(3).html()
                    with open(dest, "w") as f:
                        f.write(out_html.encode("utf-8"))
            elif repodir == "graphics":
                res_dirname = os.path.join(dirname, "../res/")
                mkdir_p(res_dirname)
                file_list = glob.glob("%s/maps/*-map.gif" % path)
                file_list += glob.glob("%s/locator/*/*_large_locator.gif" % path)
                file_list += glob.glob("%s/flags/large/*-lgflag.gif" % path)
                for filename in file_list:
                    basename = os.path.basename(filename)
                    src = filename
                    dest = os.path.join(res_dirname, basename)
                    os.rename(src, dest)
            shutil.rmtree(path)

class FactbookProcessor(HtmlContainerProcessor):
    def __init__(self, plugin):
        super(FactbookProcessor, self).__init__("div.CollapsiblePanel", plugin)

    def do_html_alts(self, dd, term):
        d = pq(dd)
        alts = []
        regex = [
            [r"^Introduction :: (.*)$",r"\1"],
            [r"^(.*) :: (.*)$", r""]
        ]
        for hw in d.find("h2"):
            candidate = d(hw).text().strip()
            for r in regex:
                candidate = re.sub(r[0],r[1],candidate)
            candidate = candidate.strip()
            if candidate != term and candidate != "":
                alts.append(candidate)
        return alts

    def do_html_term(self, doc):
        term = doc("h2").eq(0).text().strip()
        regex = [
            [r"^(.*) :: (.*)$",r"\2 \1"]
        ]
        for r in regex:
            term = re.sub(r[0], r[1], term)
        return term

    def do_html_definition(self, html, term):
        d = pq(html)
        curr = d("div.box table > tr")[0]
        curr_cat = ""
        for cat in wfb_categories:
            if cat in term:
                curr_cat = cat
                curr_ctry = term[:-len(cat)-1]
        out = ""
        if curr_cat == "Government":
            out += '<p><img src="{0}-lgflag.gif" /></p>'.format(ctry_shorts[curr_ctry])
        if curr_cat == "Geography":
            out += '<p><img src="{0}_large_locator.gif" /></p>'.format(ctry_shorts[curr_ctry])
            out += '<p><img src="{0}-map.gif" /></p>'.format(ctry_shorts[curr_ctry])
        while True:
            curr_title = d(curr).find("div.category").text().strip(" :")
            curr = d(curr).nextAll("tr")[0]
            if curr_title not in excluded_subcats:
                out += "<p>"
                out += '<b style="color:#C49;">%s</b><br />' % curr_title
                for div in d(curr).find("div"):
                    if d(div).attr("class") == "category":
                        dat = d(div).find("span.category_data").text().strip()
                        d(div).find("span.category_data").remove()
                        subcat = d(div).text()
                        if "population pyramid" in subcat:
                            # TODO: include pyramid graphics
                            dat = "The pyramid graphics are not included in this"\
                                + " version of the dictionary."
                        out += "<b>%s</b> %s<br />" % (subcat, dat)
                    elif d(div).attr("class") == "category_data":
                        dat = "%s" % d(div).text()
                        out += "%s<br />" % dat
                    else:
                        continue
                out += "</p>"
            if len(d(curr).nextAll("tr")) < 2:
                break
            curr = d(curr).nextAll("tr")[1]
        if curr_cat == "Introduction":
            out += '<hr align="left" width="25%" />'
            for cat in wfb_categories[1:]:
                out += '<p><a href="bword://{0} {1}">{1}</a></p>'.format(curr_ctry, cat)
        return out

