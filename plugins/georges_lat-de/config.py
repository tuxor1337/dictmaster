# -*- coding: utf-8 -*-

import os

cfg = {
    "dictname" : "Georges: Ausführliches lateinisch-deutsches Handwörterbuch",
    "url" : {
        "from_script" : "",
        "list" : [],
        "charset": "iso-8859-1"
    },
    "threadcnt" : 10,
    "filter" : { "html_container" : "div.zenoCOMain" },
    "format" :  {
        "html" : {
            "singleton" : "",
            "term" : {
                "text_content" : "h2.zenoTXul",
                "userscript" : ""
            },
            "definition" : {
                "userscript" : ""
            }
        }
    },
    "editor": {
        "dups": "enumerate"
    }
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
