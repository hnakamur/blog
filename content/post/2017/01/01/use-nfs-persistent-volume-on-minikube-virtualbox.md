Title: minikubeとVirtualBoxでNFSのpersistent volumeを試してみた
Date: 2017-01-01 09:40
Category: blog
Tags: kubernetes
Slug: 2017/01/01/use-nfs-persistent-volume-on-minikube-virtualbox

## はじめに
[Tutorials - Kubernetes](http://kubernetes.io/docs/tutorials/)のStateful Applicationsを試そうと思って少し読んだ所、 persistent volume というものを用意する必要があることがわかりました。

[Types of Persistent Volumes](http://kubernetes.io/docs/user-guide/persistent-volumes/#types-of-persistent-volumes) を見るとさまざまなタイプの persistent volume がありますが、Mac上での開発環境としてkubernetesを使うならNFSが手軽そうなので、これを試してみることにしました。

このページを見てもよくわからなかったので、検索して見つけた以下の情報を参考にして試行錯誤して、とりあえず動くようになったのでメモです。

* [Support mounting host directories into pods · Issue #2 · kubernetes/minikube](https://github.com/kubernetes/minikube/issues/2#issuecomment-233629375)
* [kube-solo-osx/nfs-pv-mount-on-pod.md at master · TheNewNormal/kube-solo-osx](https://github.com/TheNewNormal/kube-solo-osx/blob/master/examples/pv/nfs-pv-mount-on-pod.md)
* [kubernetes/examples/volumes/nfs at master · kubernetes/kubernetes](https://github.com/kubernetes/kubernetes/tree/master/examples/volumes/nfs)

## minikubeからmacのディスクをNFSマウントする

[Support mounting host directories into pods · Issue #2 · kubernetes/minikube](https://github.com/kubernetes/minikube/issues/2#issuecomment-233629375)のコメントに従って以下のコマンドをmacで実行しました。

```
echo "/Users -network 192.168.99.0 -mask 255.255.255.0 -alldirs -maproot=root:wheel" | sudo tee -a /etc/exports
sudo nfsd restart
```

IPアドレスは `minikube ip` の結果に合わせて調整します。私の環境では 192.168.99.100 だったので、それにあわせて `-network` は 192.168.99.0、 `-mask` は 255.255.255.0 としています。

以下の手順で、手動で一度マウントしてみました。 `minikube start` は既に起動済みなら不要です。

```
minikube start
minikube ssh -- sudo umount /Users
minikube ssh -- sudo /usr/local/etc/init.d/nfs-client start
minikube ssh -- sudo mount 192.168.99.1:/Users /Users -o rw,async,noatime,rsize=32768,wsize=32768,proto=tcp
```

IPアドレスは `minikube ip` の結果に合わせて調整します。私の環境では 192.168.99.100 だったので、minikubeからmacへは 192.168.99.1 で参照できるということでmountの引数にはこのアドレスを指定しています。

マウントポイントの /Users は適宜変更変更します。

無事マウントできたら `minikube ssh` でssh接続して `df -h` などでマウントされたことを確認し、minikube内からとmac側からファイルを作ったり削除して相互に見えることを確認しました。

一通り確認したらminikube内から `sudo umount /Users` でアンマウントしておきます。

## PodからNFSのpersistent volumeを使ってみる

[kube-solo-osx/nfs-pv-mount-on-pod.md at master · TheNewNormal/kube-solo-osx](https://github.com/TheNewNormal/kube-solo-osx/blob/master/examples/pv/nfs-pv-mount-on-pod.md)と[kubernetes/examples/volumes/nfs at master · kubernetes/kubernetes](https://github.com/kubernetes/kubernetes/tree/master/examples/volumes/nfs)を参考にして試行錯誤しました。

後者の [nfs-web-rc.yaml](https://github.com/kubernetes/kubernetes/blob/f5d9c430e9168cf5c41197b8a4e457981cb031df/examples/volumes/nfs/nfs-web-rc.yaml)では ReplicationController というものを作っているのですが、[google compute engine - Replication Controller VS Deployment in Kubernetes - Stack Overflow](http://stackoverflow.com/questions/37423117/replication-controller-vs-deployment-in-kubernetes/37423281#37423281)というコメントによると、ReplicatioControllerはDeploymentsにとって変わられるものだそうです。ただし、 [google compute engine - Replication Controller VS Deployment in Kubernetes - Stack Overflow](http://stackoverflow.com/questions/37423117/replication-controller-vs-deployment-in-kubernetes/37423217#37423217)によるとDeploymentはまだベータです。

## サービス公開用の設定ファイル

試行錯誤した結果の設定ファイルは以下の通りです。

persistent-volume-nfs.ymlのspec.nfs.pathに対応するディレクトリはmacで `mkdir -p /Users/hnakamur/kube-data` で作成しておきます。spec.nfs.serverはminikubeから見たmacのIPアドレスを指定します。

spec.persistentVolumeReclaimPolicyは[kube-solo-osx/nfs-pv-mount-on-pod.md at 252b46b4837efc41e7c85c7c3171518e23520866 · TheNewNormal/kube-solo-osx](https://github.com/TheNewNormal/kube-solo-osx/blob/252b46b4837efc41e7c85c7c3171518e23520866/examples/pv/nfs-pv-mount-on-pod.md)ではRetainedとなっていたのですが、動かしてみるとエラーメッセージが出たのでそこに書いてあった選択肢の1つのRetainに変えました。

persistemt volumeとpersistent volume claimについては[Persistent Volumes - Kubernetes](http://kubernetes.io/docs/user-guide/persistent-volumes/)に説明があります。

```
$ cat persistent-volume-nfs.yml
kind: PersistentVolume
apiVersion: v1
metadata:
  name: pv-nfs
  labels:
    type: nfs
spec:
  capacity:
    storage: 30Gi
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  nfs:
    # TODO: modify path and server appropriately
    path: /Users/hnakamur/kube-data
    server: 192.168.99.1
```

```
$ cat persistent-volume-claim.yml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: my-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 15Gi
```

Deploymentsについては[Deployments - Kubernetes](http://kubernetes.io/docs/user-guide/deployments/)を参照してください。

```
$ cat nginx-deployment.yml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.11.8
          ports:
            - containerPort: 80
          volumeMounts:
            - mountPath: "/usr/share/nginx/html"
              name: nginx-data
      volumes:
        - name: nginx-data
          persistentVolumeClaim:
            claimName: my-pvc
```

Servicesについては[Services - Kubernetes](http://kubernetes.io/docs/user-guide/services/#type-nodeport)を参照してください。

```
$ cat nginx-service.yml
kind: Service
apiVersion: v1
metadata:
  name: nginx
spec:
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: NodePort
  selector:
    app: nginx
```

## サービス作成と公開

上記の設定ファイルを用意しておけば、サービス作成と公開は以下のように実行するだけです。

```
kubectl create -f persistent-volume-nfs.yml
kubectl create -f persistent-volume-claim.yml
kubectl create -f nginx-deployment.yml
kubectl create -f nginx-service.yml
```

mac上で以下のコマンドでnginxで表示するHTMLファイルを作成します。HTMLファイルと言いつつ手抜きで単なるテキストです。

```
echo 'Hello Kubernetes NFS volume!' > ~/kube-data/index.html
```

## macからcurlでサービスのnginxにアクセスしてみる

ノードのIPとポートを取得して環境変数に設定。

```
$ export NODE_IP=$(minikube ip)
$ echo NODE_IP=$NODE_IP
NODE_IP=192.168.99.100
$ export NODE_PORT=$(kubectl get services/nginx -o go-template='{{(index .spec.ports 0).nodePort}}')
$ echo NODE_PORT=$NODE_PORT
NODE_PORT=32252
```

curlでアクセスすると、上記で作成したファイルの内容が表示されることを確認できました。

```
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes NFS volume!
```

## サービス公開停止と削除

作成時とは逆の順番に `kubectl delete -f` で設定ファイルを指定して削除すればOKでした。

```
kubectl delete -f nginx-service.yml
kubectl delete -f nginx-deployment.yml
kubectl delete -f persistent-volume-claim.yml
kubectl delete -f persistent-volume-nfs.yml
```
