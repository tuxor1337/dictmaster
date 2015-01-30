# -*- coding: utf-8 -*-

cfg = {
    "name" : "xmlittre",
    "dictname" : "XMLittré, ©littre.org",
    "url" : {
        "singleton" : "https://bitbucket.org/Mytskine/xmlittre-data/get/master.zip"
    },
    "threadcnt" : 1,
    "format" :  {
        "zip" : {
            "userscript" : "plugins/xmlittre/custom.py"
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
                "userscript" : "plugins/xmlittre/custom.py"
            }
        }
    },
}
