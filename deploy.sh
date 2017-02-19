#!/bin/bash

echo -e "\033[0;32mDeploying updates to GitHub...\033[0m"

pelican content
ghp-import public
git push origin master gh-pagse
