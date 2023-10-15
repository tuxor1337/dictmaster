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

import re

def doc_replace_els(doc, query, fun):
    old_html = ""
    new_html = doc.html()
    while old_html != new_html:
        old_html = new_html
        el = doc(query).eq(0)
        doc(el).replaceWith(fun(el))
        new_html = doc.html()

def doc_rewrap_els(doc, query, new_el, css=[], remove_empty=True,
                   textify=False, prefix="", suffix="", regex=[],
                   transfer_attr=[]):
    def fun(el):
        if textify:
            replacement = doc(el).text()
        else:
            replacement = doc(el).html()
        if replacement is None:
            replacement = ""
        if replacement != "" or not remove_empty:
            for r in regex:
                replacement = re.sub(r[0], r[1], replacement)
            replacement = doc(new_el).html(prefix + replacement + suffix)
            for s in css: replacement.css(*s)
            for a in transfer_attr:
                replacement.attr(a[1], doc(el).attr(a[0]))
        return replacement
    doc_replace_els(doc, query, fun)

def doc_retag_els(doc, query, tag, css=[]):
    for el in doc(query):
        el.tag = tag
        for s in css:
            doc(el).css(*s)

def doc_strip_els(doc, query, block=True, prefix=None, suffix=None):
    if prefix is None:
        prefix = " " if block else ""
    if suffix is None:
        suffix = " " if block else ""
    def fun(el):
        replacement = doc(el).html()
        if replacement is None:
            replacement = ""
        else:
            replacement = prefix + replacement + suffix
        return replacement
    doc_replace_els(doc, query, fun)

def doc_replace_attr(doc, query, attr, fun, new_attr=None, force=False):
    new_attr = attr if new_attr is None else new_attr
    for el in doc(query):
        val = doc(el).attr(attr)
        if val is not None or force:
            doc(el).attr(new_attr, fun(el, val))

def doc_replace_attr_re(doc, query, attr, regex, new_attr=None):
    def regex_fun(el, val):
        return re.sub(regex[0], regex[1], val)
    doc_replace_attr(doc, query, attr, regex_fun, new_attr=new_attr)
