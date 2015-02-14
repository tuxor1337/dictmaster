# -*- coding: utf-8 -*-

import os
import urllib2
import zipfile
from string import lowercase as ALPHA

from util import mkdir_p, CancelableThread

DEFAULT_THREADCNT=4

class FetcherThread(CancelableThread):
    urls = []
    postdata = None
    output_directory = ""
    no = -1
    filter_data = lambda x: x

    _i = 0

    def __init__(self, no, urls, output_directory, postdata=None, filter_data=lambda x: x):
        super(FetcherThread, self).__init__()
        self.urls = urls
        self.postdata = postdata
        self.output_directory = output_directory
        self.no = no
        self.filter_data = filter_data

    def fullpath(self, basename):
        return os.path.join(self.output_directory, basename)

    def run(self):
        for url in self.urls:
            if self._canceled:
                break
            self._i += 1
            output_file = "%d_%06d" % (self.no, self._i)
            if os.path.exists(self.fullpath(output_file)):
                continue
            data = self.download_retry(url, self.postdata)
            if data == None or len(data) < 2:
                continue
            try:
                data = self.filter_data(data)
            except Exception as e:
                if e.args[0] == "rejected":
                    continue
                elif e.args[0] == "nextBlock":
                    self.urls.nextBlock()
                else:
                    raise
            self.write_file(output_file, data)

    def progress(self):
        if self._download_status != "":
            return self._download_status
        if self._canceled:
            return "Sleeping..."
        return "{}:{}/{}".format(self.no, self._i, len(self.urls))

    def write_file(self, basename, data):
        path = self.fullpath(basename)
        tmp_path = self.fullpath("#%s#"%basename)
        with open(tmp_path, mode="w") as tmp_file:
            tmp_file.write(data)
        os.rename(tmp_path, path)

class Fetcher(CancelableThread):
    output_directory = ""
    urls = []
    filter_fct = lambda x: x
    postdata = None

    _subthreads = []

    def __init__(self,
        output_directory,
        filter_fct=lambda x: x,
        urls=[],
        threadcnt=DEFAULT_THREADCNT,
        postdata=None
    ):
        super(Fetcher, self).__init__()
        self._subthreads = [None]*threadcnt
        self.output_directory = os.path.join(output_directory, "raw")
        self.urls = urls
        self.filter_fct = filter_fct
        self.postdata = postdata

    def init_subthreads(self):
        for i in range(len(self._subthreads)):
            url_portion = self.urls[i::len(self._subthreads)]
            self._subthreads[i] = FetcherThread(
                no=i,
                urls=url_portion,
                output_directory=self.output_directory,
                filter_data=self.filter_fct,
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

class WordlistUrlGetter:
    def __init__(self, wordlist, pattern):
        self.pattern = pattern
        self.wordlist = wordlist

    def __getitem__(self, sliced):
        return [self.pattern.format(word=w) for w in self.wordlist[sliced]]

class WordFetcher(Fetcher):
    def __init__(self,
        output_directory,
        url_pattern,
        word_file,
        word_codec,
        filter_fct=lambda x: x,
        threadcnt=DEFAULT_THREADCNT,
        postdata=None
    ):
        super(WordFetcher, self).__init__(
            output_directory=output_directory,
            threadcnt=threadcnt,
            filter_fct=filter_fct,
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
        wordlist = tmplist
        self.urls = WordlistUrlGetter(wordlist, url_pattern)

class AlphanumUrlGetter:
    def __init__(self, alphabet, startnum, pattern):
        self.pattern = pattern
        self.alphabet = alphabet
        self.startnum = startnum
        self._block = 0
        self._pointer = -1

    def __getitem__(self, sliced):
        if type(sliced) == int:
            a = self.alphabet[sliced / 1000]
            sliced = sliced % 1000
            return self.pattern.format(
                alpha=a.lower(),
                ALPHA=a.upper(),
                num=sliced
            )
        return AlphanumUrlGetter(self.alphabet[sliced], self.startnum, self.pattern)

    def __iter__(self): return self
    def __len__(self): return len(self.alphabet)
    def nextBlock(self): self._block += 1

    def next(self):
        self._pointer += 1
        if self._pointer >= 200:
            self._pointer = 0
            self.nextBlock()
        if self._block >= len(self.alphabet):
            raise StopIteration
        else:
            a = self.alphabet[self._block]
            return self.pattern.format(alpha=a.lower(), ALPHA=a.upper(), num=self._pointer)

class AlphanumFetcher(Fetcher):
    def __init__(self,
        output_directory,
        url_pattern,
        alphabet=ALPHA,
        startnum=0,
        filter_fct=lambda x: x,
        threadcnt=DEFAULT_THREADCNT,
        postdata=None
    ):
        super(AlphanumFetcher, self).__init__(
            output_directory=output_directory,
            threadcnt=threadcnt,
            filter_fct=filter_fct,
            postdata=postdata
        )
        self.urls = AlphanumUrlGetter(alphabet, startnum, url_pattern)

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
        if self._canceled:
            return "Sleeping..."
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

