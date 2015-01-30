# -*- coding: utf-8 -*-

cfg = {
    "name" : "acadfran",
    "dictname" : "Dictionnaires de l’Académie française : 8ème édition",
    "url" : {
        "from_script" : "plugins/acadfran/custom.py",
        "list" : [],
        "count_condition" : {
            "html_exists" : "body > table > tr > td > div"
        }
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
                "userscript" : "plugins/acadfran/custom.py"
            }
        }
    },
}
