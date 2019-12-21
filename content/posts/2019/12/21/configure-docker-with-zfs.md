+++
title="DockerでZFSストレージドライバを使う"
date = "2019-12-21T21:00:00+09:00"
tags = ["docker", "zfs"]
categories = ["blog"]
+++


参考: [Use the ZFS storage driver | Docker Documentation](https://docs.docker.com/storage/storagedriver/zfs-driver/)

`/var/lib/docker` を `/var/lib/docker.bak` にリネームして `/var/lib/docker` を作り直しパーミションを合わせます。

```console
sudo mv /var/lib/docker{,.bak}
sudo mkdir /var/lib/docker
sudo 711 /var/lib/docker
```

以下では `tank1` というボリュームが既にある想定で `tank1/docker` ボリュームを新規作成し `/var/lib/docker` にマウントポイントを設定します。

```console
sudo zfs create tank1/docker
sudo zfs set mountpoint=/var/lib/docker tank1/docker
```

`/var/lib/docker.bak` の内容を `/var/lib/docker` にコピーします。

```console
sudo tar cf - . -C /var/lib/docker.bak | sudo tar xf - -C /var/lib/docker
```

動作確認して問題なければ `/var/lib/docker.bak` を消します。

```console
sudo rm -rf /var/lib/docker.bak
