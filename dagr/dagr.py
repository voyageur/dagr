#!/usr/bin/env python
# -*- coding: utf-8 -*-

# deviantArt Gallery Ripper
# http://lovecastle.org/dagr/
# https://github.com/voyageur/dagr

# Copying and distribution of this file, with or without
# modification, is permitted.

# This file is offered as-is, without any warranty.

import json
import re
import sys
from getopt import gnu_getopt, GetoptError
from os import getcwd, makedirs
from os.path import (
    abspath, basename, exists as path_exists,
    expanduser, join as path_join
    )
from random import choice
from requests import (
    adapters as req_adapters,
    codes as req_codes,
    session as req_session
    )
from mechanicalsoup import StatefulBrowser

# Python 2/3 compatibility stuff
try:
    # Python 3
    import configparser
except ImportError:
    # Python 2
    import ConfigParser as configparser
FNF_Error = getattr(__builtins__, 'FileNotFoundError', IOError)


# Helper functions
def da_make_dirs(directory):
    if not path_exists(directory):
        makedirs(directory)


# Main classes
class DagrException(Exception):
    def __init__(self, value):
        super(DagrException, self).__init__(value)
        self.parameter = value

    def __str__(self):
        return str(self.parameter)


class Dagr:
    """deviantArt gallery ripper class"""

    NAME = basename(__file__)
    __version__ = "0.70.1"
    MAX_DEVIATIONS = 1000000  # max deviations
    ART_PATTERN = (r"https://www\.deviantart\.com/"
                   r"[a-zA-Z0-9_-]*/art/[a-zA-Z0-9_-]*")

    def __init__(self):
        # Internals
        self.browser = None
        self.errors_count = dict()

        # Configuration
        self.directory = getcwd() + "/"
        self.mature = False
        self.overwrite = False
        self.reverse = False
        self.test_only = False
        self.verbose = False

        # Current status
        self.deviant = ""

    def load_configuration(self):
        my_conf = configparser.ConfigParser()
        # Try to read global then local configuration
        my_conf.read([expanduser("~/.config/dagr/dagr_settings.ini"),
                      path_join(getcwd(), "dagr_settings.ini")])
        if my_conf.has_option("DeviantArt", "MatureContent"):
            self.mature = my_conf.getboolean("DeviantArt", "MatureContent")
        if my_conf.has_option("Dagr", "OutputDirectory"):
            self.directory = abspath(
                expanduser(my_conf.get("Dagr", "OutputDirectory"))
                ) + "/"

    def start(self):
        if not self.browser:
            # Set up fake browser
            self.set_browser()

    def set_browser(self):
        user_agents = (
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1'
            ' (KHTML, like Gecko) Chrome/14.0.835.202 Safari/535.1',
            'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:7.0.1) Gecko/20100101',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.50'
            ' (KHTML, like Gecko) Version/5.1 Safari/534.50',
            'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)',
            'Opera/9.99 (Windows NT 5.1; U; pl) Presto/9.9.9',
            'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_5_6; en-US)'
            ' AppleWebKit/530.5 (KHTML, like Gecko) Chrome/ Safari/530.5',
            'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533.2'
            ' (KHTML, like Gecko) Chrome/6.0',
            'Mozilla/5.0 (Windows; U; Windows NT 6.1; pl; rv:1.9.1)'
            ' Gecko/20090624 Firefox/3.5 (.NET CLR 3.5.30729)'
        )
        session = req_session()
        session.headers.update({'Referer': 'https://www.deviantart.com/'})
        if self.mature:
            session.cookies.update({'agegate_state': '1'})
        session.mount('https://', req_adapters.HTTPAdapter(max_retries=3))

        self.browser = StatefulBrowser(session=session,
                                       user_agent=choice(user_agents))

    def get(self, url, file_name=None):
        if (file_name and not self.overwrite and
                path_exists(file_name)):
            print(file_name + " exists - skipping")
            return None
        get_resp = self.browser.open(url)

        if get_resp.status_code != req_codes.ok:
            raise DagrException("incorrect status code - " +
                                str(get_resp.status_code))

        if file_name is None:
            return get_resp.text

        # Open our local file for writing
        local_file = open(file_name, "wb")
        # Write to our local file
        local_file.write(get_resp.content)
        local_file.close()
        return file_name

    def find_link(self, link):
        filelink = None
        mature_error = False
        self.browser.open(link)
        # Full image link (via download link)
        link_text = re.compile("Download( (Image|File))?")
        img_link = None
        for candidate in self.browser.links("a"):
            if link_text.search(candidate.text) and candidate.get("href"):
                img_link = candidate
                break

        if img_link:
            self.browser.follow_link(img_link)
            filelink = self.browser.get_url()
            return (basename(filelink), filelink)

        if self.verbose:
            print("Download link not found, falling back to direct image")

        current_page = self.browser.get_current_page()
        # Fallback 1: try meta (filtering blocked meta)
        filesearch = current_page.find("meta", {"property": "og:image"})
        if filesearch:
            filelink = filesearch['content']
            if basename(filelink).startswith("noentrythumb-"):
                filelink = None
                mature_error = True
        if not filelink:
            # Fallback 2: try collect_rid, full
            filesearch = current_page.find("img",
                                           {"collect_rid": True,
                                            "class": re.compile(".*full")})
            if not filesearch:
                # Fallback 3: try collect_rid, normal
                filesearch = current_page.find("img",
                                               {"collect_rid": True,
                                                "class":
                                                    re.compile(".*normal")})
            if filesearch:
                filelink = filesearch['src']

        if not filelink:
            if mature_error:
                if self.mature:
                    raise DagrException("maybe not an image")
                else:
                    raise DagrException("maybe a mature deviation/" +
                                        "not an image")
            else:
                raise DagrException("all attemps to find a link failed")

        filename = basename(filelink)
        return (filename, filelink)

    def handle_download_error(self, link, link_error):
        error_string = str(link_error)
        print("Download error (" + link + ") : " + error_string)
        if error_string in self.errors_count:
            self.errors_count[error_string] += 1
        else:
            self.errors_count[error_string] = 1

    def get_pages(self, mode, base_url):
        pages = []
        for i in range(0, int(Dagr.MAX_DEVIATIONS / 24), 24):
            html = ""
            url = base_url + str(i)

            try:
                html = self.get(url)
            except DagrException:
                print("Could not find " + self.deviant + "'s " + mode)
                return pages

            prelim = re.findall(Dagr.ART_PATTERN, html,
                                re.IGNORECASE | re.DOTALL)

            for match in prelim:
                if match not in pages:
                    pages.append(match)

            done = re.findall("(This section has no deviations yet!|"
                              "This collection has no items yet!)",
                              html, re.IGNORECASE | re.S)

            if done:
                break

            print(self.deviant + "'s " + mode + " page " +
                  str(int((i / 24) + 1)) + " crawled...")

        if not self.reverse:
            pages.reverse()

        return pages

    def get_images(self, mode, mode_arg, pages):
        base_dir = self.directory + self.deviant + "/" + mode
        if mode_arg:
            base_dir += "/" + mode_arg

        try:
            da_make_dirs(base_dir)
        except OSError as mkdir_error:
            print(str(mkdir_error))
            return

        # Find previously downloaded pages
        existing_pages = []
        try:
            with open(base_dir + "/.dagr_downloaded_pages", "r") as filehandle:
                existing_pages = json.load(filehandle)
        except FNF_Error as fnf_error:
            # May not exist (new directory, ...)
            pass
        if not self.overwrite:
            pages = [x for x in pages if x not in existing_pages]

        print("Total deviations to download: " + str(len(pages)))
        for count, link in enumerate(pages, start=1):
            if self.verbose:
                print("Downloading " + str(count) + " of " +
                      str(len(pages)) + " ( " + link + " )")
            filename = ""
            filelink = ""
            try:
                filename, filelink = self.find_link(link)
            except (KeyboardInterrupt, SystemExit):
                raise
            except DagrException as link_error:
                self.handle_download_error(link, link_error)
                continue

            if not self.test_only:
                try:
                    self.get(filelink, base_dir + "/" + filename)
                except DagrException as get_error:
                    self.handle_download_error(link, get_error)
                    continue
                else:
                    if link not in existing_pages:
                        existing_pages.append(link)
            else:
                print(filelink)

        # Update downloaded pages cache
        with open(base_dir + "/.dagr_downloaded_pages", "w") as filehandle:
            json.dump(existing_pages, filehandle)

    def deviant_get(self, mode, mode_arg=None):
        print("Ripping " + self.deviant + "'s " + mode + "...")

        base_url = "https://www.deviantart.com/" + self.deviant.lower() + "/"

        if mode == "favs":
            base_url += "favourites/?catpath=/&offset="
        elif mode == "collection":
            base_url += "favourites/" + mode_arg + "?offset="
        elif mode == "scraps":
            base_url += "gallery/?catpath=scraps&offset="
        elif mode == "gallery":
            base_url += "gallery/?catpath=/&offset="
        elif mode == "album":
            base_url += "gallery/" + mode_arg + "?offset="
        elif mode == "query":
            base_url += "gallery/?q=" + mode_arg + "&offset="

        pages = self.get_pages(mode, base_url)
        if not pages:
            print(self.deviant + "'s " + mode + " had no deviations.")
            return
        print("Total deviations in " + self.deviant + "'s " +
              mode + " found: " + str(len(pages)))

        self.get_images(mode, mode_arg, pages)

        print(self.deviant + "'s " + mode + " successfully ripped.")

    def group_get(self, mode):
        print("Ripping " + self.deviant + "'s " + mode + "...")

        base_url = 'https://www.deviantart.com/' + self.deviant.lower() + '/'
        if mode == "favs":
            base_url += "favourites/"
        elif mode == "gallery":
            base_url += "gallery/"

        folders = []

        i = 0
        while True:
            html = self.get(base_url + '?offset=' + str(i))
            k = re.findall('class="ch-top" href="' + base_url +
                           '([0-9]*/[a-zA-Z0-9_-]*)"',
                           html, re.IGNORECASE)
            if k == []:
                break

            new_folder = False
            for match in k:
                if match not in folders:
                    folders.append(match)
                    new_folder = True
            if not new_folder:
                break
            i += 10

        # no repeats
        folders = list(set(folders))

        if not folders:
            print(self.deviant + "'s " + mode + " is empty.")

        print("Total folders in " + self.deviant + "'s " +
              mode + " found: " + str(len(folders)))

        if self.reverse:
            folders.reverse()

        pages = []
        for folder in folders:
            label = folder.split("/")[-1]
            print("Crawling folder " + label + "...")
            pages = self.get_pages(mode, base_url + folder + '?offset=')

            if not self.reverse:
                pages.reverse()

            self.get_images(mode, label, pages)

        print(self.deviant + "'s " + mode + " successfully ripped.")

    def print_errors(self):
        if self.errors_count:
            print("Download errors count:")
            for error in self.errors_count:
                print("* " + error + " : " + str(self.errors_count[error]))


def print_help():
    print(Dagr.NAME + " v" + Dagr.__version__ + " - deviantArt gallery ripper")
    print("Usage: " + Dagr.NAME +
          " [-d directory] " + "[-fgmhorstv] " +
          "[-q query_text] [-c collection_id/collection_name] " +
          "[-a album_id/album_name] " +
          "deviant1 [deviant2] [...]")
    print("Example: " + Dagr.NAME + " -gsfv derp123 blah55")
    print("For extended help and other options, run " + Dagr.NAME + " -h")


def print_help_detailed():
    print_help()
    print("""
Argument list:
-d, --directory=PATH
directory to save images to, default is current one
-m, --mature
allows to download mature content
-g, --gallery
downloads entire gallery
-s, --scraps
downloads entire scraps gallery
-f, --favs
downloads all favourites
-c, --collection=NUMERIC_ID/NAME
downloads specified favourites collection
 You need to specify both id and name (from the collection URL)
 Example: 123456789/my_favourites
-a, --album=NUMERIC_ID/NAME
downloads specified album
 You need to specify both id and name (from the album URL)
 Example: 123456789/my_first_album
-q, --query=QUERY_TEXT
downloads artwork matching specified query string
-t, --test
skips the actual downloads, just prints URLs
-h, --help
prints help and exits (this text)
-r, --reverse
download oldest deviations first
-o, --overwrite
redownloads a file even if it already exists
-v, --verbose
outputs detailed information on downloads

Proxies:
 you can also configure proxies by setting the environment variables
 HTTP_PROXY and HTTPS_PROXY

$ export HTTP_PROXY="http://10.10.1.10:3128"
$ export HTTPS_PROXY="http://10.10.1.10:1080"
""")


def main():
    gallery = scraps = favs = False
    collection = album = query = ""

    if len(sys.argv) <= 1:
        print_help()
        sys.exit()

    g_opts = "d:mu:p:a:q:c:vfgshrto"
    g_long_opts = ['directory=', 'mature',
                   'album=', 'query=', 'collection=',
                   'verbose', 'favs', 'gallery', 'scraps',
                   'help', 'reverse', 'test', 'overwrite']
    try:
        options, deviants = gnu_getopt(sys.argv[1:], g_opts, g_long_opts)
    except GetoptError as err:
        print("Options error: " + str(err))
        sys.exit()

    ripper = Dagr()
    ripper.load_configuration()

    for opt, arg in options:
        if opt in ('-h', '--help'):
            print_help_detailed()
            sys.exit()
        elif opt in ('-d', '--directory'):
            ripper.directory = abspath(expanduser(arg)) + "/"
        elif opt in ('-m', '--mature'):
            ripper.mature = True
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
            ripper.test_only = True
        elif opt in ('-o', '--overwrite'):
            ripper.overwrite = True

    print(Dagr.NAME + " v" + Dagr.__version__ + " - deviantArt gallery ripper")
    if deviants == []:
        print("No deviants entered. Exiting.")
        sys.exit()
    if not any([gallery, scraps, favs, collection, album, query]):
        print("Nothing to do. Exiting.")
        sys.exit()

    # Only start when needed
    ripper.start()

    for deviant in deviants:
        group = False
        try:
            html = ripper.get('https://www.deviantart.com/' + deviant + '/')
            deviant = re.search(r'<title>.[A-Za-z0-9-]*', html,
                                re.IGNORECASE).group(0)[7:]
            deviant = re.sub('[^a-zA-Z0-9_-]+', '', deviant)
            if re.search('<dt class="f h">Group</dt>', html):
                group = True
        except DagrException:
            print("Deviant " + deviant + " not found or deactivated!")
            continue
        if group:
            print("Current group: " + deviant)
        else:
            print("Current deviant: " + deviant)
        try:
            da_make_dirs(ripper.directory + deviant)
        except OSError as mkdir_error:
            print(str(mkdir_error))

        ripper.deviant = deviant
        if group:
            if gallery:
                ripper.group_get("gallery")
            if favs:
                ripper.group_get("favs")
            if any([scraps, collection, album, query]):
                print("Unsupported modes for groups were ignored")
        else:
            if gallery:
                ripper.deviant_get("gallery")
            if scraps:
                ripper.deviant_get("scraps")
            if favs:
                ripper.deviant_get("favs")
            if collection:
                ripper.deviant_get("collection", mode_arg=collection)
            if album:
                ripper.deviant_get("album", mode_arg=album)
            if query:
                ripper.deviant_get("query", mode_arg=query)
    print("Job complete.")

    ripper.print_errors()


if __name__ == "__main__":
    main()

# vim: set tabstop=4 softtabstop=4 shiftwidth=4 expandtab:
