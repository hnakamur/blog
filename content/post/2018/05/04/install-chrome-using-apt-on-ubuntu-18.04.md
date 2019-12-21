+++
title="Ubuntu 18.04でaptを使ってchromeをインストール"
date = "2018-05-04T21:00:00+09:00"
lastmod = "2018-05-19T18:22:00+09:00"
tags = ["ubuntu", "chrome"]
categories = ["blog"]
+++


## はじめに

[How to install google chrome on ubuntu 18.04 / 18.10](https://ubuntu-18-04.blogspot.com/2017/12/how-to-install-google-chrome-on-ubuntu-18-04.html) を参考にUbuntu 18.04でaptを使ってchromeをインストールしたメモです。

## インストール手順

```console
curl https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable
