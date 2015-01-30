# -*- coding: utf-8 -*-

cfg = {
    "name" : "folkets_en-sv",
    "dictname" : "Folkets lexikon En-Sv, ©folkets-lexikon.csc.kth.se",
    "url" : {
        "singleton" : "http://folkets-lexikon.csc.kth.se/folkets/folkets_en_sv_public.xml",
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
                "userscript" : "plugins/folkets_en-sv/custom.py"
            }
        }
    },
}
