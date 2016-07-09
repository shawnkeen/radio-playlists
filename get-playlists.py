# -*- coding: utf-8 -*-
from time import sleep
from lxml import html
import requests
import sys
import json
import string
from kitchen.text.converters import getwriter
from datetime import datetime
# from bs4 import BeautifulSoup
# import re

__author__ = 'Shawn Keen'

UTF8Writer = getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)


class Song:
    """
    A song consists of a title and an artist.
    """
    def __init__(self, title, artist):
        """
        :param title: the song's title as string
        :param artist: the song's artist as string
        """
        self.title = title.strip()
        self.artist = artist.strip()

    def __str__(self):
        """
        Return artist and title as lowercase, utf-8 encoded, and separated by a
        TAB (\t).
        """
        return self.title.encode("utf-8", "replace").lower() + \
            "\t" + self.artist.encode("utf-8", "replace").lower()

    def __eq__(self, other):
        """
        Songs are qual if both artist and title are equal.
        """
        if isinstance(other, self.__class__):
            return self.artist == other.artist and self.title == other.title


# class Station:
# def __init__(self, stationID, url, getter):
#         self.stationID = stationID
#         self.url = url
#         self.getter = getter


def get_tag(url, xpathExpression, params=None):
    """
    Get the tag entry described by a given xpath expression after fetching
    from a url.

    :param url: string with url
    :param xpathExpression: an xpath expression as string
    :param params: optional parameters for requests.get()
    :return: a string containing entries found using the xpath expression
    """
    headers = {'User-Agent': 'curl/7.35.0'}
    page = requests.get(url, params=params, headers=headers)
    tree = html.fromstring(page.content)
    return tree.xpath(xpathExpression)


def get_multiple_tags(url, xpathExpressionList, params=None):
    """
    Perform one query on the given url, but extract multiple entries using
    several xpath expressions.

    :param url: URL to fetch from
    :param xpathExpressionList: a list of xpath expressions
    :param params: optional parameters for the http retrieval from the URL
    :return: a list of entries, one for each xpath expression
    """
    page = requests.get(url, params=params)
    tree = html.fromstring(page.text)
    out = []
    for expression in xpathExpressionList:
        out.append(tree.xpath(expression))
    return out


# cheap tag remover
def remove_tags(text):
    """
    Remove the tags from a html input.
    :param text: A string containing html formatted text.
    :return: A string without surrounding tags.
    """
    tree = html.fromstring(text)
    return tree.xpath("//text()")


def get_first_non_empty(inputList, num):
    """
    Get the first non-empty items in a list of strings.

    :param inputList: A list of possibly empty strings.
    :param num: The number of items to get at most.
    :return: A list of non-empty strings or an empty list, if no non-empty
        strings were found.
    """
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


def scrape_fm4():
    """
    Fetch the currently playing song for FM4.

    :return: A Song, if scraping went whithout error. Return None otherwise.
    """
    url = 'http://hop.orf.at/img-trackservice/fm4.html'
    page = requests.get(url)
    tree = html.fromstring(page.text)

    tracktitles = tree.xpath('//span[@class="tracktitle"]/text()')
    trackartists = tree.xpath('//span[@class="artist"]/text()')

    if trackartists and tracktitles:
        trackartist = trackartists[-1]
        tracktitle = tracktitles[-1]
        return Song(trackartist, tracktitle)
    sys.stderr.write(
        "ERROR in fm4: " +
        str(tracktitles) +
        " " +
        str(trackartists)+"\n")
    return None


def scrape_swr3():
    """
    Fetch the currently playing song for SWR3.

    :return: A Song, if scraping went whithout error. Return None otherwise.
    """
    url = 'http://www.swr3.de/musik/playlisten'
    # The artist is encapsulated either in a <strong> or <a>,
    # the title is the trailing rest of the same <li>.
    # We try both versions for the artist. First is the <strong>.
    # If this fails, the first list is empty.
    tags = get_multiple_tags(url, ['//ul[@id="nowplaying"]/li/strong/text()',
                                   '//ul[@id="nowplaying"]/li/a/text()',
                                   '//ul[@id="nowplaying"]/li/text()'])
    if tags[0]:
        artistRaw = tags[0]
    else:
        artistRaw = tags[1]
    titleRaw = tags[2]
    if artistRaw and len(artistRaw) > 0 and titleRaw and len(titleRaw) > 1:
        artist = artistRaw[0]
        title = titleRaw[1]
        return Song(artist, title)
    sys.stderr.write("ERROR in swr3: "+str(artistRaw)+" "+str(titleRaw)+"\n")
    return None


def scrape_antenne_bayern():
    """
    Fetch the currently playing song for Antenne Bayern.

    :return: A Song, if scraping went whithout error. Return None otherwise.
    """
    url = 'http://www.antenne.de/musik/song-suche.html'
    result = get_multiple_tags(url, ['//p[@class="artist"]/a/text()',
                                     '//h2[@class="song_title"]/a/text()'])
    artistRaw = result[0]
    titleRaw = result[1]
    artist = None
    title = None
    if artistRaw:
        artist = artistRaw[0]
    if titleRaw:
        title = titleRaw[0]
    if artist and title:
        return Song(artist, title)
    return None


def scrape_bayern3():
    """
    Fetch the currently playing song for Bayern3.

    :return: A Song, if scraping went whithout error. Return None otherwise.
    """
    # The page is a query form, showing the last couple of songs.
    # The last one is the most recent.
    url = 'https://www.br.de'
    '/radio/bayern-3/bayern-3-playlist-musiktitel-recherche-100.html'

    result = get_tag(url, '//li[@class="title"]/span/text()')
    if len(result) < 2:
        return None
    return Song(result[-2], result[-1])


def scrape_detektor_fm():
    """
    Fetch the currently playing song for Detektor FM.

    :return: A Song, if scraping went whithout error. Return None otherwise.
    """
    url = 'http://detektor.fm/'
    div = get_multiple_tags(
        url, ['//div[@class="nowplaying nowplaying-musikstream hide white"]'
              '/strong/text()',
              '//div[@class="nowplaying nowplaying-musikstream hide white"]'
              '/span/text()'])

    if len(div) >= 2 \
            and isinstance(div[0], list) \
            and isinstance(div[1], list) \
            and div[0] \
            and len(div[1]) >= 2:
        artist = div[0][0]
        title = div[1][1]
        if '/' in title:
            title = title.split('/')[0]
        return Song(artist, title)

    sys.stderr.write("ERROR in detektor.fm: "+str(div)+"\n")
    return None


def scrape_byte_fm():
    """
    Fetch the currently playing song for ByteFM.

    :return: A Song, if scraping went whithout error. Return None otherwise.
    """
    url = 'https://byte.fm/ajax/song-history'
    jsonpage = requests.get(url)
    # get json
    song = json.loads(jsonpage.text)['tracks'][0]
    # replace separator, if present
    song = string.replace(song, "&ndash;", "-")
    # extract from possible html tag and split on separator
    song = remove_tags(song)[0].split("-")
    if not song or len(song) < 2:
        sys.stderr.write("ERROR in byteFM: "+str(song)+"\n")
        return None
    artist = song[0].strip()
    title = song[1].strip()
    if title.lower().strip() == "nachrichten":
        return None
    return Song(artist, title)


def scrape_radio7():
    """
    Fetch the currently playing song for Radio7.

    :return: A Song, if scraping went whithout error. Return None otherwise.
    """
    url = 'http://radio7.de/content/html/shared/playlist/index.html'
    div = get_tag(url, '//div[@class="win-pls-track-rgt"]')[0]
    title = div.xpath('//h1/text()')[1]
    artist = div.xpath('//h2/text()')[1]
    return Song(artist, title)


def scrape_donau_3_fm():
    """
    Fetch the currently playing song for Donau3 FM.

    :return: A Song, if scraping went whithout error. Return None otherwise.
    """
    date = datetime.now()

    url = 'http://www.donau3fm.de/'
    'wp-content/themes/ex-studios-2015/playlist/getplaylist.php'

    params = {'pl_time_m': str(date.minute)}
    element = get_tag(url=url,
                      params=params,
                      xpathExpression='//table//td/text()')
    artist = None
    title = None
    if len(element) >= 3:
        artist = element[2]
        title = element[1]
    if artist and title:
        return Song(artist, title)
    return None


def scrape_fritz():
    """
    Fetch the currently playing song for Fritz.de radio.

    :return: A Song, if scraping went without error. Return None otherwise.
    """
    url = 'http://www.fritz.de/musik/playlists/index.html'
    tag = get_tag(url, '//table[@class="playlist_aktueller_tag"]')
    if tag:
        tag = tag[0]
    else:
        return None
    title = tag.xpath('.//td[@class="tracktitle"]/text()')
    artist = tag.xpath('.//td[@class="trackinterpret"]/a/text()')
    if artist and title:
        return Song(artist[-1], title[-1])
    return None


def scrape_radio_koeln():
    """
    Fetch the currently playing song for Radio Köln.

    :return: A Song, if scraping went without error. Return None otherwise.
    """
    url = 'http://www.radiokoeln.de/'
    tag = get_tag(url, '//div[@id="playlist_title"]')[0]
    artist = tag.xpath('.//div/b/text()')
    title = tag.xpath('.//div/text()')
    tmp = title
    title = []
    for item in tmp:
        s = item.strip()
        if s:
            title.append(s)
    if artist and title:
        artist = artist[0]
        title = title[-1]
        return Song(artist, title)
    # else
    sys.stderr.write("ERROR in radiokoeln: "+str(artist)+" "+str(title)+"\n")
    return None


def scrape_1live():
    """
    Fetch the currently playing song for 1Live.

    :return: A Song, if scraping went without error. Return None otherwise.
    """
    url = 'http://www.einslive.de/einslive/musik/playlist/playlist284.html'
    tag = get_tag(url, '//div[@class="playlist"]')[0]
    artist = tag.xpath('.//td/strong/text()')
    title = tag.xpath('.//td/text()')
    if artist and title:
        return Song(artist[0], title[0])
    return None


def print_playing_songs(stations, lastsongs):
    """
    tag = get_tag(url, '//div[@class="playlist"]')[0]
    artist = tag.xpath('.//td/strong/text()')
    title = tag.xpath('.//td/text()')
    if artist and title:
        return Song(artist[0], title[0])
    return None

    Iterate over all stations and use the associated scrape function to get
    the currently played song. The song is only printed if it does not
    appear in the lastsongs dictionary under that station.

    :param stations: dictionary station name -> scrape function
    :param lastsongs: dictionary station name -> last played song
    :return: None
    """
    for station in stations:
        fun = stations[station]
        try:
            song = fun()
            if song is None:
                continue
            if station in lastsongs and lastsongs[station] == song:
                continue
            lastsongs[station] = song
            print datetime.utcnow().isoformat(" ") + "\t" + \
                station + "\t" + \
                str(song)
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write('ERROR while fetching from ' + station + ": ")
            sys.stderr.flush()
            sys.stderr.write(str(e)+"\n")
            sys.stderr.flush()


def main():

    stations = {'FM4': scrape_fm4,
                'SWR3': scrape_swr3,
                'Antenne Bayern': scrape_antenne_bayern,
                'Bayern3': scrape_bayern3,
                'detektor.fm': scrape_detektor_fm,
                'byte.fm': scrape_byte_fm,
                'Radio7': scrape_radio7,
                'Donau3FM': scrape_donau_3_fm,
                'Fritz': scrape_fritz,
                'RadioKoeln': scrape_radio_koeln,
                '1Live': scrape_1live}

    delay = 60
    lastsongs = {}

    if len(sys.argv) > 1 and sys.argv[1] in stations:
        fun = stations[sys.argv[1]]
        song = fun()
        print str(song)
    else:
        while True:
            print_playing_songs(stations, lastsongs)
            sleep(delay)


if __name__ == "__main__":
    main()
