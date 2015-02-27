# -*- coding: utf-8 -*-

import sys
import time
import os
import errno
import sqlite3

from urllib2 import URLError, HTTPError
from httplib import BadStatusLine
import urllib2

import importlib

import unicodedata

from pyquery import PyQuery as pq
from lxml import etree

import threading

FLAGS = {
    "FETCHED": 1 << 0,
    "PROCESSED": 1 << 1,
    "RAW_FETCHER": 1 << 2,
    "URL_FETCHER": 1 << 3,
    "ZIP_FETCHER": 1 << 4,
    "FILE": 1 << 5,
    "MEMORY": 1 << 6,
    "DUPLICATE": 1 << 7
}

def warn_nl(msg):
    sys.stdout.write("\r\n{}\n".format(msg))
    sys.stdout.flush()

def mkdir_p(path):
    try: os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path): pass
        else: raise

def load_plugin(plugin_name, popts, dirname):
    if dirname == "": dirname = "data/%s/" % plugin_name
    try:
        plugin_module = importlib.import_module("dictmaster.plugins.%s" % plugin_name)
        pthread = plugin_module.Plugin(popts, dirname)
    except ImportError as e:
        print e.args; pthread = None
    return pthread

def words_to_db(word_file, cursor, word_codec):
    wordlist = [w.decode(word_codec[0]).strip() for w in open(word_file,"r")]
    tmplist = []
    for w in wordlist:
        try: tmplist.append(urllib2.quote(w.encode(word_codec[1]), ""))
        except: print "Codec error reading word file:", w; break
    cursor.executemany('''
        INSERT INTO raw (uri,flag) VALUES (?,?)
    ''', [(w, FLAGS["RAW_FETCHER"]) for w in wordlist])

def find_synonyms(term, definition, alts):
    greek_alph = u'αιηωυεοςρτθπσδφγξκλζχψβνμ'
    latin_alph = u'aihwueosrtqpsdfgcklzxybnm'

    def add_alt(alts, a):
        if a not in alts and a != term: alts.append(a)

    def add_greek_alt(alts, a):
        orig_a = a
        a = remove_accents(a).lower()
        add_alt(alts, a)
        add_alt(alts, a.replace("-",""))
        for x,y in zip(greek_alph,latin_alph):
            a = a.replace(x,y)
        add_alt(alts,a)
        add_alt(alts,a.replace("-",""))

    add_greek_alt(alts,term)
    for delimiter in [",","#",";"]:
        [add_greek_alt(alts,c.strip()) for c in term.split(delimiter)]

    return alts

def remove_accents(input_str):
    if not isinstance(input_str, unicode):
        input_str = unicode(input_str,"utf8")
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def html_container_filter(container, charset="utf-8", bad_content=None):
    def tmp_func(fthread, data):
        if data == None or len(data) < 2: return None
        encoded_str = data.decode(charset).encode("utf-8")
        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(encoded_str, parser=parser))
        if len(doc(container)) == 0: return None
        elif bad_content != None and doc(container).text() == bad_content:
            return None
        else: return doc(container).html()
    return tmp_func

"""
The CancelableThread is a convenience class that all threads in dictmaster
are instances of. Apart from the cancel() method it provides convenient access
to a (cancelable and feedback providing) download method.
"""
class CancelableThread(threading.Thread):
    _canceled = False
    _download_status = ""

    def __init__(self):
        super(CancelableThread, self).__init__()
        self.daemon = True

    def progress(self):
        if self._canceled: return "Sleeping..."
        return "Active..."

    def cancel(self): self._canceled = True

    def _chunk_download(self, response, total_size):
        data, chunk_size = "", 2**16
        while True:
            if self._canceled:
                data = None
                break
            chunk = response.read(chunk_size)
            if not chunk: break
            data += chunk
            self._download_status = "Downloading... {: 6d} of {: 6d} KB".format(
                len(data)/1000, total_size/1000
            )
        self._download_status = ""
        return data

    def download_retry(self, url, params=None):
        if self._canceled: return None
        try:
            try: response = urllib2.urlopen(url, params, timeout=5)
            except HTTPError as e:
                if e.code == 404: return ""
                else: raise
            total_size = response.info().getheader('Content-Length')
            if total_size != None: total_size = int(total_size.strip())
            else: total_size = 0
            if total_size > 5*2**16:
                print("\nDownloading large file ({:.2f} MB)!".format(total_size/1000000.0))
                data = self._chunk_download(response, total_size)
            else: data = response.read()
            return data
        except (URLError, BadStatusLine):
            warn_nl("Connection to %s failed. Retrying..." % url)
            time.sleep(0.5)
            return self.download_retry(url, params)
        except Exception as e:
            warn_nl("Error on %s: '%s'. Retrying..." % (url, e))
            time.sleep(0.5)
            return self.download_retry(url, params)

