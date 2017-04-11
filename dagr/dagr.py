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

# Helper functions
def da_make_dirs(directory):
    if not path_exists(directory):
        makedirs(directory)

# Main classes
class DagrException(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return str(self.parameter)
class Dagr:
    """deviantArt gallery ripper class"""

    NAME = basename(__file__)
    __version__="0.61"
    MAX_DEVIATIONS = 1000000 # max deviations

        def __init__(self):
                # Internals
                self.browser = None
                self.errors_count = dict()

                # Configuration
                self.username = ""
                self.password = ""
                self.overwrite = False
                self.reverse = False
                self.testOnly = False
                self.verbose = False

                # Current status
                self.deviant = ""

        def start(self):
                if not self.browser:
                        # Set up fake browser
                        self.set_browser()
                # Always run login
                self.login()

        def set_browser(self):
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
                session = req_session()
                session.headers.update({'Referer': 'http://www.deviantart.com/'})

                # Try to use lxml parser if available
                # https://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser
                try:
                        import lxml
                        parser = "lxml"
                except ImportError:
                        parser = "html.parser"

                self.browser = RoboBrowser(history=False, session=session, tries=3, user_agent=random.choice(USERAGENTS), parser=parser)

        def login(self):
                if not (self.username and self.password):
                        return
                print("Attempting to log in to deviantArt...")
                self.browser.open('https://www.deviantart.com/users/login?ref=http%3A%2F%2Fwww.deviantart.com%2F&remember_me=1')
                form = self.browser.get_forms()[1]
                form['username'] = self.username
                form['password'] = self.password
                self.browser.submit_form(form)

                if self.browser.find(text=re.compile("The password you entered was incorrect")):
                        print("Wrong password or username. Attempting to download anyway.")
                elif self.browser.find(text=re.compile("\"loggedIn\":true")):
                        print("Logged in!")
                else:
                        print("Login unsuccessful. Attempting to download anyway.")

        def get(self, url, file_name = None):
                if file_name is not None and (self.overwrite == False) and (path_exists(file_name)):
                        print(file_name + " exists - skipping")
                        return
                #TODO Test robobrowser retries and exceptions
                self.browser.open(url)

                if file_name is None:
                        return str(self.browser.parsed)
                else:
                    raise DagrException("all attemps to find a link failed")

        filename = basename(filelink)
        return (filename, filelink)

    def handle_download_error(self, link, e):
        error_string = str(e)
        print("Download error (" + link + ") : " + error_string)
        if error_string in self.errors_count:
            self.errors_count[error_string] += 1
        else:
            self.errors_count[error_string] = 1

    def deviant_get(self, mode):
        print("Ripping " + self.deviant + "'s " + mode + "...")
        pat = "http://[a-zA-Z0-9_-]*\.deviantart\.com/art/[a-zA-Z0-9_-]*"
        modeArg = '_'
        if mode.find(':') != -1:
            mode = mode.split(':',1)
            modeArg = mode[1]
            mode = mode[0]

        #DEPTH 1
        pages = []
        for i in range(0,int(Dagr.MAX_DEVIATIONS/24),24):
            html = ""
            url = ""

            if mode == "favs":
                url = "http://" + self.deviant.lower() + ".deviantart.com/favourites/?catpath=/&offset=" + str(i)
            elif mode == "collection":
                url = "http://" + self.deviant.lower() + ".deviantart.com/favourites/" + modeArg + "?offset=" + str(i)
            elif mode == "scraps":
                url = "http://" + self.deviant.lower() + ".deviantart.com/gallery/?catpath=scraps&offset=" + str(i)
            elif mode == "gallery":
                url = "http://" + self.deviant.lower() + ".deviantart.com/gallery/?catpath=/&offset=" + str(i)
            elif mode == "album":
                url = "http://" + self.deviant.lower() + ".deviantart.com/gallery/" + modeArg + "?offset=" + str(i)
            elif mode == "query":
                url = "http://" + self.deviant.lower() + ".deviantart.com/gallery/?q=" + modeArg + "&offset=" + str(i)
            else:
                continue

            html = self.get(url)
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

            print(self.deviant + "'s " +  mode + " page " + str(int((i/24)+1)) + " crawled...")

        if not self.reverse:
            pages.reverse()

        if len(pages) == 0:
            print(self.deviant + "'s " + mode + " had no deviations.")
            return 0
        else:
            try:
                da_make_dirs(self.deviant + "/" + mode)
                if (mode == "query") or (mode == "album") or (mode == "collection"):
                    da_make_dirs(self.deviant + "/" + mode + "/" + modeArg)
            except Exception as e:
                print(str(e))
            print("Total deviations in " + self.deviant + "'s gallery found: " + str(len(pages)))

        ##DEPTH 2
        counter2 = 0
        for link in pages:
            counter2 += 1
            if self.verbose:
                print("Downloading " + str(counter2) + " of " + str(len(pages)) + " ( " + link + " )")
            filename = ""
            filelink = ""
            try:
                filename,filelink = self.find_link(link)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                self.handle_download_error(link, e)
                continue

            if self.testOnly == False:
                if (mode == "query") or (mode=="album") or (mode == "collection"):
                    self.get(filelink, self.deviant + "/" + mode + "/" + modeArg + "/" + filename)
                else:
                    self.get(filelink, self.deviant + "/" + mode + "/" + filename)
            else:
                print(filelink)

        print(self.deviant + "'s gallery successfully ripped.")

    def group_get(self, mode):
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
        print("Ripping " + self.deviant + "'s " + strmode2 + "...")

        folders = []

        insideFolder = False
        #are we inside a gallery folder?
        html = self.get('http://' + self.deviant + '.deviantart.com/' + strmode2 + '/')
        if re.search(strmode2 + "/\?set=.+&offset=", html, re.IGNORECASE|re.S):
            insideFolder = True
            folders = re.findall(strmode + ":.+ label=\"[^\"]*\"", html, re.IGNORECASE)

        #no repeats
        folders = list(set(folders))

        i = 0
        while not insideFolder:
            html = self.get('http://' + self.deviant + '.deviantart.com/' + strmode2 + '/?offset=' + str(i))
            k = re.findall(strmode + ":" + self.deviant + "/\d+\"\ +label=\"[^\"]*\"", html, re.IGNORECASE)
            if k == []:
                break
            flag = False
            for match in k:
                if match in folders:
                    flag = True
                else:
                    folders+=k
            if self.verbose:
                print("Gallery page " + str(int((i/10) + 1)) + " crawled...")
            if flag:
                break
            i += 10

        #no repeats
        folders = list(set(folders))

        if len(folders) == 0:
            print(self.deviant + "'s " +  strmode3 + " is empty.")
            return 0
        else:
            print("Total folders in " + self.deviant + "'s " + strmode3 + " found: " + str(len(folders)))

        if self.reverse:
            folders.reverse()

        pat = "http:\\/\\/[a-zA-Z0-9_-]*\.deviantart\.com\\/art\\/[a-zA-Z0-9_-]*"
        pages = []
        for folder in folders:
            try:
                folderid = re.search("[0-9]+",folder,re.IGNORECASE).group(0)
                label = re.search("label=\"([^\"]*)",folder,re.IGNORECASE).group(1)
            except:
                continue
            for i in range(0,int(Dagr.MAX_DEVIATIONS/24),24):
                html = self.get("http://" + self.deviant.lower() + ".deviantart.com/" + strmode2 + "/?set=" + folderid + "&offset=" + str(i - 24))
                prelim = re.findall(pat, html, re.IGNORECASE)
                if not prelim:
                    break
                for x in prelim:
                    p = str(re.sub(r'\\/','/',x))
                    if p not in pages:
                        pages.append(p)
                if self.verbose:
                    print("Page " + str(int((i/24) + 1)) + " in folder " + label + " crawled...")

            if not self.reverse:
                pages.reverse()

            try:
                if mode == "favs":
                    da_make_dirs(self.deviant + "/favs/" + label)
                elif mode == "gallery":
                    da_make_dirs(self.deviant + "/" + label)
            except Exception as err:
                print(err)
            counter = 0
            for link in pages:
                counter += 1
                if self.verbose:
                    print("Downloading " +  str(counter) +  " of " + str(len(pages)) +  " ( " + link + " )")
                filename = ""
                filelink = ""
                try:
                    filename,filelink = self.find_link(link)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as e:
                    self.handle_download_error(link, e)
                    continue

                if self.testOnly == False:
                    if mode == "favs":
                        self.get(filelink, self.devianti + "/favs/" + label + "/" + filename)
                    elif mode == "gallery":
                        self.get(filelink, self.deviant + "/" + label + "/" + filename)
                else:
                    print(filelink)

        print(self.deviant + "'s " + strmode3 + " successfully ripped.")

    def print_errors(self):
        if len(self.errors_count):
            print("Download errors count:")
            for error in self.errors_count:
                print("* " + error + " : " + str(self.errors_count[error]))

def print_help():
    print(Dagr.NAME + " v" + Dagr.__version__ + " - deviantArt gallery ripper")
    print("Usage: " + Dagr.NAME + " [-u username] [-p password] [-acfghoqrstv] [deviant]...")
    print("Example: " + Dagr.NAME + " -u user -p 1234 -gsfv derp123 blah55")
    print("For extended help and other options, run " + Dagr.NAME + " -h")

def print_help_detailed():
    print_help()
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

def main():
    gallery = scraps = favs = False
    collection = album = query = ""

    if len(sys.argv) <= 1:
        print_help()
        sys.exit()

    try:
        options, deviants = getopt.gnu_getopt(sys.argv[1:], 'u:p:a:q:c:vfgshrto', ['username=', 'password=', 'album=', 'query=', 'collection=', 'verbose', 'favs', 'gallery', 'scraps', 'help', 'reverse', 'test', 'overwrite'])
    except getopt.GetoptError as err:
        print("Options error: " + str(err))
        sys.exit()

    ripper = Dagr()

    for opt, arg in options:
        if opt in ('-h', '--help'):
            print_help_detailed()
            sys.exit()
        elif opt in ('-u', '--username'):
            ripper.username = arg
        elif opt in ('-p', '--password'):
            ripper.password = arg
        elif opt in ('-s', '--scraps'):
            scraps = True
        elif opt in ('-g', '--gallery'):
            gallery = True
        elif opt in ('-r', '--reverse'):
            ripper.reverse = True
        elif opt in ('-f', '--favs'):
            favs = True
        elif opt in ('-c', '--collection'):
            collection = arg.strip().strip('"')
        elif opt in ('-v', '--verbose'):
            ripper.verbose = True
        elif opt in ('-a', '--album'):
            album = arg.strip()
        elif opt in ('-q', '--query'):
            query = arg.strip().strip('"')
        elif opt in ('-t', '--test'):
            ripper.testOnly = True
        elif opt in ('-o', '--overwrite'):
            ripper.overwrite = True

    print(Dagr.NAME + " v" + Dagr.__version__ + " - deviantArt gallery ripper")
    if deviants == []:
        print("No deviants entered. Quitting.")
        sys.exit()
    if not gallery and not scraps and not favs and not collection and not album and not query:
        print("Nothing to do. Quitting.")
        sys.exit()

    # Only start when needed
    ripper.start()

    for deviant in deviants:
        group = False
        try:
            deviant = re.search(r'<title>.[A-Za-z0-9-]*', ripper.get("http://" + deviant + ".deviantart.com"),re.IGNORECASE).group(0)[7:]
            if re.match("#", deviant):
                group = True
            deviant = re.sub('[^a-zA-Z0-9_-]+', '', deviant)
        except:
            print("Deviant " + deviant + " not found or deactivated!")
            continue
        if group:
            print("Current group: " + deviant)
        else:
            print("Current deviant: " + deviant)
        try:
            da_make_dirs(deviant)
        except Exception as err:
            print(err)

        ripper.deviant = deviant
        if group:
            if scraps:
                print("Groups have no scraps gallery...")
            if gallery:
                ripper.group_get("gallery")
            if favs:
                ripper.group_get("favs")
            else:
                print("Option not supported in groups")
        else:
            if gallery:
                ripper.deviant_get("gallery")
            if scraps:
                ripper.deviant_get("scraps")
            if favs:
                ripper.deviant_get("favs")
            if collection:
                ripper.deviant_get("collection:" + collection)
            if album:
                ripper.deviant_get("album:" + album)
            if query:
                ripper.deviant_get("query:" + query)
    print("Job complete.")

    ripper.print_errors()

if __name__ == "__main__":
    main()

# vim: set tabstop=4 softtabstop=4 shiftwidth=4 expandtab:
