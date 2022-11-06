---
title: "UbuntuのUSERとLOGNAME環境変数について調べてみた"
date: 2022-11-06T09:56:38+09:00
---
## はじめに

Linuxで現在のユーザ名の取得に `USER` 環境変数を使っていたのですが、どこで設定されているのか調べたことがなかったので調べてみたメモです。

## USER と LOGNAME は login コマンドが設定している

[Who sets $USER and $USERNAME environment variables? - Unix & Linux Stack Exchange](https://unix.stackexchange.com/questions/76354/who-sets-user-and-username-environment-variables) の[回答](https://unix.stackexchange.com/a/76356/135274) によると Linux の [man 1 login](https://man7.org/linux/man-pages/man1/login.1.html) に以下の記載があるとのことでした。

> The environment variable values for
> $HOME, $USER, $SHELL, $PATH, $LOGNAME, and $MAIL are set
> according to the appropriate fields in the password entry.

一方、 [Ubuntu Manpage: login - begin session on the system](https://manpages.ubuntu.com/manpages/jammy/en/man1/login.1.html) では以下のようになっておりUSERについては記載がありませんでした。

> The value for $HOME, $SHELL, $PATH, $LOGNAME, and $MAIL are set according to the appropriate
> fields in the password entry.

### login パッケージのソースを確認

そこでソースを確認しようと思ってパッケージを調べました。

```
$ type login
login is /usr/bin/login
$ dpkg -S /bin/login
login: /bin/login
```

作業ディレクトリを作って login パッケージのソースをダウンロードしてみると、以下のように shadow-4.8.1 というディレクトリにソースが展開されました。

```
$ mkdir ~/login-deb-src
$ cd !$
$ apt source login
$ ls
shadow-4.8.1  shadow_4.8.1-2ubuntu2.debian.tar.xz  shadow_4.8.1-2ubuntu2.dsc  shadow_4.8.1.orig.tar.xz
```

`dpkg -l` で調べると shadow パッケージはなく login パッケージだけがありました。よくわかりませんが、こちらは一旦棚上げ。

```
$ LC_ALL=C dpkg -l login shadow
dpkg-query: no packages found matching shadow
Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name           Version          Architecture Description
+++-==============-================-============-=================================
ii  login          1:4.8.1-2ubuntu2 amd64        system login tools
```

shadow-4.8.1 のディレクトリ内で LOGNAME を検索して見ていくと以下の箇所で USER と LOGNAME 環境変数を設定していました。

https://git.launchpad.net/ubuntu/+source/shadow/tree/libmisc/setupenv.c?h=applied/1%254.8.1-2ubuntu1#n254

```c
  /*
   * Export the user name.  For BSD derived systems, it's "USER", for
   * all others it's "LOGNAME".  We set both of them.
   */

  addenv ("USER", info->pw_name);
  addenv ("LOGNAME", info->pw_name);
```

## Ubuntu では cron ジョブでは USER は設定されないが LOGNAME は設定される

[scripts - Environment Variable for Username - Ask Ubuntu](https://askubuntu.com/questions/802733/environment-variable-for-username) の [回答](https://askubuntu.com/a/802892/707184) によると、cron ジョブでは USER は設定されないが LOGNAME は設定されるとのことです(回答者の方は Ubuntu 14.04 で確認したとのこと)。

Ubuntu 22.04 LTS の環境で以下の内容で `/etc/cron.d/echo_env_user` というファイルを作って試してみました。

```
* * * * * root /bin/sh -c 'echo USER=$USER LOGNAME=$LOGNAME' >> /tmp/cron-env-user.log
```

cron ジョブが実行されるのを待ってからログを確認すると以下のようになっており、cron ジョブでは USER は設定されないが LOGNAME は設定されることが確認できました。

```
$ head -1 /tmp/cron-env-user.log
USER= LOGNAME=root
```

確認後 cron の設定とログは以下のコマンドで削除しました。

```
sudo rm /etc/cron.d/echo_env_user /tmp/cron-env-user.log
```

### Ubuntu の cron パッケージのソースを確認

https://git.launchpad.net/ubuntu/+source/cron/tree/entry.c?h=applied/3.0pl1-137#n301

```c
  snprintf(envstr, MAX_ENVSTR, "%s=%s", "LOGNAME", pw->pw_name);
  if ((tenvp = env_set(e->envp, envstr))) {
    e->envp = tenvp;
  } else {
    ecode = e_none;
    goto eof;
  }
#if defined(BSD)
  snprintf(envstr, MAX_ENVSTR, "%s=%s", "USER", pw->pw_name);
  if ((tenvp = env_set(e->envp, envstr))) {
    e->envp = tenvp;
  } else {
    ecode = e_none;
    goto eof;
  }
#endif
```

https://git.launchpad.net/ubuntu/+source/cron/tree/debian/rules?h=applied/3.0pl1-137
を見ると BSD は定義していなさそうでした。

## USER は BSD 由来、LOGNAME は System-V 由来

上の [回答](https://askubuntu.com/a/802892/707184) には `man 7 environ` で USER は BSD 由来のプログラムで使われ、 LOGNAME は System-V 由来のプログラムで使われると書かれているとありました。

[Ubuntu Manpage: environ - user environment](https://manpages.ubuntu.com/manpages/jammy/en/man7/environ.7.html) も見てみると以下のように書かれていました。

> USER   The name of the logged-in user (used by some BSD-derived programs).
>
> LOGNAME
>        The name of the logged-in user (used by some System-V derived programs).
