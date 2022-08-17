import re
from pathlib import Path
from lyricsgenius import Genius

# Get Lyrics

genius_token = 'xyz'  # Replace 'xyz' with your token

# Replace 'Green Day' with any artist you want
# But if you change the artist,
# you must also change valid_albums!
# Set valid_albums = [] to use all albums
# by the artist (may take a while!)
artist_name = 'Green Day'  # Lyrics will be inspired by this artist
# Let's use only their first 5 major-label releases
valid_albums = [
    'Dookie', 'Insomniac', 'Nimrod', 'Warning', 'American Idiot'
]
outpath = Path(f'data/lyrics/{artist_name}.txt')  # Save the lyrics here

genius = Genius(genius_token)  # Initiate a Genius instance
# Find the artist by name - we will need their "artist id" later
# We will filter by album, so set max_songs to 0 for now.
artist = genius.search_artist(artist_name, max_songs=0)

# Gather the artist's albums
albums = []
page_num = 1
while page_num:
    # Genius.com returns their results in pages.
    # We will loop through until all the pages have been queried
    this_page_albums = genius.artist_albums(artist_id=artist.id, page=page_num)
    albums.extend(this_page_albums['albums'])
    page_num = this_page_albums['next_page']
# Get the album IDs
album_ids = [
    a['id'] for a in albums
        if not valid_albums or
        a['name'] in valid_albums
]


def sanitize_lyrics(lyric_string):
    """A helper function to clean up the lyrics from Genius.com"""
    if 'lyrics' in lyric_string.lower()[:100]:
        # Sometimes the lyrics start with the title of the song
        # and the word "lyrics".
        #     i.e. "American Idiot Lyrics"
        lyric_string = lyric_string[
            lyric_string.lower().index('lyrics') + len('lyrics'):
        ]
    # For no apparent reason, some (or all?) results end
    # with a 1 or 2-digit number and the word 'Embed'.
    # The following RegEx removes this:
    embed_strings = re.findall(
        '[0-9]*Embed', lyric_string, flags=re.IGNORECASE
    )
    if embed_strings:
        # Just in case there are multiple "embed" strings,
        # make sure to remove them all
        for x in embed_strings:
            lyric_string = lyric_string.replace(x, '')
    return lyric_string


print(f'Gathering lyrics for {len(album_ids)} albums -'
      'this could take a while...')
# Gather the lyrics for all songs on our chosen albums
song_lyrics = ''
for album_id in album_ids:
    # The tracks on this album
    tracks = genius.album_tracks(album_id)['tracks']
    for track in tracks:
        song_id = track['song']['id']  # The Genius.com ID

        # Get the lyrics for this song
        # remove_section_headers=True because we don't want
        # non-lyrical content like [Intro], [Verse], [Chorus].
        # N.B. Sometimes this request raises a Timeout Exception.
        #      If so, just re-run the code.
        #      If you are using this in code that you need to be
        #      stable, use a try-except block in a loop
        lyrics = genius.lyrics(song_id, remove_section_headers=True)
        if lyrics:  # Some songs have no lyrics. Skip them
            lyrics = sanitize_lyrics(lyrics)
            song_lyrics += "/n/n" + lyrics

# Save the lyrics to a file
outpath.parent.mkdir(parents=True, exist_ok=True)  # If there is no directory called "lyrics", make one.
with open(str(outpath), 'w') as f:
    f.write(song_lyrics)


# TRAIN:
import gpt_2_simple as gpt2
# PARAMS:
# *** The artist_name here must match the artist_name above.   ***
# *** and the training_text_filepath much match outpath above. ***
# I have copied them here, but commented out the artist_name
# assuming you may want to separate this section
# into a new module, in which case you will want to uncomment artist_name and set it accordingly

# artist_name = 'Green Day'
training_text_filepath = Path(f'data/lyrics/{artist_name}.txt')
# Run the tuning for now more than 1000 iterations
# Set this lower for faster training
# or higher for more stylistic precision
max_epochs = 1000
# Every 100 epochs, generate and print a lyric-sample,
# so we can see how the model is progressing
# If everything is going well,
# these samples should get better and better
sample_every = 100

# Start with GPT-2's 124 million parameter model
gpt2_model_name = '124M'
# PATHS:
# Where to save the model
model_dir = Path('models').joinpath(artist_name)

# Download the GPT-2 model (if necessary)
# model_name is something like '124M' (see download_gpt2_model docstring for other options)
if not Path("models").joinpath(gpt2_model_name).exists():
    gpt2.download_gpt2(
        model_name=gpt2_model_name,
        model_dir=model_dir
    )

# Where to save Checkpoints (partially-trained models)
checkpoint_dir = Path('checkpoint').joinpath(artist_name)

# The actual training starts here:
sess = gpt2.start_tf_sess()  # Start, and get, a Tensorflow Session
# Fine-Tune the model
gpt2.finetune(
    sess,
    dataset=str(training_text_filepath),
    steps=max_epochs, sample_every=sample_every,
    model_dir=model_dir,
    checkpoint_dir=checkpoint_dir
)

# GENERATE:
# N.B. If you are putting all the code in a single module,
#      you only need the final call: gpt2.generate().
#      You can delete everything above it.
#      I have left in duplicate imports and variables assuming you
#      will want to put this code in a seperate module.
import gpt_2_simple as gpt2

artist_name = 'Green Day'
# Where to save the model
model_dir = Path('models').joinpath(artist_name)

# Where to save checkpoints (unfinished training runs)
checkpoint_dir = Path('checkpoint').joinpath(artist_name)

# Load the trained model
sess = gpt2.start_tf_sess()
gpt2.load_gpt2(
    sess,
    checkpoint_dir=checkpoint_dir,
    model_dir=model_dir
)

# Generate Lyrics!
gpt2.generate(
    sess,
    temperature=0.7,
    checkpoint_dir=checkpoint_dir,
    model_dir=model_dir
)
