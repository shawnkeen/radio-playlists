from time import sleep

__author__ = 'Shawn Keen'
# -*- coding: utf-8 -*-
from lxml import html
import requests
import sys
import json
import string
from kitchen.text.converters import getwriter
from datetime import datetime
# from bs4 import BeautifulSoup
# import re


UTF8Writer = getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)


class Song:
    def __init__(self, title, artist):
        self.title = title.strip()
        self.artist = artist.strip()

    def __str__(self):
        return self.title.encode("utf-8", "replace").lower() + "\t" + self.artist.encode("utf-8", "replace").lower()

    # Songs are equal if artist and title are equal
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.artist == other.artist and self.title == other.title


class Station:
    def __init__(self, stationID, url, getter):
        self.stationID = stationID
        self.url = url
        self.getter = getter


def getTag(url, xpathExpression, params=None):
    headers = {'User-Agent': 'curl/7.35.0'}
    page = requests.get(url, params=params, headers=headers)
    #print page.text
    tree = html.fromstring(page.text)
    return tree.xpath(xpathExpression)


def getMultipleTags(url, xpathExpressionList, params=None):
    page = requests.get(url, params=params)
    tree = html.fromstring(page.text)
    out = []
    for expression in xpathExpressionList:
        out.append(tree.xpath(expression))
    return out


# cheap tag remover
def deTag(text):
    tree = html.fromstring(text)
    return tree.xpath("//text()")


def getFirstNonEmpty(inputList, num):
    i = num
    outputList = []
    for item in inputList:
        if item.strip() == '':
            continue
        outputList.append(item.strip())
        i -= 1
        if i <= 0:
            break
    return outputList


def getFM4():
    url = 'http://hop.orf.at/img-trackservice/fm4.html'
    page = requests.get(url)
    tree = html.fromstring(page.text)

    tracktitles = tree.xpath('//span[@class="tracktitle"]/text()')
    trackartists = tree.xpath('//span[@class="artist"]/text()')

    trackartist = trackartists[-1]
    tracktitle = tracktitles[-1]

    return Song(trackartist, tracktitle)


def getSWR3():
    url = 'http://www.swr3.de/musik/playlisten'
    tags = getMultipleTags(url, ['//ul[@id="nowplaying"]/li/strong/text()', '//ul[@id="nowplaying"]/li/text()'])
    #print tags
    artistRaw = tags[0]
    titleRaw = tags[1]
    artist = None
    title = None
    if artistRaw and len(artistRaw) > 0:
        artist = artistRaw[0]
    if titleRaw and len(titleRaw) > 1:
        title = titleRaw[1]
    if artist and title:
        return Song(artist, title)
    else:
        return None


def getAntenneBayern():
    url = 'http://www.antenne.de/musik/song-suche.html'
    result = getMultipleTags(url, ['//p[@class="artist"]/a/text()', '//h2[@class="song_title"]/a/text()'])
    artistRaw = result[0]
    titleRaw = result[1]
    artist = None
    title = None
    if artistRaw:
        artist = artistRaw[0]
    if titleRaw:
        title = titleRaw[0]
    #print title
    #print artist
    if artist and title:
        return Song(artist, title)
    return None


def getBayern3():
    ## The page is a query form, showing the last couple of songs. The last one is the most recent.
    url = 'https://www.br.de/radio/bayern-3/bayern-3-playlist-musiktitel-recherche-100.html'
    result = getTag(url, '//li[@class="title"]/span/text()')
    #print result
    if len(result) < 2:
        return None
    return Song(result[-2], result[-1])


def getDetektorFM():
    url = 'http://detektor.fm/'
    div = getMultipleTags(url, ['//div[@class="nowplaying nowplaying-musikstream hide white"]/strong/text()',
                                '//div[@class="nowplaying nowplaying-musikstream hide white"]/span/text()'])
    #print div
    artist = div[0][0]
    title = div[1][1]
    #print artist, title
    return Song(artist, title)


def getByteFM():
    url = 'https://byte.fm/ajax/song-history'
    jsonpage = requests.get(url)
    # get json
    song = json.loads(jsonpage.text)['tracks'][0]
    # replace separator, if present
    song = string.replace(song, "&ndash;", "-")
    # extract from possible html tag and split on separator
    song = deTag(song)[0].split("-")
    artist = song[0].strip()
    title = song[1].strip()
    if title.lower().strip() == "nachrichten":
        return None
    return Song(artist, title)


def getRadio7():
    url = 'http://radio7.de/content/html/shared/playlist/index.html'
    div = getTag(url, '//div[@class="win-pls-track-rgt"]')[0]
    title = div.xpath('//h1/text()')[1]
    artist = div.xpath('//h2/text()')[1]
    return Song(artist, title)


def getDonau3FM():
    #url = 'http://www.donau3fm.de/programm/playlist'
    date = datetime.now()
    url = 'http://www.donau3fm.de/wp-content/themes/ex-studios-2015/playlist/getplaylist.php'
    params = {'pl_time_m': str(date.minute)}
    element = getTag(url=url, params=params, xpathExpression='//table//td/text()')
    #print element
    artist = None
    title = None
    if len(element) >= 3:
        artist = element[2]
        title = element[1]
    if artist and title:
        return Song(artist, title)
    return None


#print sys.stdout.encoding


def printPlaying(stations, lastsongs):
    for station in stations:
        fun = stations[station]
        try:
            song = fun()
            if song is None:
                continue
            if station in lastsongs and lastsongs[station] == song:
                continue
            lastsongs[station] = song
            print datetime.utcnow().isoformat(" ") + "\t" + station + "\t" + str(song)
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write('ERROR while fetching from ' + station + "\n")
            sys.stderr.write(str(e))


def main():

    stations = {'FM4': getFM4,
                'SWR3': getSWR3,
                'Antenne Bayern': getAntenneBayern,
                'Bayern3': getBayern3,
                'detektor.fm': getDetektorFM,
                'byte.fm': getByteFM,
                'Radio7': getRadio7,
                'Donau3FM': getDonau3FM}

    delay = 60
    lastsongs = {}

    if len(sys.argv) > 1 and sys.argv[1] in stations:
        fun = stations[sys.argv[1]]
        song = fun()
        print str(song)
        #delay = int(sys.argv[1])
    else:
        while True:
            printPlaying(stations, lastsongs)
            sleep(delay)


if __name__ == "__main__":
    main()