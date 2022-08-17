
# Built-In Python
import json
from pathlib import Path
import re
import logging
from argparse import ArgumentParser

# Third-Party
import requests
from lyricsgenius import Genius


def get_lyrics(token, artist, save_path='lyrics.txt', min_year=None, max_year=None, max_songs=None, max_retries=5,
               remove_if_album_contains=None):

    genius = Genius(token)
    artist = genius.search_artist(artist, max_songs=0)

    albums = []
    page_num = 1
    while page_num:
        this_page_albums = genius.artist_albums(artist_id=artist.id, page=page_num)
        albums.extend(this_page_albums['albums'])
        page_num = this_page_albums['next_page']

    logging.info('--- Albums ---')

    def album_sorter(a):
        date_comp = a['release_date_components']
        return (date_comp['year'] or 9999, date_comp['month'] or 13) if date_comp else (9999, 13)

    albums.sort(key=album_sorter)
    real_albums = []
    for album in albums:
        name = album['name']
        year = album['release_date_components']['year'] if album['release_date_components'] else 9999
        month = album['release_date_components']['month'] if album['release_date_components'] else 13

        is_valid_year = (not min_year or year >= min_year) and (not max_year or year <= max_year)
        is_valid_album = (not remove_if_album_contains or not any(
            [x.lower() in name.lower() for x in remove_if_album_contains]))
        if is_valid_year and is_valid_album:
            logging.info(f"Year: {year}, Month: {month if month else ''} Title: {name}")
            real_albums.append({'id': album['id'], 'name': name, 'year': year})

    num_songs = 0
    tracks_by_album = {}
    for album in real_albums:
        tracks = genius.album_tracks(album['id'])
        tracks_by_album[album['name']] = []
        for track in tracks['tracks']:
            if max_songs is not None and num_songs >= max_songs:
                break
            retries = 1
            lyrics = None
            while lyrics is None and retries < max_retries:
                try:
                    logging.info(f'Getting lyrics for {track["song"]["title"]}')
                    lyrics = genius.lyrics(track['song']['id'], remove_section_headers=True)
                    if not lyrics:
                        break
                except requests.exceptions.Timeout as e:
                    logging.error(f'Request timed out. Trying again ({retries} / {max_retries}')
                    if retries >= max_retries:
                        raise e
                    retries += 1

            if lyrics:
                if 'lyrics' in lyrics.lower()[:100]:
                    lyrics = lyrics[lyrics.lower().index('lyrics') + len('lyrics'):]
                # Some (all?) results end with a 1 or 2-digit number and the word 'Embed'. Remove this:
                embed_strings = re.findall('[0-9]*Embed', lyrics, flags=re.IGNORECASE)
                if embed_strings:
                    for x in embed_strings:
                        lyrics = lyrics.replace(x, '')
                this_song = {'title': track['song']['title'], 'lyrics': lyrics}
                tracks_by_album[album['name']].append(this_song)
                print(f"\n{this_song['title']}")
                print(this_song['lyrics'])
                num_songs += 1

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if save_path.suffix == '.json':
        with open(save_path, 'w') as jf:
            json.dump(tracks_by_album, jf, indent=4)
    elif save_path.suffix == '.txt':
        if save_path.exists():  # Delete if already exists
            save_path.unlink()
        with open(save_path, 'a') as f:
            for album, tracks in tracks_by_album.items():
                for track in tracks:
                    # f.write('\n' + track['title'] + '\n')
                    for line in track['lyrics'].split('\n'):
                        f.write(line + '\n')
    else:
        raise Exception(f'Unknown suffix for {save_path}')


if __name__ == '__main__':
    logging.getLogger().setLevel('INFO')

    parser = ArgumentParser(description='A script which uses the Genius.com api to fetch song lyrics')
    parser.add_argument('-artist', type=str, help='Search for songs by this artist')
    parser.add_argument('-min_year', type=int, help='Filter out any songs before this year')
    parser.add_argument('-max_year', type=int, help='Filter out any songs after this year')
    parser.add_argument('-album_filters', nargs='*',
                        help='A list of strings. Any album containing any of these strings will not be used '
                             '(case insensitive)')
    parser.add_argument('-output_path', help='Save the lyrics to this filepath')
    args = parser.parse_args()

    TOKEN = 'c_ZYOMNLSa1mb6gn31CXQ89vYL948UtzzyS_o0oRvc92fIYjJJzLAopxgNjXOCVH'

    out_path = args.output_path or f'data/lyrics/{args.artist}.txt'
    get_lyrics(token=TOKEN, artist=args.artist, min_year=args.min_year, max_year=args.max_year, save_path=out_path,
               remove_if_album_contains=args.album_filters)
