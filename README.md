bibbib
======

Some python utilities to manage bib files. 

* bibGen.py:
Executes verifyBib function that verifies a bib file according to doi of each entry or to a doi found in internet. 
Returns a filename.verified.bib and  filename.unverified.bib

Synax:
src/bibGen filename.bib


Requirements:
doi_finder.py (https://github.com/torfbolt/DOI-finder), pybtex (http://pybtex.sourceforge.net/) and titlecase.py (https://launchpad.net/titlecase.py/trunk/0.2) should be in the path

