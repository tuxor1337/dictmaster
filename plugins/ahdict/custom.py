# -*- coding: utf-8 -*-

import re
from pyquery import PyQuery as pq

def process_html_element(html, term):
    doc = pq(html)
    doc("img").remove()
    doc("div[align=right]").remove()
    doc("a").removeAttr("name")
    doc("a").removeAttr("target")
    for a in html.find("a:not([href])"):
        if doc(a).text().strip() == "":
            doc(a).remove()
        else:
            doc(a).replaceWith(doc(a).html())
    for a in html.find("a"):
        if doc(a).text().strip() == "":
            doc(a).remove()
        elif "search.html" not in doc(a).attr("href"):
            doc(a).replaceWith(doc(a).html())
        else:
            href = "bword://%s" % doc(a).text().strip(". ").lower()
            doc(a).attr("href", href)
    doc("div.rtseg b").css("color","#069")
    doc("i").css("color","#940")
    doc("div.pseg > i").css("color","#900")
    doc("div.runseg > i").css("color","#900")
    for div in html.find("div.ds-list"):
        doc(div).replaceWith(
            doc("<p/>").html(doc(div).html()).outerHtml()
        )
    for div in html.find("div.sds-list"):
        doc(div).replaceWith(
            doc("<p/>").css("margin-left","1ex")
                .html(doc(div).html()).outerHtml()
        )
    html.find("*").removeAttr("class").removeAttr("title")
    for span in html.find("span"):
        doc(span).replaceWith(doc(span).html())

    return html.html().strip()
