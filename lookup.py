__author__ = 'skeen'
import pylast
import sys

KEY_FILE_NAME = "lastfm.keyinfo"

keyfile = open(KEY_FILE_NAME)

apiKey = keyfile.readline().strip()
apiSecret = keyfile.readline().strip()

# print apiKey
#print apiSecret

keyfile.close()

network = pylast.LastFMNetwork(api_key=apiKey, api_secret=apiSecret)

artist = network.get_artist(sys.argv[1])

#track = network.get_track("rag bone man", "disfigured")

try:
    # print artist.get_similar()
    print artist.get_name(True)
except pylast.WSError as err:
    print err
    # print artist.get_name(True)