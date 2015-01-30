# -*- coding: utf-8 -*-

import urllib2, httplib, copy, re, time, sys, os, errno, threading
from pyquery import PyQuery as pq

from config import cfg

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; de; rv:1.9.2.24) Gecko/20111103 Firefox/3.6.24'
BASE_URL = "http://www.zeno.org"
STEP_SIZE = 20
ZENO_KEY = "Georges-1913"
        
def _download(url,params=None):
    try:
        html = urllib2.urlopen(url, params).read()
        return html
    except (urllib2.URLError,httplib.BadStatusLine):
        print "Connection to %s failed. Retrying..." % url
        time.sleep(0.2)
        return _download(url,params)

class downloadThread(object):
    def __init__(self, no, url_pattern):
        self.threadno = no
        self.url = url_pattern
        self.output = []
        
    def run(self):
        startnum = STEP_SIZE*self.threadno
        while True:
            if len(self.output) % 60 == 0:
                sys.stdout.write("\r\033[%dC%d:%04d" % (7*self.threadno+1, self.threadno, len(self.output)))
                sys.stdout.flush()
            html = _download(self.url % (BASE_URL, ZENO_KEY, startnum))
            d = pq(html)
            hitlist = d("span.zenoSRHitTitle")
            if len(hitlist) == 0:
                break
            for hit in hitlist:
                self.output.append("%s%s" % (BASE_URL, d(hit).find("a").attr("href")))
            startnum += cfg["threadcnt"]*STEP_SIZE

def get_url():
    url_list = []
    url = "%s/Kategorien/T/%s?s=%d"
    print("Collecting article urls...")
    
    dtList = []
    for j in range(cfg["threadcnt"]):
        dt = downloadThread(j, url)
        dtList.append(dt)
        t = threading.Thread(target=dt.run)
        t.daemon = True
        t.start()
        
    while threading.active_count() > 1:
        time.sleep(0.2)
        
    for dt in dtList:
        url_list.extend(dt.output)
        
    print("\r\n...collected %d article urls." % len(url_list))
    return url_list
    
def _download_res(doc):
    def _download(url,params=None):
        try:
            data = urllib2.urlopen(url, params).read()
            return data
        except (urllib2.URLError,httplib.BadStatusLine):
            print "Connection to %s failed. Retrying..." % url
            time.sleep(0.2)
            return _download(url,params)
    for img in doc.find("img"):
        url = "%s%s" % (BASE_URL,doc(img).attr("src"))
        basename = url.split('/')[-1]
        data = _download(url)
        mkdir_p("data/%s/res" % cfg["name"])
        with open("data/%s/res/%s" % (cfg["name"],basename), "w") as img_file:
            img_file.write(data)
        doc(img).attr("src", basename)
    definition = doc.html()

def process_html_element(html, term):
    doc = pq(html)
    doc.remove("a.zenoTXKonk[title='Faksimile']")
    for div in doc("div.zenoIMBreak"):
        doc(div).replaceWith(
            doc("<p/>").html(doc(div).find("div a").html()).outerHtml()
        )
    doc.remove("div")
    for a in doc("a"):
        doc(a).replaceWith(
            doc("<span/>").html(doc(a).html()).outerHtml()
        )
    _download_res(doc)
    result = ""
    for para in doc.find("p"):
        result += "%s<br />" % doc(para).html()
    return result
    
    
