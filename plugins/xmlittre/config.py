# -*- coding: utf-8 -*-

import os

cfg = {
    "dictname" : "XMLittré, ©littre.org",
    "url" : {
        "singleton" : "https://bitbucket.org/Mytskine/xmlittre-data/get/master.zip"
    },
    "threadcnt" : 1,
    "format" :  {
        "zip" : {
            "userscript" : ""
        },
        "html" : {
            "container_iter" : "entree",
            "term" : {
                "attr" : {
                    "key" : "terme"
                },
                "lower" : True
            },
            "definition" : {
                "userscript" : ""
            }
        }
    },
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
