# python-ffdl
Fanfiction downloader

[![Build Status](https://travis-ci.org/Birion/python-ffdl.svg?branch=master)](https://travis-ci.org/Birion/python-ffdl)

## Installation

`$ pip install git+ssh://git@github.com/Birion/python-ffdl.git@master`

## Usage

### Download a new story

`pyffdl download [--from <URL FILE>] [<URL>[ <URL>[...]]]`

`pyffdl simple --author <NAME> --title <TITLE> [--from <URL FILE>] [<CHAPTER URL>[ <CHAPTER URL>[...]]]`

### Update an existing story file

`pyffdl.py update [--force] [--backup] <EPUB FILE>`

## Supported sites

* [adult-fanfiction.org](http://adult-fanfiction.org)
* [archiveofourown.org](https://archiveofourown.org)
* [fanfiction.net](https://fanfiction.net)
* [fictionpress.com](https://fictionpress.com)
* [tthfanfic.org](https://tthfanfic.org)

## TODO

* better covers
    * by genres?
* actually useful tests