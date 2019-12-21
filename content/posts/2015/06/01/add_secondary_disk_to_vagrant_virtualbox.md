+++
Categories = []
Description = ""
Tags = ["vagrant", "virtualbox"]
date = "2015-06-01T06:04:04+09:00"
title = "Vagrant + Virtualboxでのディスク追加"

+++
Vagrant + Virtualboxでのディスク追加についてのメモです。

## ディスク追加の設定

* http://stackoverflow.com/questions/21050496/vagrant-virtualbox-second-disk-path/26743144#26743144
* https://gist.github.com/leifg/4713995#comment-1206250

を参考に以下のようにしました。

```
# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.box = 'base'

  config.vm.provider "virtualbox" do |p|
    vagrant_root = File.dirname(File.expand_path(__FILE__))
    file_to_disk = File.join(vagrant_root, 'ad1.vdi')
    unless File.exist?(file_to_disk)
      vb.customize ['createhd', '--filename', file_to_disk, '--size', 500 * 1024]
    end
    vb.customize ['storageattach', :id, '--storagectl', 'SATA Controller', '--port', 1, '--device', 0, '--type', 'hdd', '--medium', file_to_disk]
  end
end
```

上記の後者のリンク先では `Vagrantfile` のあるディレクトリを `VAGRANT_ROOT` と大文字で定数に設定していますが、私は `vagrant_root` と小文字で変数にしました。

デバッグプリントを入れてみてわかったのですが、このブロックは1度ではなく複数回呼ばれます。定数だと既に初期化済みの警告が出るので変数にしたというわけです。

## SATA Controllerの作成はpackerで行っておく

上の設定だけでは https://github.com/hnakamur/freebsd-packer/tree/ef57aff51b02a03e658f0348eb5e463ed08735aa で作ったFreeBSD 10.1 amd64のboxではSATA Controllerが無いためうまく行きませんでした。

https://gist.github.com/leifg/4713995#comment-1374268 でVagrantにモンキーパッチで対応しようとしているがうまくいかない例がありました。

[Rescue customization exception · Issue #4015 · mitchellh/vagrant](https://github.com/mitchellh/vagrant/issues/4015#issuecomment-45930125)のVagrant開発者のコメントで、Vagrantfileの設定は手続き型ではなく宣言型なので、Vagrantfileの設定では無理でVagrantプラグインを作る必要があると書かれています。

結局 https://github.com/hnakamur/freebsd-packer/commit/fc041427ffd9de330d390036ebd0948f01e707fe のようにpackerのテンプレートを作る際にSATA Controllerも作っておくのがお手軽だったのでそうしました。
