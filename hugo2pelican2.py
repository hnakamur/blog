#!/usr/bin/env python
import os
import fileinput

def convert_file(path):
    with fileinput.input(files=(path,), inplace=True) as f:
        for line in f:
            line = line.strip('\n')
            if line.startswith('Slug:'):
                slug = line[len('Slug: blog/'):]
                print('Slug: {0}'.format(slug))
            else:
                print(line)

for path, dirs, files in os.walk('content'):
    for f in files:
        if f.endswith('.md') or f.endswith('.markdown'):
            fpath = os.path.join(path, f)
            print('path={0}'.format(fpath))
            convert_file(fpath)
