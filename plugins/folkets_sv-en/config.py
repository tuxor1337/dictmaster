# -*- coding: utf-8 -*-

cfg = {
    "name" : "folkets_sv-en",
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
                "userscript" : "plugins/folkets_sv-en/custom.py"
            }
        }
    },
}
