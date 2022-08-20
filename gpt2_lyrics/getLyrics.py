
# Built-In Python
import os
import typing
from pathlib import Path
import re
import logging
from argparse import ArgumentParser

# Third-Party
import requests
from lyricsgenius import Genius


class Album:
    def __init__(self, album_id, title, artist, year, month):
        self.id = album_id
        self.title = title
        self.artist = artist
        self.year = year
        self.month = month

    def __repr__(self):
        title = self.title or 'Unknown Title'
        artist = self.artist or 'Unknown Artist'
        year = self.year or 'Unknown Year'
        return f"<{self.__class__.__name__} {title} by {artist} ({year})>"


class Song:
    def __init__(self, song_id, title=None, artist=None, year=None, month=None, lyrics=''):
        self.id = song_id
        self.title = title
        self.artist = artist
        self.year = year
        self.month = month

    def __repr__(self):
        title = self.title or 'Unknown Title'
        artist = self.artist or 'Unknown Artist'
        year = self.year or 'Unknown Year'
        return f"<{self.__class__.__name__} {title} by {artist} ({year})>"


class GeniusApi:
    def __init__(self, token):
        self.token = token
        self.genius = Genius(token)

    @classmethod
    def sanitize_lyrics(cls, lyrics):
        if 'lyrics' in lyrics.lower()[:100]:
            lyrics = lyrics[lyrics.lower().index('lyrics') + len('lyrics'):]
        # Some (all?) results end with a 1 or 2-digit number and the word 'Embed'. Remove this:
        embed_strings = re.findall('[0-9]*Embed', lyrics, flags=re.IGNORECASE)
        if embed_strings:
            for x in embed_strings:
                lyrics = lyrics.replace(x, '')
        return lyrics

    def find_artist(self, artist_name, display_songs=3):
        return self.genius.search_artist(artist_name, max_songs=display_songs)

    def get_artist_albums(self, artist_id, min_year=None, max_year=None, remove_if_title_contains=None):
        albums = []
        page_num = 1
        while page_num:
            this_page_albums = self.genius.artist_albums(artist_id=artist_id, page=page_num)
            albums.extend(this_page_albums['albums'])
            page_num = this_page_albums['next_page']

        logging.info('--- Albums ---')

        def album_sorter(a):
            date_comp = a['release_date_components']
            return (date_comp['year'] or 9999, date_comp['month'] or 13) if date_comp else (9999, 13)

        albums.sort(key=album_sorter)
        valid_albums = []
        for album in albums:
            name = album['name']
            year = album['release_date_components']['year'] if album['release_date_components'] else 9999
            month = album['release_date_components']['month'] if album['release_date_components'] else 13

            is_valid_year = (not min_year or year >= min_year) and (not max_year or year <= max_year)
            is_valid_album = (not remove_if_title_contains or not any(
                [x.lower() in name.lower() for x in remove_if_title_contains]))
            if is_valid_year and is_valid_album:
                logging.info(f"Year: {year}, Month: {month if month else ''} Title: {name}")
                valid_albums.append(
                    Album(album['id'], title=name, artist=album['artist']['name'], year=year, month=month)
                )
        return valid_albums

    def get_lyrics(self, song_id, remove_section_headers=False, max_retries=5):
        retries = 1
        lyrics = None
        while lyrics is None and retries < max_retries:
            try:
                lyrics = self.genius.lyrics(song_id, remove_section_headers=remove_section_headers)
                if not lyrics:
                    break
            except requests.exceptions.Timeout as e:
                logging.error(f'Request timed out. Trying again ({retries} / {max_retries}')
                if retries >= max_retries:
                    raise e
                retries += 1
        return self.sanitize_lyrics(lyrics) if lyrics else None

    def get_album_lyrics(self, albums, max_retries=5):
        # Coerce albums to be a list, so we can loop even if there is only 1 album
        albums = [albums] if not isinstance(albums, list) else albums

        found_ids = set()  # Track song ids to avoid getting the same lyrics multiple times
        num_songs = 0      # Total num songs processed
        song_lyrics = []   # A list of strings

        for album in albums:
            tracks = self.genius.album_tracks(album.id)['tracks']  # The tracks on this album
            for track in tracks:
                # A Song Object
                song = Song(song_id=track['song']['id'],
                            title=track['song']['title'],
                            artist=album.artist,
                            year=album.year,
                            month=album.month)

                if song.id in found_ids:
                    logging.warning(f'Already found {song}. Skipping to avoid lyric replication')
                    continue
                logging.info(f'Getting lyrics for {song.title}')
                lyrics = self.get_lyrics(song.id, remove_section_headers=True, max_retries=max_retries)
                found_ids.add(song.id)

                if lyrics:
                    song.lyrics = lyrics
                    song_lyrics.append(song)
                    print(f"\n{song.title}\n{song.lyrics}")
                    num_songs += 1
                else:
                    logging.warning(f'No lyrics found for {song}. Is it instrumental?')
        return song_lyrics

    @classmethod
    def save_lyrics(cls, lyrics: list, save_path: typing.Union[str, Path]):
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        if save_path.suffix == '.txt':
            save_path.unlink(missing_ok=True)  # Delete if already exists
            with open(save_path, 'a') as f:
                for track in lyrics:
                    for line in track.lyrics.split('\n'):
                        f.write(line + '\n')
        else:
            raise Exception(f'Unknown suffix for {save_path}')

    def get_lyrics_by_artist(self, artist_name, save_path='lyrics.txt', min_year=None, max_year=None, max_retries=5,
                             remove_if_album_title_contains=None):
        artist = self.find_artist(artist_name, display_songs=0)

        albums = self.get_artist_albums(artist.id, min_year, max_year, remove_if_album_title_contains)

        lyrics = self.get_album_lyrics(albums, max_retries=max_retries)
        self.save_lyrics(lyrics, save_path)


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

    TOKEN = os.getenv('GENIUS_TOKEN')
    if TOKEN is None:
        raise Exception('Please set GENIUS_TOKEN environment variable to your Genius.com API token')

    out_path = args.output_path or f'data/lyrics/{args.artist}.txt'

    genius_api = GeniusApi(TOKEN)
    genius_api.get_lyrics_by_artist(artist_name=args.artist, save_path=out_path,
                                    min_year=args.min_year, max_year=args.max_year,
                                    remove_if_album_title_contains=args.album_filters)