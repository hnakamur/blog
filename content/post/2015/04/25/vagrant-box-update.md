Title: vagrant box updateでboxファイルをアップグレードする
Date: 2015-04-25 21:55
Category: blog
Tags: vagrant
Slug: blog/2015/04/25/vagrant-box-update


Vagrant Cloudに上がっているUbuntu trustyのオフィシャルイメージ[ubuntu/trusty64 | Atlas by HashiCorp](https://atlas.hashicorp.com/ubuntu/boxes/trusty64)をVagrantfileで参照していたら、 `vagrant up` の際に以下の様なメッセージが表示される時がありました。

```
$ vagrant up
…(略)…
==> default: A newer version of the box 'ubuntu/trusty64' is available! You currently
==> default: have version '14.04'. The latest is version '20150422.0.0'. Run
==> default: `vagrant box update` to update.
```

以下のように実行するとアップデートが出来ました。

```
$ vagrant box update --box ubuntu/trusty64
Checking for updates to 'ubuntu/trusty64'
Latest installed version: 14.04
Version constraints: > 14.04
Provider: virtualbox
Updating 'ubuntu/trusty64' with provider 'virtualbox' from version
'14.04' to '20150422.0.0'...
Loading metadata for box 'https://atlas.hashicorp.com/ubuntu/trusty64'
Adding box 'ubuntu/trusty64' (v20150422.0.0) for provider: virtualbox
Downloading: https://atlas.hashicorp.com/ubuntu/boxes/trusty64/versions/20150422.0.0/providers/virtualbox.box
Successfully added box 'ubuntu/trusty64' (v20150422.0.0) for 'virtualbox'!
```

アップデート完了後、box一覧を確認してみると以下のように新旧のバージョンが出力されました。

```
$ vagrant box list | grep 'ubuntu/trusty64'
ubuntu/trusty64                               (virtualbox, 14.04)
ubuntu/trusty64                               (virtualbox, 20150422.0.0)
```

検証用に古いバージョンを使うことはできるのかなと思ったら[Box Versioning - Vagrant Documentation](https://docs.vagrantup.com/v2/boxes/versioning.html)に書いてありました。

`config.vm.box_version` を指定すれば良いようです。
また `config.vm.box_check_update = false` を指定すれば、boxの新バージョンが出ているかのチェックを無効にできるそうです。
