from time import sleep

__author__ = 'Shawn Keen'
# -*- coding: utf-8 -*-
from lxml import html
import requests
import sys
from kitchen.text.converters import getwriter
from datetime import datetime
#from bs4 import BeautifulSoup
#import re

UTF8Writer = getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)


class Song:
    def __init__(self, title, artist):
        self.title = title.strip()
        self.artist = artist.strip()

    def __str__(self):
        return self.title.encode("utf-8", "replace").lower() +"\t"+ self.artist.encode("utf-8", "replace").lower()

    # Songs are equal if artist and title are equal
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.artist == other.artist and self.title == other.title


class Station:
    def __init__(self, stationID, url, getter):
        self.stationID = stationID
        self.url = url
        self.getter = getter


def getTag(url, xpathExpression):
    page = requests.get(url)
    tree = html.fromstring(page.text)
    return tree.xpath(xpathExpression)


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
    

def getFM4(url):
    page = requests.get(url)
    tree = html.fromstring(page.text)

    tracktitles = tree.xpath('//span[@class="tracktitle"]/text()')
    trackartists = tree.xpath('//span[@class="artist"]/text()')

    trackartist = trackartists[len(trackartists)-1]
    tracktitle = tracktitles[len(tracktitles)-1]

    return Song(trackartist, tracktitle)


def getSWR3(url):
    result = getFirstNonEmpty(getTag(url, '//a[@rel="x-type:Person"]/text()'), 3)
    return Song(result[1], result[2])


def getAntenneBayern(url):
    result = getTag(url, '//div[@class="left media-info"]/a/text()')
    return Song(result[1], result[0])


def getBayern3(url):
    result = getTag(url, '//li[@class="title"]/span/text()')
    #print result
    if len(result) < 2:
        return None
    return Song(result[0], result[1])


def getDetektorFM(url):
    div = getTag(url, '//div[@class="nowplaying nowplaying-musikstream hide white"]')[0]
    #print div
    artist = div.xpath('//strong/text()')
    title = div.xpath('//span[@id="musicmarquee"]/text()')
    return Song(artist[0], title[0].split("/")[0])


def getByteFM(url):
    song = getTag(url, '///text()')[1].split("-")
    artist = song[0].strip()
    title = song[1].strip()
    if title.lower().strip() == "nachrichten":
        return None
    return Song(artist, title)


def getRadio7(url):
    div = getTag(url, '//div[@class="win-pls-track-rgt"]')[0]
    title = div.xpath('//h1/text()')[1]
    artist = div.xpath('//h2/text()')[1]
    return Song(artist, title)


def getDonau3FM(url):
    element = getTag(url, '//div[@id="playlistContent"]//td/text()')
    artist = element[2]
    title = element[1]
    return Song(artist, title)

#print sys.stdout.encoding


def printPlaying(stations, lastsongs):
    for station in stations:
        fun = stations[station][0]
        url = stations[station][1]
        try:
            song = fun(url)
            if song == None:
                continue
            if station in lastsongs and lastsongs[station] == song:
                continue
            lastsongs[station] = song
            print datetime.utcnow().isoformat(" ") +"\t"+ station +"\t"+ str(song)
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write('ERROR while fetching from '+station+"\n")
            sys.stderr.write(str(e))


stations = {'FM4': (getFM4, 'http://hop.orf.at/img-trackservice/fm4.html'),
            'SWR3': (getSWR3, 'http://www.swr3.de/musik/playlisten/Die-letzten-13-Titel-auf-SWR3/-/id=47424/did=202234/1wuwzys/index.html'),
            'Antenne Bayern': (getAntenneBayern, 'http://www.antenne.de/musik/song-suche.html'),
            'Bayern3': (getBayern3, 'http://www.br.de/radio/bayern3/welle108.html'),
            'detektor.fm': (getDetektorFM, 'http://detektor.fm/'),
            'byte.fm': (getByteFM, 'http://byte.fm/php/content/home/new.php'),
            'Radio7': (getRadio7, 'http://radio7.de/content/html/shared/playlist/index.html'),
            'Donau3FM': (getDonau3FM, 'http://www.donau3fm.de/programm/playlist')}

if len(sys.argv) > 1:
    delay = int(sys.argv[1])
else:
    delay = 60

#print getDonau3FM('http://www.donau3fm.de/programm/playlist')

lastsongs = {}
while True:
    printPlaying(stations, lastsongs)
    sleep(delay)