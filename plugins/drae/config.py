# -*- coding: utf-8 -*-

import os

# TODO: enmiendas articulos, cf.
#   https://github.com/vibragiel/glotologia/blob/master/enmiendas_drae/enmiendas-drae.py

cfg = {
    "dictname" : "Diccionario de la lengua española: 22a edición",
    "url" : {
        "pattern" : "http://lema.rae.es/drae/srv/search?val={word}",
        "itermode" : {
            "wordlist" : {
                "from_file" : "words.txt",
                "decode" : "utf-8"
                "encode" : "iso-8859-1"
            }
        },
        "count_condition" : {
            "always_continue": True
        },
        "charset": "utf-8",
        "postdata": "TS014dfc77_id=3"\
            + "&TS014dfc77_cr=6df4b31271d91b172321d2080cefbee7:becd:943t352k:1270247778"\
            + "&TS014dfc77_76=0"\
            + "&TS014dfc77_86=0"\
            + "&TS014dfc77_md=1"\
            + "&TS014dfc77_rf=0"\
            + "&TS014dfc77_ct=0"\
            + "&TS014dfc77_pd=0"
    },
    "threadcnt" : 10,
    "filter" : { "html_container" : "html" },
    "format" :  {
        "html" : {
            "container_iter" : "body > div",
            "term" : {
                "text_content" : "p.p span.f b"
            },
            "definition" : {
                "userscript" : ""
            },
            "codec": "utf-8"
        }
    },
    "editor": {
        "dups": "enumerate"
    }
}

cfg["name"] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[1]
