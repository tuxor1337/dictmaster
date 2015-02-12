#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Deprecated drae-fetcher that always recalculates the challenge/response pair.
"""

import re, urllib2, requests, time, sys
from pyquery import PyQuery as pq
from ctypes import c_int32

def decode_string(in_str):
    return urllib2.unquote(in_str)

def decode_action(d):
    f = d("form").eq(0)
    action = d(f).attr('action')
    d(f).attr('action', decode_string(action))

def submit_form(d):
    e = d("input")
    for i in [1,2,5,7]:
        d(e[i]).attr("value", decode_string(d(e[i]).attr("value")))
    ">>>"
    form_data = ""
    for el in e:
        form_data += "%s=%s&" % (d(el).attr("name"), d(el).attr("value"))
    form_data = form_data.strip("&")
    return (d("form").attr("action"), form_data)
    "<<<"

def cookie_redirect(d):
    cookie = ''
    e = d("input")
    uri = d("form").attr("action")
    path = uri
    tchr = '&'
    token = path.index('?')
    if token > 0:
        path = path[0:token]
    elif token != 0:
        token = path.index('#')
        tchr = '#'
    for i in range(len(e)):
        cookie += d(e[i]).attr("name") + '=' + d(e[i]).attr("value")
        if i < (len(e) - 1):
                cookie += '&'
    js_d = time.time() + 5.0
    d_GMTString = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(js_d))
    doc_cookies = {
        d(e[0]).attr("name")[0:11] + '75=' : cookie,
        "expires": d_GMTString,
        "path": path
    }
    if token > 0:
        qs = tchr + uri[token + 1:]
    else:
        qs = ""
    uri = path + '?' + d(e[0]).attr("name") + '=' + d(e[0]).attr("value") + qs
    return ("http://lema.rae.es" + uri, doc_cookies)

def challenge(html):
    d = pq(html)
    table = re.search(r'var table = "([^"]+)"', html).groups()[0]
    c = int(re.search(r'var c = (.*)\n', html).groups()[0])
    slt = re.search(r'var slt = "([^"]+)"', html).groups()[0]
    s1 = re.search(r"var s1 = '([^']+)'", html).groups()[0]
    s2 = re.search(r"var s2 = '([^']+)'", html).groups()[0]
    n = int(re.search(r'var n = (.*)\n', html).groups()[0])
    something = re.search(r'.value="([^"]+):" \+ chlg', html).groups()[0]

    start = ord(s1[0])
    end = ord(s2[0])
    arr = [None]*n
    m = ((end - start) + 1)**n
    chlg = u""
    for i in range(n):
        arr[i] = s1
    for i in range(m - 1):
        j = n - 1
        while j >= 0:
            t = ord(arr[j][0])
            t += 1
            arr[j] = unichr(t)
            if ord(arr[j][0]) <= end:
                break
            else:
                arr[j] = s1
            j -= 1
        chlg = u"".join(arr)
        js_str = chlg + slt
        crc = 0
        crc = c_int32(crc).value ^ (-1)
        for k in js_str:
            table_offset = ((c_int32(crc).value ^ c_int32(ord(k)).value) & 0x000000FF) * 9
            table_data = int(table[table_offset:table_offset + 8],16)
            crc = (c_int32(crc).value >> 8) ^ c_int32(table_data).value
        crc = crc ^ (-1)
        crc = abs(crc)
        if crc == c:
            break
    d(d("input").eq(1)).attr("value", u"%s:%s:%s:%d" % (something, chlg, slt, crc))
    decode_action(d)
    _, formdata = submit_form(d)
    url, cookies = cookie_redirect(d)
    return (url, formdata, cookies)


if __name__ == "__main__" and len(sys.argv) > 1:
    url = "http://lema.rae.es/drae/srv/search?val=" + urllib2.quote(
        sys.argv[1].decode("utf-8").encode("iso-8859-1")
    )
    headers = {
        "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64; rv:35.0) Gecko/20100101 Firefox/35.0",
    }
    s = requests.Session()
    s.headers.update(headers)
    r1 = s.get(url=url)
    html = r1.content.decode("utf-8")
    url, formdata, cookies = challenge(html)
    req = requests.Request('POST',  url, data=formdata, headers={ "Referer": url })
    prepped = s.prepare_request(req)
    r2 = s.send(prepped)
    print pq(r2.content.decode("utf-8")).find("body").outerHtml().encode("utf-8")

