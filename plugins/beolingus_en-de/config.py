# -*- coding: utf-8 -*-

import os

cfg = {
    "dictname" : "BEOLINGUS Englisch-Deutsch",
    "url" : {
        "singleton" : "http://ftp.tu-chemnitz.de/pub/Local/urz/ding/de-en-devel/de-en.txt.zip"
    },
    "threadcnt" : 1,
    "format" :  {
        "zip" : { },
        "dictfile" : {
            "fieldSplit" : "::",
            "subfieldSplit" : "|",
            "subsubfieldSplit" : ";",
            "flipCols": True,
            "term": { },
            "definition": { }
        }
    },
    "editor": {
        "dups": "enumerate"
    }
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
