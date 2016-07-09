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


def get_tag(url, xpathExpression, params=None):
    """
    Get the tag entry described by a given xpath expression after fetching
    from a url.

    :param url: string with url
    :param xpathExpression: an xpath expression as string
    :param params: optional parameters for requests.get()
    :return: a string containing entries found using the xpath expression
    :raises: requests.exceptions.HTTPError, if one occured
    """
    headers = {'User-Agent': 'curl/7.35.0'}
    page = requests.get(url, params=params, headers=headers)
    page.raise_for_status()
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
    :raises: requests.exceptions.HTTPError, if one occured
    """
    headers = {'User-Agent': 'curl/7.35.0'}
    page = requests.get(url, params=params, headers=headers)
    page.raise_for_status()
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
    url = 'https://www.br.de' \
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
    # The landing page shows the currently played songs for both channels
    # "Wort" and "Musik". We pinpoint the "Musik" part. The artist is printed
    # in a <strong> and the title is encapsulated in a span.
    url = 'https://detektor.fm'
    div = get_multiple_tags(
        url, ['//div[@class="nowplaying nowplaying-musikstream hide white"]'
              '/strong/text()',
              '//div[@class="nowplaying nowplaying-musikstream hide white"]'
              '/span[@id="musicmarquee"]/text()'])

    if len(div) >= 2 \
            and isinstance(div[0], list) \
            and isinstance(div[1], list) \
            and div[0] \
            and div[1]:
        artist = div[0][0]
        title = div[1][0]
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

    url = 'http://www.donau3fm.de/' \
        'wp-content/themes/ex-studios-2015/playlist/getplaylist.php'

    element = get_tag(url=url,
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

    # The page contains a table of recently played songs, with the first row
    # being the most recent. Every <td class="entry"> is either artist or
    # title. We extract the first two entries as artist and title.
    url = 'http://www1.wdr.de/radio/1live/musik/1live-playlist/index.html'
    tag = get_tag(
        url,
        '//table[@summary="WDR3 - Playliste"]//td[@class="entry"]/text()')
    if not tag and not isinstance(tag, list):
        sys.stderr.write("ERROR in 1live:" + str(tag) + "\n")
        return
    artist = tag[0].strip()
    title = tag[1].strip()
    if artist and title:
        return Song(artist, title)
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
                sys.stderr.write("ERROR while fetching from " + station +
                                 ": empty response\n")
                sys.stderr.flush()
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

    # We use dotted notation here to make it easier for R to import the
    # station names as factors.
    stations = {'fm4': scrape_fm4,
                'swr3': scrape_swr3,
                'antenne.bayern': scrape_antenne_bayern,
                'bayern3': scrape_bayern3,
                'detektor.fm': scrape_detektor_fm,
                'byte.fm': scrape_byte_fm,
                'radio7': scrape_radio7,
                'donau3fm': scrape_donau_3_fm,
                'fritz': scrape_fritz,
                'radio.koeln': scrape_radio_koeln,
                '1live': scrape_1live}

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
