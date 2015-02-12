# -*- coding: utf-8 -*-

from pyquery import PyQuery as pq

from urllib2 import URLError
from httplib import BadStatusLine
import urllib2

import sys, threading, time, importlib, os
from string import lowercase as ALPHA

from util import mkdir_p

def fetch(plugin):
    print("Fetching for plugin %s..." % plugin["name"])

    ftList = []
    url = None

    if "from_script" in plugin["url"]:
        userscript = importlib.import_module("plugins.%s.custom" % plugin["name"])
        plugin["url"]["list"] = userscript.get_url()

    for j in range(plugin["threadcnt"]):
        ft = fetcherThread(j, plugin, url)
        ftList.append(ft)
        t = threading.Thread(target=ft.fetch)
        t.daemon = True
        t.start()

    while threading.active_count() > 1:
        time.sleep(0.2)

    print("\r\n...done fetching.")

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
    except Exception as e:
        sys.stdout.write("\rError on %s: '%s'. Retrying...\n" % (url, e))
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
        if "zip" in self.plugin["format"]:
            self.output_dir = "data/%s/zip" % self.plugin["name"]
        else:
            self.output_dir = "data/%s/raw" % self.plugin["name"]

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
            elif "wordlist" in self.plugin["url"]["itermode"]:
                wordlist_opts = self.plugin["url"]["itermode"]["wordlist"]
                wordlist = []
                f = None
                if "from_file" in wordlist_opts:
                    fname = "data/%s/%s" % (self.plugin["name"],wordlist_opts["from_file"])
                    f = open(fname,"r")
                    wordlist = f.readlines()
                wordlist = [\
                    wordlist[i].strip() for i in \
                    range(self.threadno, len(wordlist), self.plugin["threadcnt"]) \
                ]
                self.fetch_words(wordlist)
                f.close() if f else ""

    def fetch_list(self, url_list):
        for i,url in enumerate(url_list):
            sys.stdout.write("\r\033[%dC%d:%04d" % (7*self.threadno+1, self.threadno, i))
            sys.stdout.flush()
            output_file = "%06d" % (i*self.plugin["threadcnt"]+self.threadno)
            if self.file_exists(output_file):
                continue
            params = None
            if "postdata" in self.plugin["url"]:
                params = "postdata"
            data = download(url, params)
            if "charset" in self.plugin["url"] and "zip" not in self.plugin["format"]:
                data = data.decode(self.plugin["url"]["charset"])
            if self.stop_count(data):
                break
            self.write_file(output_file, data)

    def fetch_alphanum(self, letterrange, numberrange):
        for letter in letterrange:
            for pagenumber in numberrange:
                sys.stdout.write("\r\033[%dC%s:%03d" % (6*self.threadno+1, letter, pagenumber))
                sys.stdout.flush()
                output_file = "%s%04d" % (letter, pagenumber)
                if self.file_exists(output_file):
                    continue
                url = self.plugin["url"]["pattern"].replace("{a..z}", letter.lower()) \
                    .replace("{A..Z}", letter.upper()) \
                    .replace("{0..9}", "%d" % pagenumber)
                params = None
                if "postdata" in self.plugin["url"]:
                    params = "postdata"
                data = download(url, params)
                if "charset" in self.plugin["url"] and "zip" not in self.plugin["format"]:
                    data = data.decode(self.plugin["url"]["charset"])
                if self.stop_count(data):
                    break
                self.write_file(output_file, data)

    def fetch_words(self, wordlist):
        wordlist_opts = self.plugin["url"]["itermode"]["wordlist"]
        for i,word in enumerate(wordlist):
            word = word.decode(wordlist_opts["decode"])
            if i % 7 == 0:
                sys.stdout.write("\r\033[%dC%d:%s" % (
                    6*self.threadno+1,
                    self.threadno,
                    word[:3].encode("utf-8")
                ))
                sys.stdout.flush()
            output_file = word
            if self.file_exists(output_file):
                continue
            try:
                url = self.plugin["url"]["pattern"].replace("{word}", urllib2.quote(
                    word.encode(wordlist_opts["encode"])
                ))
            except:
                print("\n%s" % word)
                continue
            params = None
            if "postdata" in self.plugin["url"]:
                params = self.plugin["url"]["postdata"]
            data = download(url, params)
            if "charset" in self.plugin["url"] and "zip" not in self.plugin["format"]:
                try:
                    data = data.decode(self.plugin["url"]["charset"])
                except:
                    print("Problem decoding data from %s." % url)
            if self.stop_count(data):
                break
            self.write_file(output_file, data)

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

    def file_exists(self, basename):
        path = os.path.join(self.output_dir, basename)
        return os.path.exists(path)

    def write_file(self, basename, data):
        if "zip" not in self.plugin["format"]:
            if "filter" in self.plugin:
                filtered = apply_filter(data, self.plugin["filter"])
            else:
                filtered = data
            if type(filtered) == unicode:
                filtered = filtered.encode("utf-8")
        else:
            filtered = data
        mkdir_p(self.output_dir)
        path = os.path.join(self.output_dir, basename)
        tmp_path = os.path.join(self.output_dir, "#%s#"%basename)
        with open(tmp_path, mode="w") as tmp_file:
            tmp_file.write(filtered)
        os.rename(tmp_path, path)

