#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Hiroaki Nakamura'
SITENAME = "hnakamur's blog at github"
SITEURL = ''

PATH = 'content'

TIMEZONE = 'Asia/Tokyo'

DEFAULT_LANG = 'ja'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = ()

# Social widget
SOCIAL = ()

DEFAULT_PAGINATION = True

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

OUTPUT_PATH = 'public/'
USE_FOLDER_AS_CATEGORY = False
DEFAULT_CATEGORY = 'blog'
DISPLAY_CATEGORIES_ON_MENU = True

DATE_FORMATS = {
          'en': '%a, %d %b %Y',
          'ja': '%Y-%m-%d',
}
