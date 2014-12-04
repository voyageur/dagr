#!/usr/bin/env python
# -*- coding: utf-8 -*-

# deviantArt Gallery Ripper
# http://lovecastle.org/dagr/
# https://github.com/voyageur/dagr

# Copying and distribution of this file, with or without
# modification, is permitted.

# This file is offered as-is, without any warranty.

import getopt, random, re, sys
from os import makedirs
from os.path import basename, exists as path_exists

from robobrowser import RoboBrowser
from requests import session as req_session

class DagrException(Exception):
        def __init__(self, value):
                self.parameter = value
        def __str__(self):
                return str(self.parameter)

MAX = 1000000 # max deviations
VERSION="0.60"
NAME = basename(__file__)
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

def daMakedirs(directory):
        if not path_exists(directory):
                makedirs(directory)

def daSetBrowser():
        global BROWSER
        session = req_session()
        session.headers.update({'Referer': 'http://www.deviantart.com/'})

        BROWSER = RoboBrowser(history=False, session=session, tries=3, user_agent=random.choice(USERAGENTS))

def daLogin(username,password):
        BROWSER.open('https://www.deviantart.com/users/login?ref=http%3A%2F%2Fwww.deviantart.com%2F&remember_me=1')
        form = BROWSER.get_forms()[1]
        form['username'] = username
        form['password'] = password
        BROWSER.submit_form(form)

        if BROWSER.find(text=re.compile("The password you entered was incorrect")):
                print("Wrong password or username. Attempting to download anyway.")
        elif BROWSER.find(text=re.compile("\"loggedIn\":true")):
                print("Logged in!")
        else:
                print("Login unsuccessful. Attempting to download anyway.")

def daGet(url, file_name = None):
        if file_name is not None and (overwrite == False) and (path_exists(file_name)):
                print(file_name + " exists - skipping")
                return
        #TODO Test robobrowser retries and exceptions
        BROWSER.open(url)

        if file_name is None:
                return str(BROWSER.parsed)
        else:
                # Open our local file for writing
                local_file = open(file_name, "wb")
                #Write to our local file
                local_file.write(BROWSER.response.content)
                local_file.close()

def findLink(link):
        filelink = None
        mature_error = False
        BROWSER.open(link)
        # Full image link (via download link)
        img_link = BROWSER.get_link(text=re.compile("Download( (Image|File))?"))
        if img_link and img_link.get("href"):
                BROWSER.follow_link(img_link)
                filelink = BROWSER.url
        else:
                if verbose:
                        print("Download link not found, falling back to direct image")
                # Fallback 1: try meta (filtering blocked meta)
                filesearch = BROWSER.find("meta", {"name":"og:image"})
                if filesearch:
                        filelink = filesearch['content']
                        if basename(filelink).startswith("noentrythumb-"):
                                filelink = None
                                mature_error = True
                if not filelink:
                        # Fallback 2: try collect_rid, full
                        filesearch = BROWSER.find("img", {"collect_rid":True, "class":re.compile(".*full")})
                        if not filesearch:
                        # Fallback 3: try collect_rid, normal
                                filesearch = BROWSER.find("img", {"collect_rid":True, "class":re.compile(".*normal")})
                        if filesearch:
                                filelink = filesearch['src']

                if not filelink:
                        if mature_error:
                                raise DagrException("probably a mature deviation")
                        else:
                                raise DagrException("all attemps to find a link failed")

        filename = basename(filelink)
        return (filename, filelink)

def handle_download_error(link, e):
        print("Download error (" + link + ") : " + str(e))

def deviantGet(mode,deviant,reverse,testOnly=False):
        print("Ripping " + deviant + "'s " + mode + "...")
        pat = "http://[a-zA-Z0-9_-]*\.deviantart\.com/art/[a-zA-Z0-9_-]*"
        modeArg = '_'
        if mode.find(':') != -1:
                mode = mode.split(':',1)
                modeArg = mode[1]
                mode = mode[0]

        #DEPTH 1
        pages = []
        for i in range(0,int(MAX/24),24):
                html = ""
                url = ""

                if mode == "favs":
                        url = "http://" + deviant.lower() + ".deviantart.com/favourites/?catpath=/&offset=" + str(i)
                elif mode == "collection":
                        url = "http://" + deviant.lower() + ".deviantart.com/favourites/" + modeArg + "?offset=" + str(i)
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

                html = daGet(url)
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

                print(deviant + "'s " +  mode + " page " + str(int((i/24)+1)) + " crawled...")


        if not reverse:
                pages.reverse()

        if len(pages) == 0:
                print(deviant + "'s " + mode + " had no deviations.")
                return 0
        else:
                try:
                        daMakedirs(deviant+"/"+mode)
                        if (mode == "query") or (mode == "album") or (mode == "collection"):
                            daMakedirs(deviant + "/" + mode + "/" + modeArg)
                except Exception as e:
                        print(str(e))
                print("Total deviations in " + deviant + "'s gallery found: " + str(len(pages)))

        ##DEPTH 2
        counter2 = 0
        for link in pages:
                counter2 += 1
                if verbose:
                        print("Downloading " + str(counter2) + " of " + str(len(pages)) + " ( " + link + " )")
                filename = ""
                filelink = ""
                try:
                        filename,filelink = findLink(link)
                except (KeyboardInterrupt, SystemExit):
                        raise
                except Exception as e:
                        handle_download_error(link, e)
                        continue

                if testOnly == False:
                        if (mode == "query") or (mode=="album") or (mode == "collection"):
                                daGet(filelink,deviant+"/"+mode+"/"+modeArg+"/"+filename)
                        else:
                                daGet(filelink,deviant+"/"+mode+"/"+filename)
                else:
                        print(filelink)

        print(deviant + "'s gallery successfully ripped.")



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
                print("?")
                sys.exit()
        print("Ripping " + deviant + "'s " + strmode2 + "...")

        folders = []

        insideFolder = False
        #are we inside a gallery folder?
        html = daGet('http://'+deviant+'.deviantart.com/'+strmode2+'/')
        if re.search(strmode2+"/\?set=.+&offset=",html,re.IGNORECASE|re.S):
                insideFolder = True
                folders = re.findall(strmode+":.+ label=\"[^\"]*\"", html, re.IGNORECASE)

        #no repeats
        folders = list(set(folders))

        i = 0
        while not insideFolder:
                html = daGet('http://'+deviant+'.deviantart.com/'+strmode2+'/?offset='+str(i))
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
                        print("Gallery page " + str(int((i/10) + 1)) + " crawled...")
                if flag:
                        break
                i += 10

        #no repeats
        folders = list(set(folders))

        if len(folders) == 0:
                print(deviant + "'s " +  strmode3 + " is empty.")
                return 0
        else:
                print("Total folders in " + deviant + "'s " + strmode3 + " found: " + str(len(folders)))

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
                for i in range(0,int(MAX/24),24):
                        html = daGet("http://" + deviant.lower() + ".deviantart.com/" + strmode2 + "/?set=" + folderid + "&offset=" + str(i - 24))
                        prelim = re.findall(pat, html, re.IGNORECASE)
                        if not prelim:
                                break
                        for x in prelim:
                                p = str(re.sub(r'\\/','/',x))
                                if p not in pages:
                                        pages.append(p)
                        if verbose:
                                print("Page " + str(int((i/24) + 1)) + " in folder " + label + " crawled...")

                if not reverse:
                        pages.reverse()

                try:
                        if mode == "favs":
                                daMakedirs(deviant+"/favs/"+label)
                        elif mode == "gallery":
                                daMakedirs(deviant+"/"+label)
                except Exception as err:
                        print(err)
                counter = 0
                for link in pages:
                        counter += 1
                        if verbose:
                                print("Downloading " +  str(counter) +  " of " + str(len(pages)) +  " ( " + link + " )")
                        filename = ""
                        filelink = ""
                        try:
                                filename,filelink = findLink(link)
                        except (KeyboardInterrupt, SystemExit):
                                raise
                        except Exception as e:
                                handle_download_error(link, e)
                                continue

                        if testOnly==False:
                                if mode == "favs":
                                        daGet(filelink, deviant+"/favs/"+label+"/"+filename)
                                elif mode == "gallery":
                                        daGet(filelink, deviant+"/"+label+"/"+filename)
                        else:
                                print(filelink)


        print(deviant + "'s " + strmode3 + " successfully ripped.")

def printHelp():
        print(NAME + " v" + VERSION + " - deviantArt gallery ripper")
        print("Usage: " + NAME + " [-u username] [-p password] [-acfghoqrstv] [deviant]...")
        print("Example: " + NAME + " -u user -p 1234 -gsfv derp123 blah55")
        print("For extended help and other options, run " + NAME + " -h")

def printHelpDetailed():
        printHelp()
        print("""
Argument list:
-u, --username=USERNAME
 your deviantArt account username
-p, --password=PASSWORD
 your deviantArt account password
-g, --gallery
 downloads entire gallery of selected deviants
-s, --scraps
 downloads entire scraps gallery of selected deviants
-f, --favs
 downloads all favourites of selected deviants
-c, --collection=#####
 downloads all artwork from given favourites collection of selected deviants
-a, --album=#####
 downloads specified album
-q, --query=#####
 downloads artwork matching specified query string
-t, --test
 skips the actual download, just prints urls
-h, --help
 prints usage message and exits (this text)
-r, --reverse
 download oldest deviations first
-o, --overwrite
 redownloads a file even if it already exists
-v, --verbose
 outputs detailed information on downloads

Mature deviations:
 to download mature deviations you must specify your deviantArt account, with \"Show Deviations with Mature Content\" option enabled

Proxys:
 you can also configure proxies by setting the environment variables HTTP_PROXY and HTTPS_PROXY

 $ export HTTP_PROXY="http://10.10.1.10:3128"
 $ export HTTPS_PROXY="http://10.10.1.10:1080"
""")

if __name__ == "__main__":
        if len(sys.argv) <= 1:
                printHelp()
                sys.exit()

        #defaults
        BROWSER = None
        username = ""
        password = ""
        gallery = False
        verbose = False
        overwrite = False
        reverse = False
        scraps = False
        favs = False
        collection = False
        collectionS = ""
        testOnly = False
        album = False
        albumId = -1
        query = False
        queryS = ""

        try:
                options, deviants = getopt.gnu_getopt(sys.argv[1:], 'u:p:x:a:q:c:vfgshrtob', ['username=', 'password=', 'album=', 'query=', 'collection=', 'verbose', 'favs', 'gallery', 'scraps', 'help', 'reverse', 'test', 'overwrite'])
        except getopt.GetoptError as err:
                print("Options error: " + str(err))
                sys.exit()
        for opt, arg in options:
                if opt in ('-h', '--help'):
                        printHelpDetailed()
                        sys.exit()
                elif opt in ('-u', '--username'):
                        username = arg
                elif opt in ('-p', '--password'):
                        password = arg
                elif opt in ('-s', '--scraps'):
                        scraps = True
                elif opt in ('-g', '--gallery'):
                        gallery = True
                elif opt in ('-r', '--reverse'):
                        reverse = True
                elif opt in ('-f', '--favs'):
                        favs = True
                elif opt in ('-c', '--collection'):
                        collection = True
                        collectionS = arg.strip().strip('"')
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
                        overwrite = True

        print(NAME + " v" + VERSION + " - deviantArt gallery ripper")
        if deviants == []:
                print("No deviants entered. Quitting.")
                sys.exit()
        if not gallery and not scraps and not favs and not collection and not album and not query:
                print("Nothing to do. Quitting.")
                sys.exit()

        # Set up fake browser
        daSetBrowser()

        if username and password:
                print("Attempting to log in to deviantArt...")
                daLogin(username,password)

        for deviant in deviants:
                group = False
                try:
                        deviant = re.search(r'<title>.[A-Za-z0-9-]*', daGet("http://"+deviant+".deviantart.com"),re.IGNORECASE).group(0)[7:]
                        if re.match("#", deviant):
                                group = True
                        deviant = re.sub('[^a-zA-Z0-9_-]+', '', deviant)
                except:
                        print("Deviant " + deviant + "not found or deactivated!")
                        continue
                if group:
                        print("Current group: " + deviant)
                else:
                        print("Current deviant: " + deviant)
                try:
                        daMakedirs(deviant)
                except Exception as err:
                        print(err)

                args = (deviant,reverse,testOnly)
                if group:
                        if scraps:
                                print("Groups have no scraps gallery...")
                        if gallery:
                                groupGet("gallery",*args)
                        if favs:
                                groupGet("favs",*args)
                        else:
                                print("Option not supported in groups")
                else:
                        if gallery:
                                deviantGet("gallery",*args)
                        if scraps:
                                deviantGet("scraps",*args)
                        if favs:
                                deviantGet("favs",*args)
                        if collection:
                                deviantGet("collection:"+collectionS,*args)
                        if album:
                                deviantGet("album:"+albumId,*args)
                        if query:
                                deviantGet("query:"+queryS,*args)
        print("Job complete.")

# vim: set tabstop=8 softtabstop=8 shiftwidth=8 expandtab:
