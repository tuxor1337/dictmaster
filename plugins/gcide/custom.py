# -*- coding: utf-8 -*-

import os, glob, shutil, re, sys
from pyquery import PyQuery as pq

def post_unzip(dirname):
    repodir = os.listdir(dirname)[0]
    path = os.path.join(dirname, repodir)
    for filename in glob.glob("%s/CIDE.*" % path):
        filename = os.path.basename(filename)
        src = os.path.join(path, filename)
        dest = os.path.join(dirname, filename)
        os.rename(src, dest)
    shutil.rmtree(path)

"""
Format information from dico source code (c and lex files)
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/ent.c
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/grk.c
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/idxgcide.l
http://git.gnu.org.ua/cgit/dico.git/tree/modules/gcide/markup.l
"""

entities = {
    "br": ""
}

grk_chars = {
    "a": "α"
}

def process_html_element(html, term):
    if not html.html():
        return ""

    d = pq(html)
    for e in html.find("entity"):
        val = d(e).text()
        replace = ""
        if val in entities:
            replace = entities[val]
        d(e).replaceWith(replace)

    for u in html.find("unicode"):
        val = int(d(u).text(),16)
        replace = ""
        # get matching unicode point in utf-8
        d(u).replaceWith(replace)

    for g in html.find("grk"):
        val = d(g).text()
        replace = ""
        # parse to greek letters in utf-8
        d(g).replaceWith(replace)

    for hw in html.find("hw"):
        d(hw).replaceWith(
            d("<b/>").html(d(hw).html()).outerHtml()
        )

    return html.html().strip()

