###  dagr.py
dagr.py (deviantArt gallery ripper) is a deviantArt image downloader script written in Python.
It can download every image (deviation) in a gallery, as well as every favorited deviation a deviant may have.
Originally developed at http://lovecastle.org/dagr/ (now defunct), development now continues on Github

### Dependencies
* a working Python installation (2.x or 3.x)
* MechanicalSoup module (https://github.com/MechanicalSoup/MechanicalSoup), and its dependencies

### Installation
dagr is available on PyPI and has setuptools support.

So to install latest released version, you can just run:
```
# pip install dagr
```

To install from checked out source:
```
# python setup.py install
```

### Gentoo package
dagr is available in the voyageur overlay (https://cafarelli.fr/cgi-bin/cgit.cgi/voyageur-overlay/).
You can install it with layman:
```
# layman -a voyageur
# emerge dagr
```

### Current bugs and limitations
These should be tracked here: https://github.com/voyageur/dagr/issues

### Configuration file
Some parameters can be set in a configuration file, the script will look for it in these locations:
* ~/.config/dagr/dagr_settings.ini
* ./dagr_settings.ini

You can copy and adapt the provided [sample file](dagr_settings.ini.sample), also available after installation in /usr/share/dagr

###  Usage
Here's an example of how to use the script:

```
$ python dagr.py
dagr.py v0.63 - deviantArt gallery ripper
Usage: dagr.py [-d directory] [-fgmhorstv] [-q query_text] [-c collection_id/collection_name] [-a album_id/album_name] deviant1 [deviant2] [...]
Example: dagr.py -gsfv derp123 blah55
For extended help and other options, run dagr.py -h

$ python dagr.py -gs doo22
dagr.py v0.63 - deviantArt gallery ripper
Current deviant: doo22
Ripping doo22's gallery...
```

### FAQ
- Will I be banned from deviantArt if I use dagr.py?
Not likely. However, dagr.py could be blocked at any time. If you want to be sure your main account isn't banned, use a disposable account and a proxy.

- The deviantArt page says a deviant has 145 deviations but the program can only find 139!
Sometimes deviantArt reports the wrong number of deviations in a gallery. This is because you can submit deviations exclusively to a group without having it show up in your gallery.

- Why can I not download mature deviations?
You need to enable the mature content download option, either in the configuration file or via the "-m" command line flag
