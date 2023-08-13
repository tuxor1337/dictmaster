
import re
import os
import sys

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.replacer import *
from dictmaster.plugins.bgl import BglProcessor, Plugin as BglPlugin

symbol_img = {
    "8EAF66FD.bmp": "", # image not found (red x in white square)
}

image_to_html = {
    "00CE26A7.bmp": "🟫",
    "019396D2.bmp": "<num>20</num>",
    "024813B0.bmp": "<num>12</num>",
    "06049169.bmp": "<u>ay</u>",
    "0C5A52AB.bmp": "<u>Au</u>",
    "1019D0D5.bmp": "<num>9</num>",
    "136E9342.bmp": "<u>ei</u>",
    "17F512D1.bmp": "<u>O</u>",
    "184D30BA.bmp": "<u>u</u>",
    "23926352.bmp": "═",
    "25D17148.bmp": "ɛ͂",
    "2688309E.bmp": "<u>ie</u>",
    "279793DC.bmp": "y̆",
    "28D7FBEF.bmp": "ɲ",
    "28E83D73.bmp": "<u>ee</u>",
    "2B2B54F2.bmp": "<u>aa</u>",
    "2EA1007D.bmp": "<num>10</num>",
    "2F89DD93.bmp": "dʒ",
    "30B718E5.bmp": "<u>Ei</u>",
    "30F5C97E.bmp": "<u>ee</u>",
    "337939BD.bmp": "<u>eu</u>",
    "34DA53B3.bmp": "<u>ä</u>",
    "3681A467.bmp": "<num>5</num>",
    "3E879C3B.jpg": "🇦🇹",
    "3F3A8CEE.bmp": "ɐ",
    "400D64F8.jpg": "🇦🇺",
    "403584BE.bmp": "u̯",
    "42E5DC52.bmp": "a͜u",
    "4474C8CF.bmp": "<num>23</num>",
    "45B14D38.bmp": "o̯",
    "4651E7C6.jpg": "🇬🇧",
    "470C36EF.jpg": "🇺🇸",
    "47474EEB.bmp": "<u>ä</u>",
    "481C117D.bmp": "<num>11</num>",
    "495BC838.bmp": "ɐ̯",
    "496F99FD.bmp": "<u>ü</u>",
    "4C2849FE.bmp": "<num>32</num>",
    "502F5DDA.bmp": "⟹",
    "525DEF9F.bmp": "<u>W</u>",
    "52F0BCB8.bmp": "<num>15</num>",
    "54EFB593.bmp": "<u>E</u>",
    "55C90477.bmp": "<u>ei</u>",
    "596FBECE.bmp": "<num>16</num>",
    "59738991.bmp": "⮀",
    "59FE3E77.bmp": "ɟ",
    "5D58A0A1.bmp": "<u>oo</u>",
    "617F985B.bmp": "<num>7</num>",
    "623DCC79.bmp": "<u>I</u>",
    "62C8D4F5.bmp": "ʊ",
    "66CF36F1.bmp": "<u>Au</u>",
    "68579D0A.bmp": "<u>ey</u>",
    "6B1898C1.bmp": "<num>26</num>",
    "6B36F75C.bmp": "t͜ʃ",
    "6B9D59EE.bmp": "ˊ",
    "6CBF8257.bmp": "i̯",
    "6FFE20B4.bmp": "<num>31</num>",
    "70D556FE.bmp": "ɔ͜y",
    "71E23CA0.bmp": "<u>e</u>",
    "731CF705.bmp": "<u>I</u>",
    "73948D23.jpg": "🇺🇸",
    "74B95B6D.bmp": "<u>ie</u>",
    "758EE5EC.bmp": "<u>Ei</u>",
    "75A4E003.bmp": "<u>ö</u>",
    "7698D7B8.bmp": "<u>U</u>",
    "76FA59A5.bmp": "<u>eu</u>",
    "7A05AE88.bmp": "t͜s",
    "7AF8D89C.bmp": "<sup>e</sup>",
    "7DAB38E4.bmp": "<num>13</num>",
    "7DE58D95.bmp": "<num>8</num>",
    "7E18EE64.bmp": "<u>Aa</u>",
    "83C18C85.bmp": "<u>oo</u>",
    "848D8F4A.bmp": "ʀ",
    "874087A9.bmp": "<num>33</num>",
    "8D7038CE.bmp": "l̩",
    "8F1C0698.bmp": "<num>22</num>",
    "8F72CEBD.bmp": "<u>ai</u>",
    "904D6470.bmp": "<num>4</num>",
    "90EF7C51.bmp": "œ͂",
    "985E0F06.bmp": "<u>ui</u>",
    "98780C67.bmp": "ɱ",
    "9AD0434C.bmp": "<num>3</num>",
    "9C152C3B.jpg": "🇨🇭",
    "9E4CA30E.bmp": "<num>19</num>",
    "A1EFA0B4.jpg": "🇦🇺",
    "A4F2AA15.bmp": "<num>1</num>",
    "A53B4C25.bmp": "<u>E</u>",
    "A7915FE9.jpg": "🇨🇦",
    "A9758328.bmp": "<u>Eu</u>",
    "AC3B8501.bmp": "<num>29</num>",
    "ACCA6FD2.bmp": "<num>21</num>",
    "AE9AEC46.bmp": "<u>äu</u>",
    "B14680A1.bmp": "<u>c</u>",
    "B1FE619F.bmp": "ˌ",
    "B8B49FD9.bmp": "<u>o</u>",
    "BBEF32C0.bmp": "<num>34</num>",
    "BDD8FA6A.bmp": "<num>6</num>",
    "BFC21C72.bmp": "p͜f",
    "C0FBA02E.bmp": "<u>ö</u>",
    "C1BB8184.bmp": "<u>a</u>",
    "C47A4277.jpg": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "C5895FB4.bmp": "<num>17</num>",
    "C5DC2550.bmp": "<num>25</num>",
    "C60E9312.bmp": "<u>A</u>",
    "C6B8E368.bmp": "<num>28</num>",
    "C6E631D8.bmp": "ʏ",
    "CC74EB1C.bmp": "<u>Äu</u>",
    "CF7EB89A.bmp": "<u>ü</u>",
    "D300B1A0.bmp": "<u>i</u>",
    "D7010AFC.bmp": "<num>24</num>",
    "D73538F0.bmp": "<u>au</u>",
    "DA191EC9.bmp": "<u>au</u>",
    "DB565468.bmp": "<num>2</num>",
    "DC489F9D.bmp": "n̩",
    "DD47788A.bmp": "<u>äu</u>",
    "DDD40D3C.bmp": "<u>o</u>",
    "DFE26914.bmp": "<num>30</num>",
    "E22AF855.bmp": "ɥ",
    "E39291EF.bmp": "a͜i",
    "E5762CF3.bmp": "<num>14</num>",
    "E7297AF5.bmp": "<u>a</u>",
    "E74D01DC.bmp": "<b style=\"color:#b55\">►</b>",
    "E98A75C7.bmp": "<num>18</num>",
    "EA1F890F.bmp": "<u>U</u>",
    "F1D63B1D.bmp": "<u>y</u>",
    "F8783F40.bmp": "<num>27</num>",
    "FB666D6A.bmp": "<u>C</u>",
    "FF2CE5DB.bmp": "<u>A</u>",
    "flag-am-size2.jpg": "🇺🇸",
    "flag-aus-size2.jpg": "🇦🇺",
    "flag-aust-size2.jpg": "🇦🇹",
    "flag-brit-size2.jpg": "🇬🇧",
    "flag-sui-size2.jpg": "🇨🇭",
}

class Plugin(BglPlugin):
    pons_lang = ""

    def post_setup(self, cursor):
        BglPlugin.post_setup(self, cursor)

        self.pons_lang = {
            "PONS Universelles Wörterbuch Deutsch-Französisch": "de-fr",
            "PONS Universelles Wörterbuch Französisch-Deutsch": "fr-de",
            "PONS Universelles Wörterbuch Deutsch-Italienisch": "de-it",
            "PONS Universelles Wörterbuch Italienisch-Deutsch": "it-de",
            "PONS Universelles Wörterbuch Deutsch-Spanisch": "de-es",
            "PONS Universelles Wörterbuch Spanisch-Deutsch": "es-de",
            "PONS Universelles Wörterbuch Deutsch-Englisch": "de-en",
            "PONS Universelles Wörterbuch Englisch-Deutsch": "en-de",
        }[self.dictname]

        res_dirname = os.path.join(self.output_directory, "res")
        for f in os.listdir(res_dirname):
            if f not in symbol_img:
                os.remove(os.path.join(res_dirname, f))
        self.stages['Processor'] = PonsProcessor(self)

class PonsProcessor(BglProcessor):
    def do_bgl_definition(self, definition, term, alts):
        definition = (
            definition
            .encode("utf-8")
            .replace(b"\xc2\xa0", b" ")
            .decode("utf-8")
        )
        regex = [
            [r"(?i)^[^<]*(<sup>[^<]*</sup>)?[^<]*<br>\n<div[^>]*></div>", ""],
            [r"(?i)^[^<]+<p[^>]*>[^<]*[^<]*<br( /)?>[^<]*</p>", ""],
            [r"(?i)</b><b>", ""],
            [r"(?i)<strong[^>]*>(&nbsp;| )*(<img[^>]+?>)(&nbsp;| )*</strong>", r"\2"]
        ]
        for r in regex:
            definition = re.sub(r[0], r[1], definition)

        definition = BglProcessor.do_bgl_definition(self, definition, term, alts)

        definition = re.sub(r"&([^;]+);", r"##\1||", definition)
        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(definition, parser=parser))

        doc_strip_els(doc, "body", block="False")
        doc_rewrap_els(doc, "tr", "<p/>")
        doc_strip_els(doc, "table,td", block="False")

        def _replace_img_el(el, doc=doc):
            if doc(el).outerHtml() is None:
                return ""
            assert len(doc(el).parents("strong")) == 0

            img_src = doc(el).attr("src").strip()
            replacement = el
            if img_src in image_to_html:
                replacement = doc("<span/>").html(image_to_html[img_src])
            elif img_src in symbol_img:
                replacement.addClass("_dictmaster_touched")
            else:
                print(term)
                print(img_src)
                print(definition)
                sys.exit()
            return replacement
        doc_replace_els(doc, "img:not(._dictmaster_touched)", _replace_img_el)
        doc("img").removeAttr("class")

        new_el = doc("<b/>").css({
            "background-color": "#b55",
            "color": "#fff",
            "padding": "0.1ex 0.5ex 0",
            "margin-right": "0.5ex",
        })
        doc_rewrap_els(doc, "num", new_el.outerHtml(), textify=True)

        definition = doc.html()

        # remove empty strong/div tags
        regex = [
            [r"##([^\|]+)\|\|",r"&\1;"],
            [r"(?i)<(strong|div)[^>]*>\s*</(strong|div)>", ""],
        ]
        for r in regex:
            definition = re.sub(r[0], r[1], definition)

        return definition.strip()

    def do_bgl_alts(self, definition, term, alts):
        if self.plugin.pons_lang != "fr-de":
            return alts

        if "oe" not in term:
            return alts

        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(definition, parser=parser))

        ex_term = doc.children("span:first-child").eq(0).text()
        if ex_term == term:
            return alts

        u_term = term.replace("oe", "œ")
        if ex_term != u_term:
            print()
            print(f"oe→œ: {u_term}")

        return alts + [term, u_term]

    def do_bgl_term(self, definition, term, alts):
        if self.plugin.pons_lang != "fr-de":
            return term

        if "oe" not in term:
            return term

        u_term = term.replace("oe", "œ")

        return u_term if u_term in alts else term
