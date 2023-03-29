# this script will ping listenbrainz for a user's now playing song and set it as a discord rich resence

import os
import time
from enum import Enum

import musicbrainzngs
import pylistenbrainz
import requests
from dotenv import load_dotenv
from pypresence import Presence

load_dotenv()

DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
LISTENBRAINZ_USER = os.environ.get('LISTENBRAINZ_USER')
MB_APP_NAME = os.environ.get('MB_APP_NAME')
MB_APP_VERSION = os.environ.get('MB_APP_VERSION')
MB_CONTACT = os.environ.get('MB_CONTACT')

now_playing = None

# NOT_PLAYING: user is not not listening
# PLAYING: user is listening; now playing has NOT changed since last status update
# UPDATE: user is listening; now playing has changed since last status update (unused, just send new status)
Status = Enum('Status', ['NOT_PLAYING', 'PLAYING', 'UPDATE'])


def get_status():
    global now_playing

    client = pylistenbrainz.ListenBrainz()
    listen = client.get_playing_now(LISTENBRAINZ_USER)

    if listen is None and now_playing is None:
        return Status.NOT_PLAYING

    np = f"{f'{listen.track_name[:128]}'} | {f'{listen.artist_name} - {listen.release_name}'[:128]}"
    if np == now_playing:
        return Status.PLAYING
    now_playing = np

    musicbrainzngs.set_useragent(MB_APP_NAME, MB_APP_VERSION, MB_CONTACT)

    release_info = musicbrainzngs.get_release_by_id(
        listen.release_mbid, includes=['release-groups'])
    release_group_id = release_info['release']['release-group']['id']

    # get album art
    album_art = 'navidrome'
    try:
        result = musicbrainzngs.get_release_group_image_list(release_group_id)
    except requests.exceptions.HTTPError as e:
        # handle HTTP errors
        print(f'HTTP error occurred: {e}')
    except musicbrainzngs.ResponseError as e:
        if e.status_code == 400:  # Invalid release group ID
            print('Invalid release_group_id')
        elif e.status_code == 404:  # Release not found
            print('Release not found')
        elif e.status_code == 503:  # Rate limit exceeded
            print('Rate limit exceeded')
        else:
            print('Unknown error')
            exit(1)
        # handle MusicBrainz API errors
        print(f'MusicBrainz API error occurred: {e}')
        print(f'On release: {listen.artist_name} - {listen.release_name}')
    else:
        # success
        images = result['images']
        image = None
        for img in images:
            if 'Front' in img['types']:
                image = img
                break
        if image is not None:
            album_art = img['thumbnails']['large']

    details = listen.track_name[:128]
    state = f'{listen.artist_name} - {listen.release_name}'[:128]

    status = {
        'details': details,
        'state': state,
        'large_image': album_art, 'large_text': f'{listen.artist_name} - {listen.release_name}',
    }
    if album_art != 'navidrome':
        status['small_image'] = 'navidrome'
        status['small_text'] = 'Navidrome'
    return status


def main():
    RPC = Presence(client_id=DISCORD_CLIENT_ID)
    RPC.connect()

    status = get_status()
    if status is Status.NOT_PLAYING:
        RPC.clear()
        print('Stopped listening')
    else:
        RPC.update(**status)
        print(now_playing)

    while True:
        time.sleep(15)  # Can only update presence every 15 seconds
        status = get_status()
        if status is Status.NOT_PLAYING:
            RPC.clear()
            print('Stopped listening')
        elif status is Status.PLAYING:
            pass
        else:
            RPC.update(**status)
            print(now_playing)


if __name__ == "__main__":
    main()
