#!/bin/sh
set -e
hugo
git -C public add --all
git -C public commit -m "Publishing to gh-pages"
git push origin --all
