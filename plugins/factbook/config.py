# -*- coding: utf-8 -*-

import os

cfg = {
    "dictname" : "The World Factbook 2014",
    "url" : {
        "list" : [
            "https://www.cia.gov/library/publications/download/download-2014/geos.zip",
            "https://www.cia.gov/library/publications/download/download-2014/graphics.zip"
        ]
    },
    "threadcnt" : 1,
    "format" :  {
        "zip" : {
            "userscript" : ""
        },
        "html" : {
            "container_iter" : "div.CollapsiblePanel",
            "term" : {
                "text_content": "h2",
                "regex": [
                    [r"^(.*) :: (.*)$",r"\2 \1"]
                ]
            },
            "definition" : {
                "userscript" : ""
            },
            "alts" : [
                ("h2",[
                    [r"^Introduction :: (.*)$",r"\1"],
                    [r"^(.*) :: (.*)$", r""]
                ])
            ]
        }
    },
    "editor": {
        "dups": "enumerate",
        "no_auto_synonyms": True
    }
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
