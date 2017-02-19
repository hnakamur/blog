Title: Vagrant 1.1.5とSaharaを試した
Date: 2013-04-03 00:00
Category: blog
Tags: chef, vagrant, sahara
Slug: blog/2013/04/03/how-to-setup-vagrant-1-dot-1-5-and-sahara

## Vagrantと1.0.xと1.1.xについて

バージョン1.1.xの位置づけについては以下の記事を参照。
[Vagrant 1.1, VMware Fusion - HashiCorp](http://www.hashicorp.com/blog/vagrant-1-1-and-vmware.html)
変更履歴は [vagrant/CHANGELOG.md at master · mitchellh/vagrant · GitHub](https://github.com/mitchellh/vagrant/blob/master/CHANGELOG.md)。

gem installで入れられるのは1.0.x系のみ。現在は1.0.7。
[search | RubyGems.org | your community gem host](http://rubygems.org/search?utf8=%E2%9C%93&query=vagrant)

## Vagrant 1.1.5のインストール
[Vagrant](http://www.vagrantup.com/)
→ [Vagrant - Downloads](http://downloads.vagrantup.com/)
→ [Vagrant - Downloads v1.1.5](http://downloads.vagrantup.com/tags/v1.1.5)
と進み、Vagrant.dmgをダウンロードしてインストール


## PATH設定

vagrantコマンドにPATHを通します。

```
cat <<'EOF' >> ~/.bash_profile
export PATH=/Applications/Vagrant/bin:$PATH
EOF
. ~/.bash_profile
```

ruby 1.9.3p327が同梱されています。

```
$ /Applications/Vagrant/embedded/bin/ruby --version
ruby 1.9.3p327 (2012-11-10 revision 37606) [universal.x86_64-darwin12.2.1]
```

### Vagrant 1.1.x用のSaharaをインストール

[Vagrantの必須プラグインSaharaをVagrant 1.1に対応させました | Ryuzee.com](http://www.ryuzee.com/contents/blog/6555)の手順でインストール。

```
mkdir -p ~/src/chef
cd ~/src/chef
git clone https://github.com/ryuzee/sahara.git
cd sahara
export PATH=/Applications/Vagrant/embedded/bin:$PATH
sudo gem install bundler
bundle install
bundle exec rake build
vagrant plugin install pkg/sahara-0.0.14.gem
```

~/.vagrant.d/gems/gems/sahara-0.0.14/にインストールされた。


### 複数VM環境でのテスト

Vagrantfile 
```
-*- mode: ruby -*-
## vi: set ft=ruby :

Vagrant::Config.run do |config|
  config.ssh.private_key_path = "../vagrant.id_rsa"

  config.vm.define :web1 do |c|
    c.vm.box = "centos6.4"
    c.vm.host_name = "web1"
    c.vm.network :hostonly, "192.168.33.24"
    c.vm.customize ["modifyvm", :id,
      "--name", "web1",
      "--natdnshostresolver1", "on",
      "--cpus", 1,
      "--memory", 512
    ]
  end

  config.vm.define :db1 do |c|
    c.vm.box = "centos6.4"
    c.vm.host_name = "db1"
    c.vm.network :hostonly, "192.168.33.25"
    c.vm.customize ["modifyvm", :id,
      "--name", "db1",
      "--natdnshostresolver1", "on",
      "--cpus", 1,
      "--memory", 512
    ]
  end
end
```

なお、centos6.4のVMはrubyやchef-soloはインストールしていない状態になっています。


sandboxモードをオンにしてVM起動。

```
vagrant sandbox on
vagrant up
```

ホスト側からchefセットアップ実行。

```
./bin/knife solo prepare web1
./bin/knife solo prepare db1
```

web1, db1にログインして/usr/bin/chef-soloが作成されたことを確認。

ロールバックを実行。

```
vagrant sandbox rollback
```

web1, db1にログインして/usr/bin/chef-soloが無いことを確認。

ホスト側から再度chefセットアップ実行。

```
./bin/knife solo prepare web1
./bin/knife solo prepare db1
```

コミット実行。

```
vagrant sandbox commit
```

ホスト側からchefクックブック実行。

```
./bin/knife solo cook web1
./bin/knife solo cook db1
```

web1, db1にログインして/usr/bin/chef-soloがあること、/etc/chefが作成されたことをを確認。


ロールバック実行。

```
vagrant sandbox rollback
```

web1, db1にログインして/usr/bin/chef-soloがあること、/etc/chefが無いことをを確認。

テスト環境

* OS: OS X 10.8.3
* VirtualBox: 4.2.10
* Vagrant: 1.1.5
* sahara: https://github.com/ryuzee/sahara.git commit d22795aa417ec1cb67eb92810afb52300edd3c44
