# -*- coding: utf-8 -*-

import os

cfg = {
    "dictname" : "Dictionnaires de l’Académie française : 8ème édition",
    "url" : {
        "from_script" : "",
        "list" : [],
        "count_condition" : {
            "html_exists" : "body > table > tr > td > div"
        },
        "charset": "windows-1252"
    },
    "threadcnt" : 10,
    "filter" : { "html_container" : "body > table" },
    "format" :  {
        "html" : {
            "container_iter" : "tr > td > div",
            "term" : {
                "text_content" : "B b font[color=blue]",
                "lower" : True
            },
            "definition" : {
                "userscript" : ""
            }
        }
    },
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
