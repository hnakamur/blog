#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Hiroaki Nakamura'
SITENAME = "hnakamur's blog at github"
SITEURL = 'https://hnakamur.github.io/blog'

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

RELATIVE_URLS = True
ARTICLE_URL = '{slug}/'
ARTICLE_SAVE_AS = '{slug}/index.html'
PAGE_URL = 'pages/{slug}/'
PAGE_SAVE_AS = 'pages/{slug}/index.html'

GOOGLE_ANALYTICS = 'UA-53263855-1'

THEME = 'themes/notmyidea-custom'
PYGMENTS_RST_OPTIONS = {'classprefix': '', 'linenos': 'table'}
