__author__ = 'skeen'
import pylast

KEY_FILE_NAME = "lastfm.keyinfo"

keyfile = open(KEY_FILE_NAME)

apiKey = keyfile.readline().strip()
apiSecret = keyfile.readline().strip()

print apiKey
print apiSecret

keyfile.close()

network = pylast.LastFMNetwork(api_key = apiKey, api_secret=apiSecret)

artist = network.get_artist("cosmo sheldrake ft. anndreyah vargas")

track = network.get_track("rag bone man", "disfigured")

try:
    print track.get_artist().get_name(True), track.get_name(True)
except pylast.WSError as err:
    print err
#print artist.get_name(True)