import json
import math
import os
from pprint import pprint
import sys
import urllib
from decouple import config
import requests

API_KEY = config("API_KEY")
ARTISTS_LIMIT = 100
CACHE_DIR = ".cache"
FRIENDS_BASE_URL = "http://ws.audioscrobbler.com/2.0/?method=user.getfriends&user={lastfm_username}&api_key={api_key}&format=json&recenttracks=0&page={page}"
LASTFM_USERNAME = config("LASTFM_USERNAME")
TAG_THRESHOLD = 10000
TOP_ARTISTS_BASE_URL = "http://ws.audioscrobbler.com/2.0/?method=user.gettopartists&user={lastfm_username}&api_key={api_key}&format=json&limit={artists_limit}"
TOP_TAGS_BASE_URL = "http://ws.audioscrobbler.com/2.0/?method=artist.gettoptags&artist={artist}&api_key={api_key}&format=json"


def compare_taste(toptags1, toptags2):
    numerator = 0
    tags = set(toptags1.keys())
    tags.update(toptags2.keys())
    for tag in tags:
        numerator += toptags1.get(tag, 0) * toptags2.get(tag, 0)
    denominator = sum((toptags1.get(tag, 0) ** 2 for tag in tags)) + \
        sum((toptags2.get(tag, 0) ** 2 for tag in tags))
    angle = math.degrees(math.acos(numerator / denominator))
    print("angle is {angle:.2f}°.".format(angle=angle))
    return angle


def encodeURIComponent(input_str, quotate=urllib.parse.quote):
    """
    Python equivalent of javascript's encodeURIComponent
    """
    return quotate(input_str.encode('utf-8'), safe='~()*!.\'')


def get_artist_name(artist_payload):
    artist_name = artist_payload["name"]
    # print(artist_name)
    return artist_name


def get_artist_playcount(artist_payload):
    return int(artist_payload["playcount"])


def get_artists_playcount(lastfm_username):
    response = requests.get(TOP_ARTISTS_BASE_URL.format(
        api_key=API_KEY, artists_limit=ARTISTS_LIMIT, lastfm_username=lastfm_username))
    data = json.loads(response.text)
    return {get_artist_name(artist_payload): get_artist_playcount(artist_payload) for artist_payload in data["topartists"]["artist"]}


def get_tag_count(artist_tag_payload):
    return int(artist_tag_payload["count"])


def get_tag_name(artist_tag_payload):
    return artist_tag_payload["name"]


def get_user_friends_usernames(lastfm_username):
    page = 0
    while True:
        page += 1
        response = requests.get(FRIENDS_BASE_URL.format(
            lastfm_username=lastfm_username, api_key=API_KEY, page=page))
        data = json.loads(response.text)
        if not len(data["friends"]["user"]):
            break
        for friend in data["friends"]["user"]:
            yield friend["name"]


def get_user_toptags(lastfm_username):
    print("Acquiring {lastfm_username}'s top tags...".format(
        lastfm_username=lastfm_username))
    cache_filename = os.path.join(CACHE_DIR, lastfm_username + ".json")
    if os.path.isfile(cache_filename):
        with open(cache_filename) as cache_file:
            return json.load(cache_file)
    else:
        topartists = get_artists_playcount(lastfm_username)
        # pprint(topartists)
        toptags = {}
        for artist in topartists:
            try:
                response = requests.get(TOP_TAGS_BASE_URL.format(
                    artist=encodeURIComponent(artist), api_key=API_KEY))
                data = json.loads(response.text)
                for tag in data["toptags"]["tag"]:
                    tag_name = get_tag_name(tag)
                    toptags[tag_name] = toptags.get(
                        tag_name, 0) + get_tag_count(tag) * topartists[artist]
            except Exception:
                print("Artist {artist} make us sick.".format(artist=artist))
        # data = toptags
        data = {key: toptags[key]
                for key in toptags if toptags[key] > TAG_THRESHOLD}
        with open(cache_filename, 'w') as cache_file:
            json.dump(data, cache_file)
        return data


# toptags1 = get_user_toptags(sys.argv[1])
# toptags2 = get_user_toptags(sys.argv[2])
# print("comparing...")
# print(compare_taste(toptags1, toptags2))

toptags = get_user_toptags(LASTFM_USERNAME)
comparations = []
print("Fetching {lastfm_username}'s friends...".format(
    lastfm_username=LASTFM_USERNAME))
for friend_username in get_user_friends_usernames(LASTFM_USERNAME):
    friend_toptags = get_user_toptags(friend_username)
    print("Comparing {user1} and {user2}...".format(
        user1=LASTFM_USERNAME, user2=friend_username))
    comparations.append(
        (friend_username, compare_taste(toptags, friend_toptags)))
comparations.sort(key=lambda comparation: comparation[1])
pprint(comparations)
