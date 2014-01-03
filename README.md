bibbib
======

Some python utilities to manage bib files. 

___*Syntax:*___

_usage_: bibGen.py \[\-h\] \(\-v \| \-g \| \-c\) file.bib

Fix your bib file

_positional arguments_:

+ file.bib            File to process

_optional arguments_:
+  -h, --help          show this help message and exit
+  -v, --verification  Verifies the bib file comparing with info in internet:
                      produces two files file.bib.verified.bib and
                      file.bib.unverified
+  -g, --groom         Grooms the bib file. It produces file.bib.groom.bib
+  -c, --clean         Removes unnecesary fields from the bib file (so that it
                      can be safely submitted). It produces file.bib.clean.bib


___*Requirements:*___
+ [doi_finder.py](https://github.com/torfbolt/DOI-finder)
+ [pybtex](http://pybtex.sourceforge.net/)
+ [titlecase.py](https://launchpad.net/titlecase.py/trunk/0.2)

___*Note:*___
It was inspired from a script called "mendmend.py" that I have no clue who the author was....
