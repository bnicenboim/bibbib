# -*- coding: utf-8 -*-
"""
Created on Sat Dec 28 12:52:54 2013

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author: Bruno Nicenboim <bruno.nicenboim@gmail.com>
"""



import urllib2
from pybtex.database.input.bibtex import Parser
from pybtex.database.output.bibtex import Writer
from io import StringIO
import re
import warnings
import doi_finder
import os
import socket
import titlecase
import sys
from pybtex.core import Entry, Person

_doiurl='http://dx.doi.org/'
_journal_field = "journaltitle"

def doi2bibtex(doi):
    """Returns a bib file from a doi"""
    if doi[:len(_doiurl)] == _doiurl:
        completedoiurl = doi
    elif ("http://"+doi)[:len(_doiurl)] == _doiurl:
        completedoiurl = "http://"+doi
    else:
        completedoiurl = _doiurl +doi
        
    # create the request object and set some headers
    req = urllib2.Request(completedoiurl)
    req.add_header('Accept', 'text/bibliography')
    req.add_header("style", "bibtex")
    

    answer= None   
    tryagain =True
    while tryagain==True:
        try:
            print "(Requesting from internet...)"
            res = urllib2.urlopen(req)
        except socket.timeout as e:
            warnings.warn( "Timeout: %s" % (e) )
            ta=  raw_input("try again? [Y]/n:")
            tryagain =True if (ta=="" or ta[0].capitalize()=="Y") else False
        except socket.error as e:
            warnings.warn( "Some socket error: %s" % (e) )
            ta=  raw_input("try again? [Y]/n:")
            tryagain =True if (ta=="" or ta[0].capitalize()=="Y") else False
        except urllib2.URLError as e:
            if hasattr(e, 'reason'):
                warnings.warn( "We failed to reach a server. Reason:' %s" % (e.reason) )
            elif hasattr(e, 'code'):
                warnings.warn( "The server couldn\'t fulfill the request. Error code:' %s" % (e.code) )
            ta=  raw_input("try again? [Y]/n:")
            tryagain =True if (ta=="" or ta[0].capitalize()=="Y") else False

        else: 
            tryagain=False
            answer = res.read()
    return answer
    
def doi2Entry(doi):
    """Returns a pybtex.database.BibliographyData from a doi"""
    bib_parser = Parser()
    bibtext = doi2bibtex(doi)
    if bibtext != None:
        bibtext = bibtext.decode('utf8')
        bib_data = bib_parser.parse_stream(StringIO(bibtext))
        return bib_data
    else:
        return None
    

def groomBib(bibfile, groomedfile=""):
    """Grooms a bib file according to the present doi or to a doi found in internet. Returns a filename.verified.bib and  filename.unverified.bib"""
    if groomedfile == "":
        groomedfile = bibfile + ".groomed.bib"


    with open(bibfile,"r") as f:
        bstr = f.read()
    # Assume the input is utf8 encoded
    bstr = bstr.decode('utf8')
    
    # Parse the bibtex file
    bib_parser = Parser()
    bib_data = bib_parser.parse_stream(StringIO(bstr))

    #first I groom the original bib file:
    bib_cleandata=cleanBibliographyData(bib_data)
    listofpersons =[]
    if bib_cleandata  != None:
        for (key,entry) in bib_cleandata.entries.items():
            for persontype in entry.persons:  #authors for example
                for ip in range(0,len( entry.persons[persontype])):
                    lastname = entry.persons[persontype][ip].get_part_as_text("last")
                    firstname = entry.persons[persontype][ip].get_part_as_text("first")
                    middle=entry.persons[persontype][ip].get_part_as_text("middle")
                    prelast=entry.persons[persontype][ip].get_part_as_text("prelast")
                    lineage= entry.persons[persontype][ip].get_part_as_text("lineage")
                    result = [element for element in listofpersons   #if they have the same lastname and different names tell
                             if element[0] == lastname and (firstname !=element[1] or middle !=element[2] or prelast != element[3] or lineage != element[4] )] 

                    if len(result) >0:  #warns regarding conflict with names
                        for possibleresults in result:
                            oneversion = Person(last =lastname,first=firstname , middle=middle,prelast=prelast,lineage=lineage)
                            otherversion = Person(last =possibleresults[0],first=possibleresults[1] , middle=possibleresults[2],prelast=possibleresults[3],lineage=possibleresults[4])
                            warnings.warn("Possible problem with authors: %s vs. %s" % (oneversion,otherversion ))
                    listofpersons = listofpersons + [[lastname, firstname, middle,prelast,lineage]]     
    
    savebib(bib_cleandata, groomedfile)

    
    

    
def cleanBibliographyData(BibliographyData):
    """clean a pybtex  BibliographyData and transforms it to biblatex """
    bib_data=None
    if BibliographyData  != None:
        for (key,entry) in BibliographyData.entries.items():
            for persontype in entry.persons:  #authors, editos
                for ip in range(0,len( entry.persons[persontype])):
                    eachperson = entry.persons[persontype][ip]
                     
                    middle = eachperson.get_part_as_text("middle")
                    #add space after periods                    
                    middle = re.sub(r'\.([a-zA-Z])', r'. \1', middle)
                    #add periods after initials
                    middle = re.sub('(^| )(.)($| )', r'\1\2.\3', middle)
                    #and capitalize:
                    middle =  re.sub(r'((^| )[a-z]\.)', lambda match: r'{}'.format(match.group(1).upper()), middle)

                    entry.persons[persontype][ip]._middle =[middle]  #this is the only way I found to modify the name
                    
            # Look for the title field to fix Mendeley's double-bracketing if there's nothing capitalized inside (that is, after the 3rd character: {C ...) or if there's no " inside
            if 'title' in entry.fields:
                title = entry.fields['title']
                if title.startswith("{") and title.endswith("}")  and  re.search( r'..[A-Z]|"',title)==None  :
                    title = title[1:-1]
                
                #remove the final dot
                if title.endswith("."):
                    title=title[:-1]
                if title.endswith(".}"):
                    title=title[:-2] + "}"    
                #add bracketing if there's something capitalized in the middle                    
                if not (title.startswith("{") and title.endswith("}")) and not    re.search( r'..[A-Z]|"',title)==None:   #in this case add more bracketing
                    title = "{" + title +"}"
                    
                entry.fields['title']=title
                
                
            #check if the format of the pages
            if 'pages' in entry.fields:
                pages = entry.fields['pages']
                pageparts = re.findall( r'(\d+)(-+)(\d+)',pages)
                if len(pages) >0 and  len(pageparts) ==0:
                    warnings.warn( "only one page found  in %s" % key)
                elif len(pageparts) ==0:
                    warnings.warn( "no page field in %s" % key)
                else:
                    pagei = pageparts[0][0]
                    pagef = pageparts[0][2]
                    if len(pagef) < len(pagei):  #to check if it's cut                
                        pagef = pagei[:-len(pagef)]  + pagef
                    if int(pagef) <=  int(pagei):  #checking if final page is lower than the initial
                        warnings.warn( "error in page entry in %s: the final page is smaller than the initial" % key)
                    pages = pagei + "--" + pagef
                    entry.fields['pages'] = pages
                
             #change journal for journaltitle
            if 'journal' in entry.fields and not _journal_field in entry.fields:
                journaltitle = entry.fields['journal']
                entry.fields[_journal_field] =journaltitle
                del entry.fields['journal']
            elif 'journal' in entry.fields and _journal_field in entry.fields:
                journaltitle = entry.fields[_journal_field]
                journal = entry.fields['journal']
                remove = raw_input("Journal field is '%s' and %s field is '%s'. Can I remove journal field? Y/n" % (journal,_journal_field,journaltitle))
                if remove =="" or remove[0].capitalize()=="Y":
                    del entry.fields['journal']
                else:
                    remove2 = raw_input(" Can I remove %s field then? Y/n"  %_journal_field)
                    if remove2 =="" or remove2[0].capitalize()=="Y":
                        del entry.fields[_journal_field]
                      
                        
                    
                    
            
            #I have to escape characters
            #check the titles in title case
            #add double brackets in title when needed 
        bib_data = Parser()
        bib_data = BibliographyData
    
    return bib_data



def doi2biblatex(doi):
    """Returns a a clean pybtex.database.BibliographyData that more or less complies with biblatex from a doi"""
    bib_data = Parser()
    bib_data = cleanBibliographyData(doi2Entry(doi))
    return bib_data
    




def changeThisforThat(oldvalue,newvalue,extratext):
  """Asks if you want to change an old value for a new value"""
  keep = raw_input('%s - Old value ={%s}; New value = {%s}. Change [Y]/n:' % (extratext,oldvalue,newvalue))
  keep = keep[0].capitalize() if len(keep)>0 else ""
  if keep != "N":
      return newvalue
  else:
      return oldvalue


def verifyBib(bibfile, verifiedfile="", unverifiedfile=""):
    """Verifies a bib file according to the present doi or to a doi found in internet. Returns a filename.verified.bib and  filename.unverified.bib"""
    if verifiedfile == "":
        verifiedfile = bibfile + ".verified.bib"
    if unverifiedfile == "":
        unverifiedfile = bibfile + ".unverified.bib"
        
    with open(bibfile,"r") as f:
        bstr = f.read()
    # Assume the input is utf8 encoded
    bstr = bstr.decode('utf8')

    # Parse the bibtex file
    bib_parser = Parser()
    bib_data = bib_parser.parse_stream(StringIO(bstr))

    #first I groom the original bib file:
    bib_data=cleanBibliographyData(bib_data)
    
    
    newbib_parser = Parser()
    unverif_parser = Parser()
    #bib_verifdata = bib_parser.parse_stream(StringIO(""))
    entrynumber=0
    check =0      
    for (key,entry) in bib_data.entries.items():
        check = check+1
        print "-------------------------------------"
        print "Checking entry %d of %d" % (check,len(bib_data.entries))
        print "Entry: %s..." % key
        title = entry.fields['title'] if entry.fields.has_key('title') else ""
        author = entry.fields['author'] if entry.persons.has_key('author') else ""
        journal = entry.fields[_journal_field] if entry.fields.has_key(_journal_field) else ""
        volume = entry.fields['volume'] if entry.fields.has_key('volume') else ""
        pages = entry.fields['pages'] if entry.fields.has_key('pages') else ""
        print "('%s' by %s)" % (title,author)
        #fix from here
        """first look for doi in entry if not use doi_finder, 
        if doi is found, 
        then download entryfrom internet and 
        hten compare with the actual entry, ask for changes
        """
        doi=None
        if 'doi' in entry.fields:
            doi = entry.fields['doi']
            print "doi found in bib file..."
            verificationmode="from given doi"
        else: #if 'doi' is not in entry.fields, we try to find it
            print "Looking for doi in crossref..."
            doi = doi_finder.crossref_auth_title_to_doi(doi_finder.detex(author), doi_finder.detex(title))
            verificationmode="from searched doi in crossref"
            
            if  doi != None:
                print "doi found in crossref"
            else:
                print "Looking for doi in google..."
                doi = doi_finder.google_doi(journal, volume, pages, doi_finder.detex(title))
                verificationmode="from searched doi in google"
                if doi != None:
                    print "doi found in google scholars"
                
        if  doi != None:
            print "Retrieving fields from internet..."
            entriesfrominternet = doi2biblatex(doi)
            ##check if it's the right entry:
            if entriesfrominternet != None and entriesfrominternet.entries[entriesfrominternet.entries.keys()[0]].fields.has_key("title"):
                titlefrominternet= entriesfrominternet.entries[entriesfrominternet.entries.keys()[0]].fields["title"]  
                if doi_finder.fuzzy_match(title.lower(), titlefrominternet.lower()) < .9:
                    usedoi = raw_input("maybe wrong entry... Title from internet is %s. Is it right? y/[N]:" % titlefrominternet)
                    if usedoi=="" or usedoi[0].capitalize()=="N":
                        print "Avoiding entry..."     
                        entriesfrominternet = None 
                    else:
                        print "Using entry from internet..."     
                    
            else:
                print "incomplete data from internet, avoiding entry..."     
                entriesfrominternet = None 
                          

            
        else:
            print "doi not found, avoiding entry..."
            entriesfrominternet = None
            
        if entriesfrominternet !=None:
            fieldsfrominternet = entriesfrominternet.entries[entriesfrominternet.entries.keys()[0]].fields    #It will contain only one entry, so I take the fields from the first one
            personsfrominternet = entriesfrominternet.entries[entriesfrominternet.entries.keys()[0]].persons     #authors, editors, etc   
            verifiedfields=""
            #example            
            """
            Entry(u'article', fields={u'doi': u'10.1016/S0364-0213(99)80005-6', u'title': u'{A probabilistic model of lexical and syntactic access and disambiguation}',
            u'url': u'http://doi.wiley.com/10.1016/S0364-0213(99)80005-6', u'journaltitle': u'Cognitive Science', u'issn': u'03640213', 
            u'mendeley-tags': u'Phd1,expectations,predictions', u'number': u'2', u'month': u'06', u'volume': u'2000', 
            u'file': u':home/bruno/Documents/Papers//Jurafsky - 1996 - A probabilistic model of lexical and syntactic access and disambiguation.pdf:pdf', u'year': u'1996',
            u'keywords': u'Phd1,expectations,predictions', u'pages': u'7--194'}, 
            persons={u'author': [Person(u'Jurafsky, D')]})
            """
                        
            for persons in personsfrominternet:
                verifiedfields = persons +"; "+verifiedfields
               
                if entry.persons.has_key(persons): #check if there's a person field like author, maybe editor
                   # unicode(entry.persons[persons][0]) == "apellido, nombre"
                    if entry.persons[persons] != personsfrominternet[persons]: #then compare with the old one and ask
                        #First checks for badly bwritten entries:
                        for i in range(0,min(len(entry.persons[persons]),len(personsfrominternet[persons]))): #checks the common persons
                            lastbib = entry.persons[persons][i].get_part_as_text("last")
                            lastinet = personsfrominternet[persons][i].get_part_as_text("last")
                            firstbib = entry.persons[persons][i].get_part_as_text("first")
                            firstinet = personsfrominternet[persons][i].get_part_as_text("first")
                            middlebib = entry.persons[persons][i].get_part_as_text("middle")
                            middleinet = personsfrominternet[persons][i].get_part_as_text("middle")                       
                            lineagebib =  entry.persons[persons][i].get_part_as_text("lineage")
                            lineageinet = personsfrominternet[persons][i].get_part_as_text("lineage")                       
                            prelastbib =  entry.persons[persons][i].get_part_as_text("prelast")
                            prelastinet = personsfrominternet[persons][i].get_part_as_text("prelast")                       
                            
                            #check if the name in internet has less info that the one stored
                            if lastbib==lastinet and (firstbib == firstinet[0] or firstbib == firstinet[0]+"." ):
                                print "incomplete last name in internet for %s - Skipping name %s ..." % (unicode(entry.persons[persons][i]),unicode(personsfrominternet[persons][i]))
                            else: #if there's the same amount of info then check the names
                                if unicode(entry.persons[persons][i]).strip() != unicode(personsfrominternet[persons][i]).strip():
                                    entry.persons[persons][i] = changeThisforThat(entry.persons[persons][i],personsfrominternet[persons][i],"Change for %s." % persons)
                        #check for missing or extra authors        
                        if len(entry.persons[persons]) < len(personsfrominternet[persons]): # missing authors in bib file
                            for j in range(i+1,len(personsfrominternet[persons]) ):
                                missing = changeThisforThat(None,personsfrominternet[persons][j],"Missing person for %s." % persons)
                                if missing != None:                                            
                                    entry.persons[persons].append(missing)
                        elif len(entry.persons[persons]) > len(personsfrominternet[persons]): # extra authors in bib file
                            for j in range(i+1,len(entry.persons[persons]) ):
                                extra = changeThisforThat(entry.persons[persons][j],None,"Extra person for %s." % persons)
                                if extra == None:
                                    entry.persons[persons].remove(entry.persons[persons][j])
                            
                        
                else: #if there's  new field online, the field has to be added
                    entry.fields[persons] = fieldsfrominternet[persons]                
                    
                
            for fieldname in fieldsfrominternet:
                verifiedfields = fieldname +"; "+verifiedfields 
                if entry.fields.has_key(fieldname): #i check if there are new fields first
                    if entry.fields[fieldname] != fieldsfrominternet[fieldname]: #then compare with the old ones and ask
                          #don't try to change the title if it's in title case:
                          if not (fieldname== "title" and fieldsfrominternet[fieldname] == titlecase.titlecase(fieldsfrominternet[fieldname])):
                              entry.fields[fieldname] = changeThisforThat(entry.fields[fieldname],fieldsfrominternet[fieldname],"Change for %s." % fieldname)
                          else:
                              print "avoiding title '%s' because of titlecase" % fieldsfrominternet[fieldname]
                else: #if there's  new field online, the field has to be added
                    entry.fields[fieldname] = fieldsfrominternet[fieldname]
            
            
  
            textverif = "%s were verified %s" % (verifiedfields,verificationmode)
            entry.fields["citation-verif"] = textverif
            #add to new bib            
            newbib_parser.data.add_entry(key, entry)   #these are the verified entries
            entrynumber=entrynumber+1
        else: # if cit.citation() =={}: #if we failed to find it in internet 
            unverif_parser.data.add_entry(key, entry)

    savebib(unverif_parser.data,unverifiedfile)
    savebib(newbib_parser.data,verifiedfile)
    print "%s/%s entries were checked. %s were verified" % (check, len(bib_data.entries), entrynumber)
    return "done"

                        

def savebib(bib_parser,filename):
    """ Saves a pybtex.database.BibliographyData in a file"""
    writer = Writer()
    strm = StringIO()
    writer.write_stream(bib_parser, strm)
    
    # Assume the input is utf8 encoded
    f = open(filename,"w")
    f.write(strm.getvalue().encode('utf8'))
    f.close()
    
    




if __name__ == '__main__':
    if  len(sys.argv) > 1:
        bib = sys.argv[1]
    else:
        bib = raw_input('bibfile:')
    if bib =="":
        bib = "test.bib"
    #add current path 
    bib = "%s/%s" % ( os.getcwd(),bib) if not os.path.isfile(bib) else bib   
    print verifyBib(bib)
    
