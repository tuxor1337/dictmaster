# -*- coding: utf-8 -*-

import os

cfg = {
    "dictname" : "dict.cc Deutsch-Englisch",
    "format" :  {
        "zip" : { },
        "dictfile" : {
            "fieldSplit" : "\t",
            "flipCols": False,
            "term": { },
            "definition": { }
        }
    },
    "editor": {
        "dups": "cat"
    }
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
