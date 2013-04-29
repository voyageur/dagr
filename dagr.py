#!/usr/bin/env python
# -*- coding: utf-8 -*-

# deviantArt Gallery Ripper v0.43.1
# http://lovecastle.org/dagr/
# https://github.com/voyageur/dagr

# Copying and distribution of this file, with or without
# modification, is permitted.

# This file is offered as-is, without any warranty.

import random, re, os, sys, hashlib, getopt, urllib2, urllib, cookielib
from urllib2 import Request, urlopen, URLError, HTTPError

MAX = 1000000 #max deviations
VERSION="0.43.1"
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

def daLogin(username,password,proxy=None):
        jar = cookielib.CookieJar()
        handler = urllib2.HTTPCookieProcessor(jar)
        opener = urllib2.build_opener(handler)
        if proxy:
                proxy_handler = urllib2.ProxyHandler({'http': proxy})
                opener.add_handler(proxy_handler)
        urllib2.install_opener(opener)
        opener.addheaders = [('Referer', 'http://www.deviantart.com/')]
        opener.addheaders = [('User-Agent', random.choice(USERAGENTS))]
        data = ""
        try:
                f = opener.open('https://www.deviantart.com/users/login', "ref=http%3A%2F%2Fwww.deviantart.com%2F&username="+username+"&password="+password+"&remember_me=1")
                data = f.read()
                f.close()
        except HTTPError, e:
                print "HTTP Error:",e.code
                sys.exit()
        except URLError, e:
                print "URL Error:",e.reason
                sys.exit()
        if re.search("<title>deviantART\ +:\ +Wrong Password!</title>",data):
                print "Wrong password or username. Attempting to download anyway."
        elif re.search("<title>deviantART:\ +where\ +ART\ +meets\ +application!</title>",data):
                print "Logged in!"
        else:
                print "Login unsuccessful. Attempting to download anyway."
        return jar

def get(url, cookiejar=None, proxy=None):
        if cookiejar:
                handler = urllib2.HTTPCookieProcessor(cookiejar)
                opener = urllib2.build_opener(handler)
        else:
                opener = urllib2.build_opener()
        if proxy:
                proxy_handler = urllib2.ProxyHandler({'http': proxy})
                opener.add_handler(proxy_handler)
        urllib2.install_opener(opener)
        opener.addheaders = [('User-Agent', random.choice(USERAGENTS))]
        try:
                f = opener.open(url)
                return str(f.read())
        except HTTPError, e:
                print "HTTP Error:",e.code , url
        except URLError, e:
                print "URL Error:",e.reason , url

def download(url,file_name,cookiejar=None,proxy=None):
        if (DOOVERWRITE == False) and (os.path.exists(file_name)):
                print file_name+" exists - skipping"
                return
        
        if cookiejar:
                handler = urllib2.HTTPCookieProcessor(cookiejar)
                opener = urllib2.build_opener(handler)
        else:
                opener = urllib2.build_opener()
        if proxy:
                proxy_handler = urllib2.ProxyHandler({'http': proxy})
                opener.add_handler(proxy_handler)
        urllib2.install_opener(opener)
        opener.addheaders = [('User-Agent', random.choice(USERAGENTS))]
        try:
                f = opener.open(url)
                # Open our local file for writing
                local_file = open(file_name, "wb")
                #Write to our local file
                local_file.write(f.read())
                local_file.close()
        except HTTPError, e:
                print "HTTP Error:",e.code , url
        except URLError, e:
                print "URL Error:",e.reason , url
        except IOError, e:
                print e
                sys.exit()

def findLink(link,html):
        if re.search("collect_rid=\"\d*:\d*\" src=\"",html,re.IGNORECASE):
                filelink = re.search("name=\"[^\"]*ResViewSizer_fullimg[^\"]*\"[^>]*src=\"([^\"]*)\"[^>]*class=\"fullview smshadow\">",html,re.DOTALL | re.IGNORECASE).group(1)
        elif re.search("id=\"download-button\"",html,re.IGNORECASE|re.DOTALL):
                filelink = re.search("id=\"download-button\"[^>]*href=\"([^\"]*)\"",html,re.IGNORECASE|re.DOTALL).group(1)
        if re.search("_by_[A-Za-z0-9-_]+-\w+\.\w+",filelink,re.IGNORECASE) or re.search("_by_[A-Za-z0-9-_]+\.\w+",filelink,re.IGNORECASE):
                filename = filelink.split("/")[-1].split("?")[0]
        elif filelink:
                filext = re.search("\.\w+$",filelink).group(0)
                filename = re.sub("-[0-9]+$","",link.split("/")[-1])+"_by_"+re.search("^http://([A-Za-z0-9-_]+)\.",link).group(1)+filext
        return (filename,filelink)

def deviantGet(mode,deviant,verbose,reverse,cookiejar=None,proxy=None,testOnly=False):
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
                try:
                        if mode == "favs":
                                html = get("http://" + deviant.lower() + ".deviantart.com/favourites/?catpath=/&offset=" + str(i), cookiejar, proxy)
                        elif mode == "scraps":
                                html = get("http://" + deviant.lower() + ".deviantart.com/gallery/?catpath=scraps&offset=" + str(i), cookiejar, proxy)
                        elif mode == "gallery":
                                html = get("http://" + deviant.lower() + ".deviantart.com/gallery/?catpath=/&offset=" + str(i), cookiejar, proxy)
                        elif mode == "album":
                                html = get("http://" + deviant.lower() + ".deviantart.com/gallery/" + modeArg + "?offset=" + str(i), cookiejar, proxy)
                        elif mode == "query":
                                print "http://" + deviant.lower() + ".deviantart.com/gallery/?q="+modeArg+"&offset=" + str(i)
                                html = get("http://" + deviant.lower() + ".deviantart.com/gallery/?q="+modeArg+"&offset=" + str(i), cookiejar, proxy)
                        else:
                                continue
                except HTTPError, e:
                        print "HTTP Error:",e.code , url
                        continue
                except URLError, e:
                        print "URL Error:",e.reason , url
                        continue
                except Exception, e:
                        print e
                        continue
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
                        os.makedirs(deviant+"/"+mode)
                        if (mode == "query") or (mode == "album"):
                            os.makedirs(deviant+"/"+mode+"/"+modeArg) 
                except Exception, e:
                        print str(e)
                print "Total deviations in "+deviant+"'s gallery found:",len(pages)
                
        ##DEPTH 2
        counter2 = 0
        for link in pages:
                html = get(link,cookiejar,proxy)
                counter2 += 1
                if verbose:
                        print "Downloading",counter2,"of",len(pages),"( "+link+" )"
                filename = ""
                filelink = ""
                try:
                        filename,filelink = findLink(link,html)
                except:
                        print "Download error. Possible mature deviation? (",link,")"
                        continue

                if testOnly == False:
                        if (mode == "query") or (mode=="album"):
                                download(filelink,deviant+"/"+mode+"/"+modeArg+"/"+filename,proxy)
                        else:
                                download(filelink,deviant+"/"+mode+"/"+filename,proxy)
                else:
                        print filelink

        print deviant+"'s gallery successfully ripped."



def groupGet(mode,deviant,verbose,reverse,cookiejar=None,proxy=None,testOnly=False):
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
        html = get('http://'+deviant+'.deviantart.com/'+strmode2+'/',cookiejar,proxy)
        if re.search(strmode2+"/\?set=.+&offset=",html,re.IGNORECASE|re.S):
                insideFolder = True
                folders = re.findall(strmode+":.+ label=\"[^\"]*\"", html, re.IGNORECASE)
        
        #no repeats     
        folders = list(set(folders))
        
        i = 0
        while not insideFolder:
                html = get('http://'+deviant+'.deviantart.com/'+strmode2+'/?offset='+str(i),cookiejar,proxy)
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
                        html = ""
                        try:
                                html = get("http://" + deviant.lower() + ".deviantart.com/" + strmode2 + "/?set=" + folderid + "&offset=" + str(i - 24), cookiejar, proxy)
                        except (URLError,HTTPError):
                                print Exception
                                continue
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
                                os.makedirs(deviant+"/favs/"+label)
                        elif mode == "gallery":
                                os.makedirs(deviant+"/"+label)
                except Exception, err:
                        print err
                counter = 0
                for link in pages:
                        html = get(link,cookiejar,proxy)
                        counter += 1
                        if verbose:
                                print "Downloading",counter,"of",len(pages),"( "+link+" )"
                        filename = ""
                        filelink = ""
                        try:
                                filename,filelink = findLink(link,html)
                        except:
                                print "Download error. Possible mature deviation? (",link,")"
                                continue
                        
                        if testOnly==False:
                                if mode == "favs":
                                        download(filelink,deviant+"/favs/"+label+"/"+filename,proxy)
                                elif mode == "gallery":
                                        download(filelink,deviant+"/"+label+"/"+filename,proxy)
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

        cookiejar = None
        if username and password:
                print "Attempting to log in to deviantArt..."
                cookiejar = daLogin(username,password,proxy)
        else:
                print "Mature deviations will not be available for download without logging in!"

        for deviant in deviants:
                group = False
                try:
                        deviant = re.search(r'<title>.[A-Za-z0-9-]*', get("http://"+deviant+".deviantart.com",cookiejar,proxy),re.IGNORECASE).group(0)[7:]
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
                        os.makedirs(deviant)
                except Exception, err:
                        print err
                        
                args = (deviant,verbose,reverse,cookiejar,proxy,testOnly)
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
                                deviatGet("album:"+albumId,*args)
                        if query:
                                deviantGet("query:"+queryS,*args)
        print "Job complete."
