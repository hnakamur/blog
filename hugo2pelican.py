#!/usr/bin/env python
import os
import fileinput

def print_meta(path, title, date, tags):
    slug = os.path.splitext(path.replace('content/post', 'blog'))[0]
    print('Title: {0}'.format(title))
    print('Date: {0}'.format(date))
    print('Category: blog')
    if len(tags) > 0:
        print('Tags: {0}'.format(tags.lower()))
    print('Slug: {0}'.format(slug))
    print()

def convert_file(path):
    with fileinput.input(files=(path,), inplace=True) as f:
        state = 'start'
        title = ''
        date = ''
        tags = ''
        for line in f:
            line = line.strip('\n')
            if state == 'start':
                if line == '---':
                    state = 'octopress-meta'
                elif line == '+++':
                    state = 'hugo-meta'
                else:
                    # already converted
                    print(line)
                    state = 'body'
            elif state == 'octopress-meta':
                if line == '---':
                    print_meta(path, title, date, tags)
                    state = 'body'
                else:
                    kv = line.split(': ', maxsplit=1)
                    key = kv[0].lower()
                    if key == 'title':
                        title = kv[1].strip('"')
                    elif key == 'date':
                        date = kv[1] + ' 00:00'
                    elif key == 'categories':
                        tags = kv[1].strip('[]')
            elif state == 'hugo-meta':
                if line == '+++':
                    print_meta(path, title, date, tags)
                    state = 'body'
                else:
                    kv = line.split(' = ', maxsplit=1)
                    key = kv[0].lower()
                    if key == 'title':
                        title = kv[1].strip('"')
                    elif key == 'date':
                        date = kv[1].strip('"').replace('T', ' ')[:len('YYYY-MM-DD HH:MM')]
                    elif key == 'tags':
                        tags = kv[1].strip('[]').replace('"', '')
            else:
                print(line)

for path, dirs, files in os.walk('content'):
    for f in files:
        if f.endswith('.md') or f.endswith('.markdown'):
            fpath = os.path.join(path, f)
            print('path={0}'.format(fpath))
            convert_file(fpath)
