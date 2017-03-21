#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Hiroaki Nakamura'
AUTHOR_URL = 'https://hnakamur.github.io'
SITENAME = "hnakamur's blog at github"
SITEURL = 'https://hnakamur.github.io/blog'

GOOGLE_ANALYTICS = 'UA-53263855-1'

PATH = 'content'
OUTPUT_PATH = 'public/'
# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True
ARTICLE_URL = '{slug}/'
ARTICLE_SAVE_AS = '{slug}/index.html'
PAGE_URL = 'pages/{slug}/'
PAGE_SAVE_AS = 'pages/{slug}/index.html'
# http://docs.getpelican.com/en/stable/content.html#attaching-static-files
STATIC_PATHS = ['images', 'files']
ARTICLE_PATHS = ['post', 'images', 'files']

DEFAULT_LANG = 'ja'
TIMEZONE = 'Asia/Tokyo'
DATE_FORMATS = {
          'en': '%a, %d %b %Y',
          'ja': '%Y-%m-%d',
}

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

USE_FOLDER_AS_CATEGORY = False
DEFAULT_CATEGORY = 'blog'
DISPLAY_CATEGORIES_ON_MENU = True

THEME = 'themes/notmyidea-custom'
# PYGMENTS_RST_OPTIONS = {'classprefix': '', 'linenos': 'table'}

# https://github.com/lqez/pelican-embed-tweet
PLUGIN_PATHS = ['pelican/plugins']
PLUGINS = ['embed_tweet']
