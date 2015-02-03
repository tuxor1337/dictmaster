# -*- coding: utf-8 -*-

import sys
import os
import shutil
import importlib
import zipfile

import re
import codecs

import threading
import time

from pyquery import PyQuery as pq
from lxml import etree

from pyglossary.glossary import Glossary
from editor import glossEditor
from util import mkdir_p

THREAD_CNT = 3

class ppThread(object):
    def __init__(self, threadno, plugin, file_list, dirname):
        self.threadno = threadno
        self.output = []
        self.dirname = dirname
        self.plugin = plugin
        self.userscript = importlib.import_module("plugins.%s.custom" % self.plugin["name"])
        self.files = file_list

    def run(self):
        for i in range(self.threadno, len(self.files), THREAD_CNT):
            f = self.files[i]
            sys.stdout.write("\r\033[%dC%s %06d:" \
                % (self.threadno*23 + 1, u"{:<7}".format(f[0:7]), len(self.output)))
            sys.stdout.flush()
            if "html" in self.plugin["format"]:
                self.output.extend(self._do_html(
                    "%s/%s" % (self.dirname, f)
                ))
            elif "bgl" in self.plugin["format"]:
                self.output.extend(self._do_bgl(
                    "%s/%s" % (self.dirname, f)
                ))

    def _do_print_progress_term(self, datalen, term):
        if datalen % 25 == 0:
            sys.stdout.write("\r\033[%dC%s" \
                % (self.threadno*23 + 16, u"{:<6}".format(term[0:6])))
            sys.stdout.flush()

    def _do_data_append(self, term, definition, data, alts=None):
        if alts == None:
            m = re.search(r"^(.*)\([0-9]+\)$", term)
            if m != None:
                alts = {'alts': [m.group(1),m.group(1).lower()]}
        data.append((term, definition, alts))
        self._do_print_progress_term(len(data)-1, term)

    def _do_bgl(self, filename):
        data = []
        g = Glossary()
        g.read(filename)
        if "dictname" not in self.plugin:
            self.plugin["dictname"] = g.getInfo("bookname")
        shutil.move("%s_files" % filename, "data/%s/res" % self.plugin["name"])
        for d in g.data:
            term, definition, alts = d
            definition = definition.decode("utf-8")
            term = term.decode("utf-8")
            if "alts" in alts:
                for i in range(len(alts["alts"])):
                    alts["alts"][i] = alts["alts"][i].decode("utf-8")
            definition = re.sub(r"(?i)^[^<]+<br>\n<div[^>]+></div>", "", definition)

            encoded_str = definition.encode("utf-8")
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(encoded_str, parser=parser))
            for font_el in doc("font"):
                replacement = doc("<span/>").html(doc(font_el).html())
                if doc(font_el).attr("color"):
                    replacement.css("color", doc(font_el).attr("color"))
                if doc(font_el).attr("face"):
                    replacement.css("font-family", doc(font_el).attr("face"))
                if doc(font_el).attr("size"):
                    fontsize = doc(font_el).attr("size")
                    if fontsize[0] in "+-":
                        fontsize = float(fontsize.strip("+")) + 2
                    else:
                        fontsize = float(fontsize)
                    fontsize = int(min(7, max(fontsize,1))-1)
                    replacement.css("font-size",
                        ["0.8","1","1.3","1.5","2","2.7","4"][fontsize]+"em")
                doc(font_el).replaceWith(replacement.outerHtml())
            definition = doc.outerHtml()
            self._do_data_append(
                term, definition, data, alts
            )
        return data

    def _do_html(self,filename):
        html_structure = self.plugin["format"]["html"]
        data = []
        with codecs.open(filename, "r", "utf-8") as html_file:
            encoded_str = html_file.read().encode("utf-8")
            parser = etree.HTMLParser(encoding="utf-8")
            doc = pq(etree.fromstring(encoded_str, parser=parser))
            if "alternating" in html_structure:
                a = html_structure["alternating"]["a"]
                b = html_structure["alternating"]["b"]
                dt = doc(a)
                while len(dt) > 0:
                    dt, dd = dt.eq(0), dt.nextAll(b).eq(0)
                    self._do_html_data_append(dt, dd, data)
                    dt = dt.nextAll(a)
            elif "container_iter" in html_structure:
                for container in doc(html_structure["container_iter"]):
                    self._do_html_data_append(
                        doc(container), doc(container), data
                    )
            elif "singleton" in html_structure:
                if html_structure["singleton"] != "":
                    container = doc(html_structure["singleton"])
                else:
                    container = doc
                self._do_html_data_append(
                    doc(container), doc(container), data
                )
        return data

    def _do_html_data_append(self, dt, dd, data):
        html_structure = self.plugin["format"]["html"]
        term = self._do_html_element(dt, html_structure["term"])
        definition = self._do_html_element(dd, html_structure["definition"], term)
        self._do_data_append(term, definition, data)

    def _do_html_element(self, html, rule, term=""):
        result = ""

        if "attr" in rule:
            if "target" not in rule["attr"]:
                target = html
            else:
                try:
                    target = html.find(rule["attr"]["target"])
                except:
                    print html.html()
                    sys.exit()
            result = target.attr(rule["attr"]["key"]).strip()

        if "text_content" in rule:
            if rule["text_content"] == "":
                target = html
            else:
                try:
                    target = html.find(rule["text_content"])
                except:
                    print html.html()
                    sys.exit()
            result = target.text().strip()
            html = result

        if "userscript" in rule:
            result = self.userscript.process_html_element(html, term)

        if "regex" in rule:
            for regex in rule["regex"]:
                result = re.sub(regex[0], regex[1], result)

        if "lower" in rule:
            result = result.lower()

        return result

class Postprocessor(object):
    def __init__(self, plugin):
        self.plugin = plugin
        self.userscript = importlib.import_module("plugins.%s.custom" % self.plugin["name"])
        self.data = []

    def run(self):
        dirname = "data/%s/raw" % self.plugin["name"]
        if "zip" in self.plugin["format"]:
            if os.path.exists(dirname):
                shutil.rmtree(dirname)
            zdirname = "data/%s/zip" % self.plugin["name"]
            for zfile in os.listdir(zdirname):
                z = zipfile.ZipFile("%s/%s" % (zdirname, zfile))
                for n in z.namelist():
                    dest = os.path.join(dirname, n)
                    destdir = os.path.dirname(dest)
                    mkdir_p(destdir)
                    if not os.path.isdir(dest):
                        zdata = z.read(n)
                        f = open(dest, 'w')
                        f.write(zdata)
                        f.close()
                z.close()
            if "userscript" in self.plugin["format"]["zip"]:
                self.userscript.post_unzip(dirname)

        file_list = sorted(os.listdir(dirname))
        pptList = []
        for j in range(THREAD_CNT):
            ppt = ppThread(j, self.plugin, file_list, dirname)
            pptList.append(ppt)
            t = threading.Thread(target=ppt.run)
            t.daemon = True
            t.start()

        while threading.active_count() > 1:
            time.sleep(0.2)

        for ppt in pptList:
            self.data.extend(ppt.output)

        sys.stdout.write("\r\n")

    def editor(self):
        g = Glossary()
        g.data = self.data
        if "dictname" in self.plugin:
            g.setInfo("bookname", self.plugin["dictname"])
        ed = glossEditor(g)
        ed.write("data/%s/db.sqlite" % self.plugin["name"])
        return ed

