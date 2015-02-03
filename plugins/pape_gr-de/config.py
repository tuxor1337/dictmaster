# -*- coding: utf-8 -*-

import os

cfg = {
    "dictname" : "Pape: Handwörterbuch der griechischen Sprache",
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
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
