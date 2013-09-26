#!/usr/bin/env python
# -*- coding: utf-8 -*-

# deviantArt Gallery Ripper
# http://lovecastle.org/dagr/
# https://github.com/voyageur/dagr

# Copying and distribution of this file, with or without
# modification, is permitted.

# This file is offered as-is, without any warranty.

import getopt, mechanize, os, random, re, sys, traceback
from urllib2 import URLError, HTTPError
from httplib import IncompleteRead

MAX = 1000000 #max deviations
VERSION="0.51"
NAME = os.path.basename(__file__)
USERAGENTS = (
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.835.202 Safari/535.1',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:7.0.1) Gecko/20100101',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)',
    'Opera/9.99 (Windows NT 5.1; U; pl) Presto/9.9.9',
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_6; en-US) AppleWebKit/530.5 (KHTML, like Gecko) Chrome/ Safari/530.5',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533.2 (KHTML, like Gecko) Chrome/6.0',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; pl; rv:1.9.1) Gecko/20090624 Firefox/3.5 (.NET CLR 3.5.30729)'
    )
DOOVERWRITE = False
BROWSER = mechanize.Browser()

class DagrException(Exception):
        def __init__(self, value):
                self.parameter = value
        def __str__(self):
                return repr(self.parameter)

def daMakedirs(directory):
        if not os.path.exists(directory):
                os.makedirs(directory)

def daLogin(username,password):
        data = ""
        try:
                BROWSER.open('https://www.deviantart.com/users/login', "ref=http%3A%2F%2Fwww.deviantart.com%2F&remember_me=1")
                BROWSER.select_form(nr=1)
                BROWSER.form['username'] = username
                BROWSER.form['password'] = password
                BROWSER.submit()
                data = BROWSER.response().read()
        except HTTPError, e:
                print "HTTP Error:",e.code
                sys.exit()
        except URLError, e:
                print "URL Error:",e.reason
                sys.exit()
        if re.search("The password you entered was incorrect",data):
                print "Wrong password or username. Attempting to download anyway."
        elif re.search("\"loggedIn\":true",data):
                print "Logged in!"
        else:
                print "Login unsuccessful. Attempting to download anyway."

def get(url, file_name = None):
        if file_name is not None and (DOOVERWRITE == False) and (os.path.exists(file_name)):
                print file_name+" exists - skipping"
                return

        remaining_tries = 3
        while 1:
                try:
                        f = BROWSER.open(url)
                        output = f.read()
                        break
                except HTTPError, e:
                        if verbose:
                                print "HTTP Error: ", e.code , url
                        remaining_tries -= 1
                        if remaining_tries == 0:
                                raise
                except URLError, e:
                        if verbose:
                                print "URL Error: ", e.reason , url
                        remaining_tries -= 1
                        if remaining_tries == 0:
                                raise
                except IncompleteRead:
                        if verbose:
                                print "Incomplete read: ", url
                        remaining_tries -= 1
                        if remaining_tries == 0:
                                raise
        
        if file_name is None:
                return str(output)
        else:
                # Open our local file for writing
                local_file = open(file_name, "wb")
                #Write to our local file
                local_file.write(output)
                local_file.close()

def findLink(link):
        html = get(link)
        # Full image link (via download link)
        try:
                req = BROWSER.click_link(text_regex="Download( (Image|File))?")
                BROWSER.open(req)
                filelink = BROWSER.geturl()
                filename = os.path.basename(filelink)
                return (filename, filelink)
        except mechanize.LinkNotFoundError:
                if verbose:
                        print "Download link not found, falling back to preview image"
                # Fallback 1: try meta
                filesearch = re.search("<meta[^>]*name=\"og:image\"[^>]*content=\"([^\"]*)\"[^>]*>", html, re.DOTALL | re.IGNORECASE)
                if not filesearch:
                        # Fallback 2: try collect_rid, full
                        filesearch = re.search("<img[^>]*collect_rid=\"[^\"]*\"[^>]*src=\"([^\"]*)\"[^>]*class=\"[^\"]*full[^\"]*\"[^>]*>", html, re.DOTALL | re.IGNORECASE)
                if not filesearch:
                        # Fallback 3: try collect_rid, normal
                        filesearch = re.search("<img[^>]*collect_rid=\"[^\"]*\"[^>]*src=\"([^\"]*)\"[^>]*class=\"[^\"]*normal[^\"]*\"[^>]*>", html, re.DOTALL | re.IGNORECASE)

                if filesearch:
                        filelink = filesearch.group(1)
                        if re.search("_by_[A-Za-z0-9-_]+-\w+\.\w+",filelink,re.IGNORECASE) or re.search("_by_[A-Za-z0-9-_]+\.\w+",filelink,re.IGNORECASE):
                                filename = filelink.split("/")[-1].split("?")[0]
                        else:
                                filext = re.search("\.\w+$",filelink).group(0)
                                filename = re.sub("-[0-9]+$","",link.split("/")[-1])+"_by_"+re.search("^http://([A-Za-z0-9-_]+)\.",link).group(1)+filext
                        return (filename,filelink)
                else:
                        raise DagrException("all attemps to find a link failed")

def handle_download_error(link):
        print "Download error (",link,")"
        if verbose:
                traceback.print_exc(file=sys.stdout)
        else:
                print "Use verbose mode to display the error"

def deviantGet(mode,deviant,reverse,testOnly=False):
        print "Ripping "+deviant+"'s "+mode+"..."
        pat = "http://[a-zA-Z0-9_-]*\.deviantart\.com/art/[a-zA-Z0-9_-]*"
        modeArg = '_'
        if mode.find(':') != -1:
                mode = mode.split(':',1)
                modeArg = mode[1]
                mode = mode[0]

        #DEPTH 1
        pages = []
        for i in range(0,MAX/24,24):
                html = ""
                url = ""

                if mode == "favs":
                        url = "http://" + deviant.lower() + ".deviantart.com/favourites/?catpath=/&offset=" + str(i)
                elif mode == "scraps":
                        url = "http://" + deviant.lower() + ".deviantart.com/gallery/?catpath=scraps&offset=" + str(i)
                elif mode == "gallery":
                        url = "http://" + deviant.lower() + ".deviantart.com/gallery/?catpath=/&offset=" + str(i)
                elif mode == "album":
                        url = "http://" + deviant.lower() + ".deviantart.com/gallery/" + modeArg + "?offset=" + str(i)
                elif mode == "query":
                        url = "http://" + deviant.lower() + ".deviantart.com/gallery/?q="+modeArg+"&offset=" + str(i)
                else:
                        continue

                html = get(url)
                prelim = re.findall(pat, html, re.IGNORECASE|re.DOTALL)
                
                c = len(prelim)
                for match in prelim:
                        if match in pages:
                                c -= 1
                        else:
                                pages.append(match)
                
                done = re.findall("(This section has no deviations yet!|This collection has no items yet!)", html, re.IGNORECASE|re.S)
                
                if len(done) >= 1 or c <= 0:
                        break
                
                print deviant+"'s",mode,"page",str((i/24)+1),"crawled..."
                
                        
        if not reverse:
                pages.reverse()

        if len(pages) == 0:
                print deviant+"'s "+mode+" had no deviations."
                return 0
        else:
                try:
                        daMakedirs(deviant+"/"+mode)
                        if (mode == "query") or (mode == "album"):
                            daMakedirs(deviant+"/"+mode+"/"+modeArg)
                except Exception, e:
                        print str(e)
                print "Total deviations in "+deviant+"'s gallery found:",len(pages)
                
        ##DEPTH 2
        counter2 = 0
        for link in pages:
                counter2 += 1
                if verbose:
                        print "Downloading",counter2,"of",len(pages),"( "+link+" )"
                filename = ""
                filelink = ""
                try:
                        filename,filelink = findLink(link)
                except:
                        handle_download_error(link)
                        continue

                if testOnly == False:
                        if (mode == "query") or (mode=="album"):
                                get(filelink,deviant+"/"+mode+"/"+modeArg+"/"+filename)
                        else:
                                get(filelink,deviant+"/"+mode+"/"+filename)
                else:
                        print filelink

        print deviant+"'s gallery successfully ripped."



def groupGet(mode,deviant,reverse,testOnly=False):
        if mode == "favs":
                strmode  = "favby"
                strmode2 = "favourites"
                strmode3 = "favs gallery"
        elif mode == "gallery":
                strmode  = "gallery"
                strmode2 = "gallery"
                strmode3 = "gallery"
        else:
                print "?"
                sys.exit()
        print "Ripping "+deviant+"'s",strmode2+"..."
        
        folders = []

        insideFolder = False
        #are we inside a gallery folder?
        html = get('http://'+deviant+'.deviantart.com/'+strmode2+'/')
        if re.search(strmode2+"/\?set=.+&offset=",html,re.IGNORECASE|re.S):
                insideFolder = True
                folders = re.findall(strmode+":.+ label=\"[^\"]*\"", html, re.IGNORECASE)
        
        #no repeats     
        folders = list(set(folders))
        
        i = 0
        while not insideFolder:
                html = get('http://'+deviant+'.deviantart.com/'+strmode2+'/?offset='+str(i))
                k = re.findall(strmode+":"+deviant+"/\d+\"\ +label=\"[^\"]*\"", html, re.IGNORECASE)
                if k == []:
                        break
                flag = False
                for match in k:
                        if match in folders:
                                flag = True
                        else:
                                folders+=k
                if verbose:
                        print "Gallery page",(i/10)+1,"crawled..."
                if flag:
                        break
                i += 10

        #no repeats
        folders = list(set(folders))

        if len(folders) == 0:
                print deviant+"'s",strmode3,"is empty."
                return 0
        else:
                print "Total folders in "+deviant+"'s",strmode3,"found:",len(folders)
                
        if reverse:
                folders.reverse()


        pat = "http:\\/\\/[a-zA-Z0-9_-]*\.deviantart\.com\\/art\\/[a-zA-Z0-9_-]*"
        pages = []
        for folder in folders:
                try:
                        folderid = re.search("[0-9]+",folder,re.IGNORECASE).group(0)
                        label = re.search("label=\"([^\"]*)",folder,re.IGNORECASE).group(1)
                except:
                        continue
                for i in range(0,MAX/24,24):                    
                        html = get("http://" + deviant.lower() + ".deviantart.com/" + strmode2 + "/?set=" + folderid + "&offset=" + str(i - 24))
                        prelim = re.findall(pat, html, re.IGNORECASE)
                        if not prelim:
                                break
                        for x in prelim:
                                p = str(re.sub(r'\\/','/',x))
                                if p not in pages:
                                        pages.append(p)
                        if verbose:
                                print "Page",(i/24)+1,"in folder",label,"crawled..."

                if not reverse:
                        pages.reverse()
                        
                try:
                        if mode == "favs":
                                daMakedirs(deviant+"/favs/"+label)
                        elif mode == "gallery":
                                daMakedirs(deviant+"/"+label)
                except Exception, err:
                        print err
                counter = 0
                for link in pages:
                        counter += 1
                        if verbose:
                                print "Downloading",counter,"of",len(pages),"( "+link+" )"
                        filename = ""
                        filelink = ""
                        try:
                                filename,filelink = findLink(link)
                        except:
                                handle_download_error(link)
                                continue
                        
                        if testOnly==False:
                                if mode == "favs":
                                        get(filelink, deviant+"/favs/"+label+"/"+filename)
                                elif mode == "gallery":
                                        get(filelink, deviant+"/"+label+"/"+filename)
                        else:
                                print filelink
                        

        print deviant+"'s",strmode3,"successfully ripped."

def printHelp():
        print NAME+" v"+VERSION+" - deviantArt gallery ripper"
        print "Usage: "+NAME+" [-u username] [-p password] [-hfgsv] [deviant]..."
        print "Example: "+NAME+" -u user -p 1234 -gsfv derp123 blah55"
        print "For help use the -h flag, ie. dagr.py -h"

def printHelpDetailed():
        printHelp()
        print "Argument list:"
        print "-u, --username=USERNAME"
        print " your username (account must have \"Show Deviations with Mature Content\" enabled to download mature deviations)"
        print "-p, --password=PASSWORD"
        print " your password (account must have \"Show Deviations with Mature Content\" enabled to download mature deviations)"
        print "-g, --gallery"
        print " downloads entire gallery of selected deviants"
        print "-s, --scraps"
        print " downloads entire scraps gallery of selected deviants"
        print "-f, --favs"
        print " downloads all favourites of selected deviants"
        print "-a, --album=#####"
        print " downloads specified album"
        print "-q, --query"
        print " downloads artwork matching specified query string"
        print "-t, --test"
        print " skips the actual download, just prints urls"
        print "-h, --help"
        print " prints usage message and exits (this text)"
        print "-r, --reverse"
        print " download oldest deviations first"
        print "-o, --overwrite"
        print " redownloads a file even if it already exists"
        print "-x, --proxy=PROXY:PORT"
        print " enables proxy mode (very unreliable)"
        print "-v, --verbose"
        print " outputs detailed information on downloads"

if __name__ == "__main__":
        if len(sys.argv) <= 1:
                printHelp()
                sys.exit()

        #defaults
        username = ""
        password = ""
        proxy = None
        gallery = False
        verbose = False
        reverse = False
        scraps = False
        favs = False
        testOnly = False
        album = False
        albumId = -1
        query = False
        queryS = ""

        try:
                options, deviants = getopt.gnu_getopt(sys.argv[1:], 'u:p:x:a:q:vfgshrto', ['username=', 'password=', 'proxy=','album=', 'query=', 'verbose', 'favs', 'gallery', 'scraps', 'help', 'reverse', 'test', 'overwrite'])
        except getopt.GetoptError, err:
                print "Error:",str(err)
                sys.exit()
        for opt, arg in options:
                if opt in ('-h', '--help'):
                        printHelpDetailed()
                        sys.exit()
                elif opt in ('-u', '--username'):
                        username = arg
                elif opt in ('-p', '--password'):
                        password = arg
                elif opt in ('-x', '--proxy'):
                        proxy = arg
                elif opt in ('-s', '--scraps'):
                        scraps = True
                elif opt in ('-g', '--gallery'):
                        gallery = True
                elif opt in ('-r', '--reverse'):
                        reverse = True
                elif opt in ('-f', '--favs'):
                        favs = True
                elif opt in ('-v', '--verbose'):
                        verbose = True
                elif opt in ('-a', '--album'):
                        album = True
                        albumId = arg.strip()
                elif opt in ('-q', '--query'):
                        query = True
                        queryS = arg.strip().strip('"')
                elif opt in ('-t', '--test'):
                        testOnly = True
                elif opt in ('-o', '--overwrite'):
                        DOOVERWRITE = True
        
        print NAME+" v"+VERSION+" - deviantArt gallery ripper"
        if deviants == []:
                print "No deviants entered. Quitting."
                sys.exit()
        if not gallery and not scraps and not favs and not album and not query:
                print "Nothing to do. Quitting."
                sys.exit()

        # Set up mechanize
        BROWSER.set_handle_redirect(True)
        BROWSER.set_handle_robots(False)
        BROWSER.addheaders = [('Referer', 'http://www.deviantart.com/')]
        BROWSER.addheaders = [('User-Agent', random.choice(USERAGENTS))]

        if username and password:
                print "Attempting to log in to deviantArt..."
                daLogin(username,password)
        else:
                if verbose:
                        print "Mature deviations will not be available for download without logging in!"
        if proxy:
                BROWSER.set_proxies({"http": proxy})

        for deviant in deviants:
                group = False
                try:
                        deviant = re.search(r'<title>.[A-Za-z0-9-]*', get("http://"+deviant+".deviantart.com"),re.IGNORECASE).group(0)[7:]
                        if re.match("#", deviant):
                                group = True
                        deviant = re.sub('[^a-zA-Z0-9_-]+', '', deviant)
                except:
                        print "Deviant",deviant,"not found or deactivated!"
                        continue
                if group:
                        print "Current group:",deviant
                else:
                        print "Current deviant:",deviant
                try:
                        daMakedirs(deviant)
                except Exception, err:
                        print err
                        
                args = (deviant,reverse,testOnly)
                if group:
                        if scraps:
                                print "Groups have no scraps gallery..."
                        if gallery:
                                groupGet("gallery",*args)
                        if favs:
                                groupGet("favs",*args)
                        else:
                                print "Option not supported in groups"
                else:
                        if gallery:
                                deviantGet("gallery",*args)
                        if scraps:
                                deviantGet("scraps",*args)
                        if favs:
                                deviantGet("favs",*args)
                        if album:
                                deviantGet("album:"+albumId,*args)
                        if query:
                                deviantGet("query:"+queryS,*args)
        print "Job complete."

# vim: set tabstop=8 softtabstop=8 shiftwidth=8 expandtab:
