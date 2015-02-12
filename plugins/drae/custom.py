# -*- coding: utf-8 -*-

import re
from pyquery import PyQuery as pq

def process_html_element(html, term):
    doc = pq(html)
    html.find("a").removeAttr("name")
    html.find("a").removeAttr("target")
    for a in html.find("a:not([href])"):
        doc(a).replaceWith(doc(a).html())
    for a in html.find("a"):
        if doc(a).text().strip() == "":
            doc(a).replaceWith("")
        else:
            doc(a).replaceWith(
                doc("<a/>").attr("href", "bword://%s" % doc(a).text())
                    .html(doc(a).html()).outerHtml()
            )
    html.find("span.d,span.f").css("color", "#00f")
    html.find("span.a").css("color", "#080")
    html.find("span.g").css("color", "#AAA")
    html.find("span.j").css("color", "#F00")
    html.find("span.k").css("color", "#800")
    html.find("span.h").css("color", "#808")
    for span in html.find("span.b,span.n"):
        doc(span).replaceWith(doc(span).html())

    for span in html.find("span:not([style])"):
        doc(span).replaceWith(doc(span).html())
    html.find("*").removeAttr("class").removeAttr("title")
    return html.html().strip()
