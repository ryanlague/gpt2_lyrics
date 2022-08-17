from setuptools import setup, find_packages

setup(
    name='gpt2_lyrics',
    version='1.0.0',
    description='Create Lyrics inspired by an artist using Genius API and GPT-2',
    author='Ryan Lague',
    author_email='ryanlague@hotmail.com',
    packages=find_packages(),
    install_requires=[
        'requests',
        'gpt_2_simple',
        'lyricsgenius'
    ]
)