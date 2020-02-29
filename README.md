blog
====

hnakamur's tech blog (powered by Hugo and GitHub Pages).

## setup
[Host on GitHub | Hugo](https://gohugo.io/hosting-and-deployment/hosting-on-github/#build-and-deployment)

```console
rm -rf public
git worktree add -B gh-pages public origin/gh-pages
```

## development

Create a new article.

```console
hugo new post/2006/01/02/article-title.md
```

```console
./dev.sh
```

## deploy

```console
./deploy.sh
```
