
from pyquery import PyQuery as pq
from lxml import etree

from pyglossary.glossary import Glossary

from dictmaster.replacer import *
from dictmaster.plugins.bgl import BglProcessor, Plugin as BglPlugin

class Plugin(BglPlugin):
    def post_setup(self, cursor):
        BglPlugin.post_setup(self, cursor)
        self.stages['Processor'] = LarousseProcessor(self)

class LarousseProcessor(BglProcessor):
    def do_bgl_definition(self, definition, term):
        definition = BglProcessor.do_bgl_definition(self, definition, term)

        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(definition, parser=parser))

        doc_rewrap_els(doc, "liaison", "<span/>")

        return doc.html()
