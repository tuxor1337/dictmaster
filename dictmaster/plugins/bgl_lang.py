
import re
import os
import sys

from pyquery import PyQuery as pq
from lxml import etree

from pyglossary.glossary import Glossary

from dictmaster.replacer import *
from dictmaster.plugins.bgl import BglProcessor, Plugin as BglPlugin

symbol_img = {}

image_to_html = {
    "223E9A06.bmp": ":",
    "3244C0D7.bmp": "æ̃",
    "44A97BB5.bmp": "o̯",
    "502F5DDA.bmp": "⟹",
    "795FA043.bmp": "l̩",
    "7A064BAA.bmp": "z,",
    "8DAD7054.bmp": "n̩",
    "BC107C97.bmp": "​ɔ̃​",
    "C95012A3.bmp": "á̯",
    "CF4DA527.bmp": "ɑ͂",
    "D5188025.bmp": "i̯",
}

class Plugin(BglPlugin):
    def post_setup(self, cursor):
        BglPlugin.post_setup(self, cursor)

        res_dirname = os.path.join(self.output_directory, "res")
        for f in os.listdir(res_dirname):
            if f not in symbol_img:
                os.remove(os.path.join(res_dirname, f))
        self.stages['Processor'] = LangProcessor(self)

class LangProcessor(BglProcessor):
    def do_bgl_definition(self, definition, term, alts):
        definition = BglProcessor.do_bgl_definition(self, definition, term, alts)

        definition = re.sub(r"&([^;]+);", r"##\1||", definition)
        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(definition, parser=parser))

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

        return doc.html()
