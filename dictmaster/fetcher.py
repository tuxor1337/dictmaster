# -*- coding: utf-8 -*-

import os
import urllib2
import zipfile
import glob
from string import lowercase as ALPHA

from util import mkdir_p, CancelableThread

DEFAULT_THREADCNT=6

class FetcherThread(CancelableThread):
    urls = []
    postdata = None
    output_directory = ""
    no = -1

    _i = 0

    def __init__(self, no, urls, output_directory, postdata=None):
        super(FetcherThread, self).__init__()
        self.urls = urls
        self.postdata = postdata
        self.output_directory = output_directory
        self.no = no

    def fullpath(self, basename):
        return os.path.join(self.output_directory, basename)

    def filter_data(self, data):
        return data

    def fetchUrl(self, url):
        self._i += 1
        output_file = "%d_%06d" % (self.no, self._i)
        if os.path.exists(self.fullpath(output_file)):
            return None
        data = self.download_retry(url, self.postdata)
        data = self.filter_data(data)
        if data == None or len(data) < 2:
            return None
        self.write_file(output_file, data)

    def run(self):
        for url in self.urls:
            if self._canceled:
                break
            self.fetchUrl(url)

    def progress(self):
        if self._download_status != "": return self._download_status
        if self._canceled: return ""
        return "{}:{:.1f}%".format(self.no, 100*self._i/float(len(self.urls)))

    def write_file(self, basename, data):
        path = self.fullpath(basename)
        tmp_path = self.fullpath("#%s#"%basename)
        with open(tmp_path, mode="w") as tmp_file:
            tmp_file.write(data)
        os.rename(tmp_path, path)

class Fetcher(CancelableThread):
    class FetcherThread(FetcherThread): pass

    output_directory = ""
    urls = []
    postdata = None

    _subthreads = []

    def __init__(self,
        output_directory,
        urls=[],
        threadcnt=DEFAULT_THREADCNT,
        postdata=None
    ):
        super(Fetcher, self).__init__()
        self._subthreads = [None]*threadcnt
        self.output_directory = os.path.join(output_directory, "raw")
        self.urls = urls
        self.postdata = postdata

    def init_subthreads(self):
        for i in range(len(self._subthreads)):
            url_portion = self.urls[i::len(self._subthreads)]
            self._subthreads[i] = self.FetcherThread(
                no=i,
                urls=url_portion,
                output_directory=self.output_directory,
                postdata=self.postdata
            )

    def progress(self):
        if self._canceled or self._subthreads[0] == None:
            return "Sleeping..."
        prog = "Fetching... "
        for i in range(len(self._subthreads)):
            sub_progress = self._subthreads[i].progress()
            if sub_progress[:11] == "Downloading":
                prog = sub_progress
                break
            else:
                prog += "%s " % self._subthreads[i].progress()[:13]
        return prog

    def run(self):
        if self._canceled:
            return

        self.init_subthreads()
        for i in range(len(self._subthreads)):
            self._subthreads[i].start()

        for i in range(len(self._subthreads)):
            self._subthreads[i].join()

    def cancel(self):
        CancelableThread.cancel(self)
        for i in range(len(self._subthreads)):
            self._subthreads[i].cancel()

class WordFetcher(Fetcher):
    class FetcherThread(FetcherThread): pass
    def __init__(self,
        output_directory,
        url_pattern,
        word_file,
        word_codec,
        threadcnt=DEFAULT_THREADCNT,
        postdata=None
    ):
        super(WordFetcher, self).__init__(
            output_directory=output_directory,
            threadcnt=threadcnt,
            postdata=postdata
        )
        wordlist = []
        with open(word_file, "r") as f:
            wordlist = [w.decode(word_codec[0]).strip() for w in f.readlines()]
        tmplist = []
        for w in wordlist:
            try:
                tmplist.append(urllib2.quote(w.encode(word_codec[1])))
            except:
                print "Codec problem while reading in word file:"
                print w
                break
        self.urls = tmplist
        def run_override(fthread):
            for w in fthread.urls:
                if fthread._canceled:
                    break
                fthread.fetchUrl(url_pattern.format(word=w))
        self.FetcherThread.run = run_override

class AlphanumFetcher(Fetcher):
    class FetcherThread(FetcherThread):
        def progress(self):
            if self._download_status != "": return self._download_status
            if self._canceled: return ""
            total = len(self.urls)*50
            return "{}:{:.1f}%".format(self.no, 100*self._i/float(total))

    def __init__(self,
        output_directory,
        url_pattern,
        alphabet=ALPHA,
        startnum=0,
        threadcnt=DEFAULT_THREADCNT,
        postdata=None
    ):
        super(AlphanumFetcher, self).__init__(
            output_directory=output_directory,
            threadcnt=threadcnt,
            postdata=postdata
        )
        self.urls = alphabet
        def run_override(fthread):
            for a in fthread.urls:
                for i in range(startnum, 200):
                    if fthread._canceled:
                        return
                    try:
                        fthread.fetchUrl(url_pattern.format(
                            alpha=a.lower(),
                            ALPHA=a.upper(),
                            num=i
                        ))
                    except Exception as e:
                        if e.args[0] == "next_block":
                            break
                        else:
                            raise
        self.FetcherThread.run = run_override

class ZipFetcher(Fetcher):
    def __init__(self, output_directory, urls, postdata=None):
        super(ZipFetcher, self).__init__(
            output_directory=output_directory,
            urls=urls,
            threadcnt=1,
            postdata=postdata
        )
        self.output_directory = os.path.join(output_directory, "zip")

class Unzipper(CancelableThread):
    def __init__(self, output_directory):
        super(Unzipper, self).__init__()
        self.output_directory = os.path.join(output_directory, "zip")
        self.unzip_directory = os.path.join(output_directory, "raw")

    def progress(self):
        if self._canceled: return "Sleeping..."
        return "Unzipping..."

    def run(self):
        zdirname = self.output_directory
        for zfile in os.listdir(zdirname):
            z = zipfile.ZipFile("%s/%s" % (zdirname, zfile))
            for n in z.namelist():
                dest = os.path.join(self.unzip_directory, n)
                destdir = os.path.dirname(dest)
                mkdir_p(destdir)
                if not os.path.isdir(dest):
                    zdata = z.read(n)
                    f = open(dest, 'w')
                    f.write(zdata)
                    f.close()
            z.close()

class UrlFetcherThread(FetcherThread):
    def __init__(self, no, urls, output_directory, postdata=None):
        super(UrlFetcherThread, self).__init__(no, urls, output_directory, postdata)
        self.output_path = self.fullpath("url_%d.txt" % self.no)
        self.offset = 0
        if os.path.exists(self.output_path):
            self.offset = sum(1 for line in open(self.output_path))

    def write_file(self, basename, data):
        with open(self.output_path, mode="a") as f:
            f.write(data)

class UrlFetcher(Fetcher):
    class FetcherThread(UrlFetcherThread): pass
    def __init__(self, plugin, postdata=None):
        super(UrlFetcher, self).__init__(
            output_directory=plugin.output_directory,
            postdata=postdata
        )
        self.output_directory = plugin.output_directory
        self.plugin = plugin

    def progress(self):
        if self._canceled or self._subthreads[0] == None:
            return "Sleeping..."
        prog = "Fetching URLs... "
        for i in range(len(self._subthreads)):
            sub_progress = self._subthreads[i].progress()
            if sub_progress[:11] == "Downloading":
                prog = sub_progress
                break
            else:
                prog += "%s " % self._subthreads[i].progress()[:13]
        return prog

    def run(self):
        Fetcher.run(self)
        for f in glob.glob("%s/url_*.txt" % self.output_directory):
            self.plugin.url_list.extend([l.strip() for l in open(f)])

