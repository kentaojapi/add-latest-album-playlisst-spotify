import os


import spotipy
import spotipy.util as util
import slackweb
from spotipy.oauth2 import SpotifyOAuth
import boto3


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('SpotifyToken')


class SpotifyToken(object):
    def __init__(self, proxies=None, state=None):
        self.username = os.environ['USERNAME']
        self.client_id = os.environ['CLIENT_ID']
        self.client_secret = os.environ['CLIENT_SECRET']
        self.redirect_uri = ''
        self.state = state
        self.proxies = proxies
        self.playlist_id = os.environ['PLAYLIST_ID']
        self.slack_channel_uri = os.environ['SLACK_CHANNEL_URI']
        self.scope = 'playlist-modify-public'


def add_tracks(sp, username, playlist_id, slack_channel_uri, search_word):
    name = search_word
    # serch by artist name
    try:
        result = sp.search(q='artist:' + name, type='artist')
        # get the artist_id
        artist_id = result['artists']['items'][0]['id']
        # get the latest album of the artist
        albums = sp.artist_albums(artist_id)
        most_latest_album = albums['items'][0]['id']
        # get uris of album trucks by list
        album_trucks = sp.album_tracks(most_latest_album)
        # album name
        album_name = albums['items'][0]['name']
        # artist_name
        artist_name = albums['items'][0]['artists'][0]['name']
        # URL of image of the album
        image = albums['items'][0]['images'][1]['url']
        # release_date
        release_date = albums['items'][0]['release_date']
        track_uris =[]
        for i in range(len(album_trucks['items'])):
            track_id = album_trucks['items'][i]['uri']
            track_uris.append(track_id)
        # add uris of trucks to playlist"NewRelease"
        sp.user_playlist_add_tracks(username, playlist_id, track_uris)
        # post image,album name to slck channel
        _success_slackpost(slack_channel_uri, album_name, artist_name, image, release_date)
    except:
        _failed_slackpost(slack_channel_uri)


def _failed_slackpost(slack_channel_uri):
    """
    If the artist was not finded, this fucntion posts to Error Message to the Slack channel.
    """
    slack = slackweb.Slack(url=slack_channel_uri)
    slack.notify(text="Can't find it.")


def _success_slackpost(slack_channel_uri, album_name, artist_name, image, release_date):
    slack = slackweb.Slack(url=slack_channel_uri)
    slack.notify(text='{}(release:{}) / {}'.format(album_name, release_date, artist_name))
    slack.notify(text=image)


def get_new_access_token(oauth):
    pre_token = _load_dynamodb()
    refresh_token = pre_token
    new_token = oauth.refresh_access_token(refresh_token)
    _update_dynamodb(new_token)
    access_token = new_token['access_token']
    return access_token


def _load_dynamodb():
    response = table.scan()
    pre_token = response['Items'][0]['refresh_token']
    return pre_token


def _update_dynamodb(new_token):
    table.put_item(
        Item={
            'token':'key',
            'access_token': new_token['access_token'],
            'token_type': new_token['token_type'],
            'expires_in': new_token['expires_in'],
            'scope': new_token['scope'],
            'expires_at': new_token['expires_at'],
            'refresh_token': new_token['refresh_token']
        })


def lambda_handler(event, context):
    user = SpotifyToken()
    oauth = SpotifyOAuth(client_id=user.client_id, client_secret=user.client_secret,
    redirect_uri=None)
    access_token = get_new_access_token(oauth)
    sp = spotipy.Spotify(auth=access_token)
    sp.trace = False
    search_word = event['text']
    add_tracks(sp, user.username, user.playlist_id, user.slack_channel_uri, search_word)
