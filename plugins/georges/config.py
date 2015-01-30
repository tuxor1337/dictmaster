# -*- coding: utf-8 -*-

cfg = {
    "name" : "georges",
    "dictname" : "Georges: Ausführliches lateinisch-deutsches Handwörterbuch",
    "url" : {
        "from_script" : "plugins/georges/custom.py",
        "list" : [],
        "charset": "iso-8859-1"
    },
    "threadcnt" : 10,
    "filter" : { "html_container" : "div.zenoCOMain" },
    "format" :  {
        "html" : {
            "singleton" : "",
            "term" : {
                "text_content" : "h2.zenoTXul"
            },
            "definition" : {
                "userscript" : "plugins/georges/custom.py"
            }
        }
    },
}
