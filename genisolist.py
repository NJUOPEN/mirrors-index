#!/usr/bin/env python2

import os
import re
import glob
import json
import urlparse
from distutils.version import LooseVersion
from ConfigParser import ConfigParser

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'genisolist.ini')

def getPlatformPriority (platform):
    platform = platform.lower()
    if platform in ['amd64', 'x86_64', '64bit']:
        return 100
    elif platform in ['i386', 'i486', 'i586', 'i686', 'x86', '32bit']:
        return 90
    else:
        return 0

def parseSection(items):
    items = dict(items)

    if 'location' in items:
        locations = [items['location']]
    else:
        locations = []
        i = 0
        while ("location_%d" % i) in items:
            locations.append(items["location_%d" % i])
            i += 1

    pattern = items.get("pattern", "")
    prog = re.compile(pattern) 

    images = []
    for location in locations:
        for imagepath in glob.glob(location):
            result = prog.search(imagepath)
            if not(result):
                continue

            group_count = len(result.groups()) + 1
            imageinfo = {"filepath": imagepath, "distro": items["distro"]}

            for prop in ("version", "type", "platform"):
                s = items.get(prop, "")
                for i in xrange(0, group_count):
                    s = s.replace("$%d" % i, result.group(i))
                imageinfo[prop] = s

            images.append(imageinfo)

    images.sort(key = lambda k: ( LooseVersion(k['version']),
                                  getPlatformPriority(k['platform']),
                                  k['type'] ),
                reverse=True)

    i = 0
    versions = set()
    listvers = int(items.get('listvers', 0xFF))
    for image in images:
        versions.add(image['version'])
        if len(versions) <= listvers: 
            yield image
        else:
            break

def getDescriptionAndURL (image_info, urlbase):
    url = urlparse.urljoin(urlbase, image_info['filepath'])
    desc = "%s (%s%s)" % (
            image_info['version'],
            image_info['platform'],
            ", %s" % image_info['type'] if image_info['type'] else ''
    )
    return (desc, url)

def getJsonOutput(url_dict, prio = {}):
    raw = []
    for distro in url_dict:
        raw.append({
            "distro": distro,
            "urls": [{"name": l[0], "url": l[1]} \
                         for l in url_dict[distro]]
        })

    raw.sort(key = lambda d: prio.get(d["distro"], 0xFFFF))

    return json.dumps(raw)


def getImageList ():
    ini = ConfigParser()
    if not(ini.read(CONFIG_FILE)):
        raise Exception("%s not found!" % CONFIG_FILE)

    root = ini.get("%main%", 'root')
    urlbase = ini.get("%main%", 'urlbase')

    prior = {}
    for (name, value) in ini.items("%main%"):
        if re.match("d\d+$", name):
            prior[value] = int(name[1:])

    oldcwd = os.getcwd()
    os.chdir(root)
    
    url_dict = {}
    for section in ini.sections():
        if section != "%main%":
            for image in parseSection(ini.items(section)):
                if not image['distro'] in url_dict:
                    url_dict[image['distro']] = []

                url_dict[image['distro']].append(
                        getDescriptionAndURL(image, urlbase)
                )

    os.chdir(oldcwd)

    return getJsonOutput(url_dict, prior)

if __name__ == "__main__":
    print(getImageList())
