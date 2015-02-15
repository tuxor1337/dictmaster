# -*- coding: utf-8 -*-

import sys
import time
import os
import errno

from urllib2 import URLError
from httplib import BadStatusLine
import urllib2

import importlib

from pyquery import PyQuery as pq
from lxml import etree

import threading

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

def html_container_filter(container, charset="utf-8", bad_content=None):
    def tmp_func(fthread, data):
        encoded_str = data.decode(charset).encode("utf-8")
        parser = etree.HTMLParser(encoding="utf-8")
        doc = pq(etree.fromstring(encoded_str, parser=parser))
        if len(doc(container)) == 0: return None
        elif bad_content != None and doc(container).text() == bad_content:
            return None
        else: return doc(container).html().encode(charset)
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
            response = urllib2.urlopen(url, params)
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

