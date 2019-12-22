+++
title="aptでgrafanaをインストール"
date = "2019-12-22T23:50:00+09:00"
tags = ["grafana"]
categories = ["blog"]
+++


参考: [Install on Debian/Ubuntu | Grafana Labs](https://grafana.com/docs/grafana/latest/installation/debian/)

grafana の apt レポジトリの GPG 鍵を追加します。

```console
curl -sSL https://packages.grafana.com/gpg.key | sudo apt-key add -
```

apt-transport-https をまだ入れていない場合はインストールします。

```console
sudo apt -y install apt-transport-https
```

apt line を追加します。

```console
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
```

grafana パッケージをインストールします。

```console
sudo apt update
sudo apt -y install grafana
```

以下はオプショナルです。以下では tank1 という zfs ボリュームが既にある想定で tank1/grafana ボリュームを新規作成し /var/lib/grafana にマウントポイントを設定します。

```console
sudo systemctl stop grafana-server

sudo mv /var/lib/grafana{,.bak}
sudo mkdir /var/lib/grafana
sudo chown grafana: /var/ilb/grafana

sudo zfs create tank1/grafana
sudo zfs set mountpoint=/var/lib/grafana tank1/grafana

sudo tar cf - . -C /var/lib/grafana.bak | sudo tar xf - -C /var/lib/grafana

sudo systemctl start grafana-server
```

動作確認して問題なければ `/var/lib/grafana.bak` を削除します。

```console
rm -rf /var/lib/grafana.bak
```
