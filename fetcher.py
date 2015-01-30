# -*- coding: utf-8 -*-

from pyquery import PyQuery as pq

from urllib2 import URLError
from httplib import BadStatusLine
import urllib2

import sys, threading, time, importlib
from string import lowercase as ALPHA

from util import mkdir_p

def fetch(plugin):
    print("Fetching for plugin %s..." % plugin["name"])
    
    ftList = []
    url = None
    
    if "from_script" in plugin["url"]:
        userscript = importlib.import_module(plugin["url"]["from_script"].replace("/",".").replace(".py",""))
        plugin["url"]["list"] = userscript.get_url()
        
    for j in range(plugin["threadcnt"]):
        ft = fetcherThread(j, plugin, url)
        ftList.append(ft)
        t = threading.Thread(target=ft.fetch)
        t.daemon = True
        t.start()
        
    while threading.active_count() > 1:
        time.sleep(0.2)
        
    print("...done fetching.")

def download(url, params=None):
    data = None
    try:
        data = urllib2.urlopen(url, params).read()
        return data
    except (URLError, BadStatusLine):
        sys.stdout.write("\rConnection to %s failed. Retrying...\n" % url)
        sys.stdout.flush()
        time.sleep(0.5)
        return download(url, params)

def html_exists(data, querystr):
    d = pq(data)
    return len(d(querystr)) > 0
    
def apply_filter(data, fltr):
    if "html_container" in fltr:
        d = pq(data)
        return unicode(d(fltr["html_container"]).html())
    else:
        return data

class fetcherThread(object):
    def __init__(self, no, plugin, url=None):
        self.threadno = no
        self.plugin = plugin
        self.url = url
        
    def fetch(self):
        if "singleton" in self.plugin["url"]:
            self.fetch_list([self.plugin["url"]["singleton"]])
        elif "list" in self.plugin["url"]:
            urlrange = [ self.plugin["url"]["list"][i] for i in
                range(
                    self.threadno,
                    len(self.plugin["url"]["list"]),
                    self.plugin["threadcnt"]
                )
            ]
            self.fetch_list(urlrange)
        elif "pattern" in self.plugin["url"]:
            if "alphanum" in self.plugin["url"]["itermode"]:
                letterrange = [ALPHA[i] for i in range(self.threadno, len(ALPHA), self.plugin["threadcnt"])]
                numberrange = range(self.plugin["url"]["itermode"]["alphanum"]["count_start"],1000)
                self.fetch_alphanum(letterrange, numberrange)
        
    def fetch_list(self, url_list):
        for i,url in enumerate(url_list):
            sys.stdout.write("\r\033[%dC%d:%04d" % (7*self.threadno+1, self.threadno, i))
            sys.stdout.flush()
            data = download(url)
            if "charset" in self.plugin["url"] and "zip" not in self.plugin["format"]:
                data = data.decode(self.plugin["url"]["charset"])
            if self.stop_count(data):
                break
            self.write_file("%06d" % (i*self.plugin["threadcnt"]+self.threadno), data)
        
    def fetch_alphanum(self, letterrange, numberrange):
        for letter in letterrange:
            for pagenumber in numberrange:
                sys.stdout.write("\r\033[%dC%s:%03d" % (6*self.threadno+1, letter, pagenumber))
                sys.stdout.flush()
                url = self.plugin["url"]["pattern"].replace("{a..z}", letter.lower()) \
                    .replace("{A..Z}", letter.upper()) \
                    .replace("{0..9}", "%d" % pagenumber)
                
                data = download(url)
                if "charset" in self.plugin["url"] and "zip" not in self.plugin["format"]:
                    data = data.decode(self.plugin["url"]["charset"])
                if self.stop_count(data):
                    break
                self.write_file("%s%04d" % (letter, pagenumber), data)
                    
    def stop_count(self, data):
        stop_count = True
        if "count_condition" in self.plugin["url"]:
            if "html_exists" in self.plugin["url"]["count_condition"]:
                stop_count = not html_exists(data, self.plugin["url"]["count_condition"]["html_exists"])
            if "always_continue" in self.plugin["url"]["count_condition"]:
                stop_count = False
        else:
            stop_count = False
        return stop_count
            
                
    def write_file(self, basename, data):
        if "zip" not in self.plugin["format"]:
            if "filter" in self.plugin:
                filtered = apply_filter(data, self.plugin["filter"])
            else:
                filtered = data
            if type(filtered) == unicode:
                filtered = filtered.encode("utf-8")
            dirname = "data/%s/raw" % self.plugin["name"]
        else:
            filtered = data
            dirname = "data/%s/zip" % self.plugin["name"]
        mkdir_p(dirname)
        path = "%s/%s" % (dirname, basename)
        with open(path, mode="w") as a_file:
            a_file.write(filtered)

