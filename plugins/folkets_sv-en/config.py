# -*- coding: utf-8 -*-

import os

cfg = {
    "dictname" : "Folkets lexikon Sv-En, ©folkets-lexikon.csc.kth.se",
    "url" : {
        "singleton" : "http://folkets-lexikon.csc.kth.se/folkets/folkets_sv_en_public.xml",
        "charset": "utf-8"
    },
    "threadcnt" : 1,
    "format" :  {
        "html" : {
            "container_iter" : "word",
            "term" : {
                "attr" : {
                    "key" : "value"
                }
            },
            "definition" : {
                "userscript" : ""
            }
        }
    },
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
