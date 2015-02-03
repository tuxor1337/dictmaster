# -*- coding: utf-8 -*-

import urllib2, urllib, httplib, copy, re
from cookielib import CookieJar
from pyquery import PyQuery as pq

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; de; rv:1.9.2.24) Gecko/20111103 Firefox/3.6.24'
BASE_URL = "http://atilf.atilf.fr/dendien/scripts/generic"
STEP_SIZE = 100

def get_url():
    cj = CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

    url = "%s/showps.exe?p=main.txt;host=interface_academie8.txt;java=no;" % BASE_URL
    req = urllib2.Request(url, None, { 'User-Agent' : USER_AGENT })
    response = opener.open(req)
    html = response.read()
    d = pq(html)
    session_id = re.sub(r"^[^;]+;s=([0-9]+);.*$", r"\1", d("body > form").attr("action"))

    url = "%s/cherche.exe?680;s=%s;;" % (BASE_URL, session_id)
    params = { "var0" : "", "var2" : "*", "var3" : "*!!*", "var5" : "*!!*" }
    req = urllib2.Request(url, urllib.urlencode(params), { 'User-Agent' : USER_AGENT })
    response = opener.open(req)
    html = response.read()
    d = pq(html)

    url = d("frame[name=fen2]").attr("src")
    wordcount = int(re.sub(r"^.+t=([0-9]+);.*$", r"\1", url))
    r_var = int(re.sub(r"^.+r=([0-9]+);.*$", r"\1", url))

    url_list = []
    for i, j in enumerate(range(0,wordcount,STEP_SIZE)):
        url = "%s/affiche.exe?%d;s=%s;d=%d;f=%d,t=%d,r=%d;" \
            % (BASE_URL, 120+i, session_id, j+1, j+STEP_SIZE, wordcount, r_var)
        url_list.append(url)
    return url_list

def process_html_element(html, term):
    html.html(
        re.sub(r"^ *\([0-9]+\) *", "", html.html())
    )
    doc = pq(html)
    heading = html.find("B b font[color=blue]").parents("b").parents("b")
    doc(heading).replaceWith(
        doc("<p/>").html(doc(heading).html()).outerHtml()
    )
    html.find("i").attr("style", "color:#3A4")
    for b in html.find("b b"):
        doc(b).replaceWith(
            doc("<span/>").html(doc(b).html()).outerHtml()
        )
    return re.sub(r" *<br?/?> *$", "", html.html().strip())


