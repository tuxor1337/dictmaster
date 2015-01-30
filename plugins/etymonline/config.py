# -*- coding: utf-8 -*-

cfg = {
    "name" : "etymonline",
    "dictname" : "Online Etymology Dictionary, ©Douglas Harper/etymonline.com",
    "url" : {
        "pattern" : "http://www.etymonline.com/index.php?l={A..Z}&p={0..9}",
        "itermode" : {
            "alphanum" : {
                "count_start" : 0
            }
        },
        "count_condition" : {
            "html_exists" : "div#dictionary dl"
        }
    },
    "threadcnt" : 10,
    "filter" : { "html_container" : "div#dictionary dl" },
    "format" :  {
        "html" : {
            "alternating" : { "a" : "dt", "b" : "dd" },
            "term" : {
                "text_content" : "a",
                "regex" : [ (" +\([^)]+\)$","") ]
            },
            "definition" : {
                "userscript" : "plugins/etymonline/custom.py"
            }
        }
    },
}
