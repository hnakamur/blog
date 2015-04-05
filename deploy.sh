#!/bin/bash

echo -e "\033[0;32mDeploying updates to GitHub...\033[0m"

# Build the project. 
hugo -t liquorice-hn

# Add changes to git.
git add -A

# Commit changes.
msg="rebuilding site `LANG=C date '+%Y-%m-%dT%H:%M:%S%z'`"
if [ $# -eq 1 ]
  then msg="$1"
fi
git commit -m "$msg"

# Push source and build repos.
git push origin master
git subtree push --prefix=public https://github.com/hnakamur/blog.git gh-pages
