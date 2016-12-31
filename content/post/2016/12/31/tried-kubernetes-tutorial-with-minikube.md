+++
date = "2016-12-31T16:24:33+09:00"
title = "minikubeでKubernetesのチュートリアルをやってみた"
Categories = []
Tags = ["kubernetes"]
Description = ""

+++
## はじめに

検索してたら [Why Kubernetes is winning the container war | Hacker News](https://news.ycombinator.com/item?id=12462261) というHacker Newsのスレッドを見つけました。

実際に勝つどうかはともかく、実際に使っている人やMesosphereやRed Hatの人のコメントがあり、非常に参考になりそうです。このブログ記事を書くまで私は Kubernetes はろくに触ったことが無かったので内容はよくわからないですが、後日また見直してみたいところです。

上記のHacker Newsのコメントで以下の2つのチュートリアルが紹介されていました。このブログ記事はこのうち1つめのほうを試してみたメモです。

* [Kubernetes Bootcamp](https://kubernetesbootcamp.github.io/kubernetes-bootcamp/)
* [kelseyhightower/kubernetes-the-hard-way: Bootstrap Kubernetes the hard way on Google Cloud Platform or Amazon EC2. No scripts.](https://github.com/kelseyhightower/kubernetes-the-hard-way)

試してから気づいたのですが、全く同じ内容が Kubernetes の公式ドキュメントの [Kubernetes Basics](http://kubernetes.io/docs/tutorials/kubernetes-basics/) にありました。

[Kubernetes Basics](http://kubernetes.io/docs/tutorials/kubernetes-basics/) はいくつかの章（このチュートリアルでは Module と呼ばれています）に分かれていて、まず図解付きのわかりやすい概念説明があり、その後ブラウザ上のターミナルでコマンドを入力すると結果が表示されるというインタラクティブなチュートリアルになっています。

各章末にクイズがあり、概念を理解したか確認できるのも良い感じです。

ターミナルの左に説明文があり、入力する各コマンドをマウスでクリックすると、右側のターミナルに入力してくれるので手軽に試せます。

とはいえ、手元の環境でも試してみたかったので、macOS上に環境構築してブラウザのインタラクティブチュートリアルとともに試してみました。

## macOS Sierraでの事前準備

`minikube start --help` の `--vm-driver` の説明によると仮想マシンドライバは virtualbox xhyve vmwarefusion のいずれかでデフォルトは virtualbox です。
ということでVirtualBoxをインストールしておきます。私の環境ではバージョンは 5.1.12 でした。 

minikubeとKubernetesはGitHubのプロジェクトにリリースページがあってそこからバイナリをダウンロードできます。

* [Release v0.14.0 · kubernetes/minikube](https://github.com/kubernetes/minikube/releases/tag/v0.14.0)
* [Release v1.5.1 · kubernetes/kubernetes](https://github.com/kubernetes/kubernetes/releases/tag/v1.5.1)

が、Homebrewでパッケージが用意されていてバージョンも上記と同じで最新だったのでHomebrewでインストールしました。

```
brew install Caskroom/cask/minikube
brew install kubectl
```

## Module 1: Kubernetsクラスタを作成する

概念の説明は [Introduction to Kubernetes cluster](https://kubernetesbootcamp.github.io/kubernetes-bootcamp/1-1.html) を参照してください。

### minikubeのバージョン確認

```
$ minikube version       
minikube version: v0.14.0
```

### minikube起動

```
$ minikube start
Starting local Kubernetes cluster...
Kubectl is now configured to use the cluster.
```

### kubectlのバージョン確認

```
$ kubectl version
Client Version: version.Info{Major:"1", Minor:"5", GitVersion:"v1.5.1", GitCommit:"82450d03cb057bab0950214ef122b67c83fb11df", GitTreeState:"clean", BuildDate:"2016-12-22T13:56:59Z", GoVersion:"go1.7.4", Compiler:"gc", Platform:"darwin/amd64"}
Server Version: version.Info{Major:"1", Minor:"5", GitVersion:"v1.5.1", GitCommit:"82450d03cb057bab0950214ef122b67c83fb11df", GitTreeState:"clean", BuildDate:"1970-01-01T00:00:00Z", GoVersion:"go1.7.1", Compiler:"gc", Platform:"linux/amd64"}
```

### クラスタの情報表示

```
$ kubectl cluster-info
Kubernetes master is running at https://192.168.99.100:8443
kubernetes-dashboard is running at https://192.168.99.100:8443/api/v1/proxy/namespaces/kube-system/services/kubernetes-dashboard

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
```

### ノード一覧

```
$ kubectl get nodes
NAME       STATUS    AGE
minikube   Ready     11h
```


## Module 2: アプリをデプロイ

概念の説明は [Your first application deployment](https://kubernetesbootcamp.github.io/kubernetes-bootcamp/2-1.html) を参照してください。

### kubernetes-bootcampアプリをデプロイ

チュートリアルのために用意されたkubernetes-bootcampアプリをデプロイしてみます。

```
$ kubectl run kubernetes-bootcamp --image=docker.io/jocatalin/kubernetes-bootcamp:v1 --port=8080
deployment "kubernetes-bootcamp" created
```

### デプロイされたアプリ一覧

```
$ kubectl get deployments
NAME                  DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
kubernetes-bootcamp   1         1         1            1           57s
```

### プロキシ起動

```
$ kubectl proxy
Starting to serve on 127.0.0.1:8001
```

プロキシを起動したらプロンプトには戻ってこないので、以降のコマンドは別のターミナルで実行します。

### Podの名前を取得

この後参照するため、Podの名前を取得して環境変数POD_NAMEに設定しておきます。

```
$ export POD_NAME=$(kubectl get pods -o go-template --template '{{range .items}}{{.metadata.name}}{{"\n"}}{{end}}')
$ echo Name of the Pod: $POD_NAME
Name of the Pod: kubernetes-bootcamp-390780338-6j8fn
```

見た感じ `--template` の引数の書式はGo言語の [text/template](https://golang.org/pkg/text/template/)パッケージのテンプレート言語をそのまま使っているようです。

Pod名の `390780338-6j8fn` の部分はデプロイの度に生成されるランダムな文字列となっています。

### プロキシ経由でアプリにアクセス

```
$ curl http://localhost:8001/api/v1/proxy/namespaces/default/pods/$POD_NAME/
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-390780338-6j8fn | v=1
```

## Module 3: デプロイしたアプリを詳しく見てみる

概念の説明は [Pods and Nodes](https://kubernetesbootcamp.github.io/kubernetes-bootcamp/3-1.html) を参照してください。

### Pod一覧表示

```
$ kubectl get pods
NAME                                  READY     STATUS    RESTARTS   AGE
kubernetes-bootcamp-390780338-6j8fn   1/1       Running   0          13m
```

### Pod詳細表示

```
$ kubectl describe pods
Name:           kubernetes-bootcamp-390780338-6j8fn
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 17:15:41 +0900
Labels:         pod-template-hash=390780338
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.4
Controllers:    ReplicaSet/kubernetes-bootcamp-390780338
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://f3d04d91e8f27b2b537c20d82253376993483f9bb9c0d1196ba50ecc3a69ff7c
    Image:              docker.io/jocatalin/kubernetes-bootcamp:v1
    Image ID:           docker://sha256:8fafd8af70e9aa7c3ab40222ca4fd58050cf3e49cb14a4e7c0f460cd4f78e9fe
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 17:15:42 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         True 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  15m           15m             1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-390780338-6j8fn to minikube
  15m           15m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "docker.io/jocatalin/kubernetes-bootcamp:v1" already present on machine
  15m           15m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id f3d04d91e8f2; Security:[seccomp=unconfined]
  15m           15m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id f3d04d91e8f2
```

### Podのログ表示

```
$ kubectl logs $POD_NAME
Kubernetes Bootcamp App Started At: 2016-12-31T08:15:42.728Z | Running On:  kubernetes-bootcamp-390780338-6j8fn 

Running On: kubernetes-bootcamp-390780338-6j8fn | Total Requests: 1 | App Uptime: 580.532 seconds | Log Time: 2016-12-31T08:25:23.260Z
```

### Pod内でコマンド実行

envコマンドを実行してみます。

```
$ kubectl exec $POD_NAME env
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOSTNAME=kubernetes-bootcamp-390780338-6j8fn
KUBERNETES_SERVICE_HOST=10.0.0.1
KUBERNETES_SERVICE_PORT=443
KUBERNETES_SERVICE_PORT_HTTPS=443
KUBERNETES_PORT=tcp://10.0.0.1:443
KUBERNETES_PORT_443_TCP=tcp://10.0.0.1:443
KUBERNETES_PORT_443_TCP_PROTO=tcp
KUBERNETES_PORT_443_TCP_PORT=443
KUBERNETES_PORT_443_TCP_ADDR=10.0.0.1
NPM_CONFIG_LOGLEVEL=info
NODE_VERSION=6.3.1
HOME=/root
```

`hostname` コマンドを実行してみます。

```
$ kubectl exec $POD_NAME hostname
kubernetes-bootcamp-390780338-6j8fn
```

`ip a` を実行してみます。

```
$ kubectl exec $POD_NAME ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host 
       valid_lft forever preferred_lft forever
11: eth0@if12: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default 
    link/ether 02:42:ac:11:00:04 brd ff:ff:ff:ff:ff:ff
    inet 172.17.0.4/16 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::42:acff:fe11:4/64 scope link tentative dadfailed 
       valid_lft forever preferred_lft forever
```

### Pod内でbash実行

以下のコマンドでbashを実行するとプロンプトが表示されます。

```
$ kubectl exec -ti $POD_NAME bash
root@kubernetes-bootcamp-390780338-6j8fn:/# 
```

チュートリアルのために用意されたkubernetes-bootcampアプリに含まれるファイル `server.js` の内容を表示してみます。このアプリは Node.js で書かれていることがわかります。

```
root@kubernetes-bootcamp-390780338-6j8fn:/# cat server.js
var http = require('http');
var requests=0;
var podname= process.env.HOSTNAME;
var startTime;
var host;
var handleRequest = function(request, response) {
  response.setHeader('Content-Type', 'text/plain');
  response.writeHead(200);
  response.write("Hello Kubernetes bootcamp! | Running on: ");
  response.write(host);
  response.end(" | v=1\n");
  console.log("Running On:" ,host, "| Total Requests:", ++requests,"| App Uptime:", (new Date() - startTime)/1000 , "seconds", "| Log Time:",new Date());
}
var www = http.createServer(handleRequest);
www.listen(8080,function () {
    startTime = new Date();;
    host = process.env.HOSTNAME;
    console.log ("Kubernetes Bootcamp App Started At:",startTime, "| Running On: " ,host, "\n" );
});
```

Pod内からcurlで直接アプリにアクセスしてみます。 Node.js コンテナ内でbashを実行しているのでホスト名には localhost を指定しています。

```
root@kubernetes-bootcamp-390780338-6j8fn:/# curl localhost:8080
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-390780338-6j8fn | v=1
```

`exit` を入力してPod内のbashを抜けます。

```
root@kubernetes-bootcamp-390780338-6j8fn:/# exit
exit
$ 
```

## Module 4: アプリをKubernetes外に公開する

概念の説明は [Services](https://kubernetesbootcamp.github.io/kubernetes-bootcamp/4-1.html) を参照してください。

Module 1では `minikube proxy` を実行してMacの8001番ポートでリッスンしておいて、Macから localhost:8001 でアクセスしました。

ここではKubernetesのノード上のポートでリッスンして、Macからminikubeのproxyを経由せずに直接アクセスします。

### サービス一覧表示

```
$ kubectl get services
NAME         CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
kubernetes   10.0.0.1     <none>        443/TCP   12h
```

### kubernetes-bootcampアプリを公開

```
$ kubectl expose deployment/kubernetes-bootcamp --type="NodePort" --port 8080
service "kubernetes-bootcamp" exposed
```

### 再度サービス一覧表示

```
$ kubectl get services
NAME                  CLUSTER-IP   EXTERNAL-IP   PORT(S)          AGE
kubernetes            10.0.0.1     <none>        443/TCP          12h
kubernetes-bootcamp   10.0.0.228   <nodes>       8080:31123/TCP   40s
```

上で `kubectl expose` コマンドでサービスを公開したので、一覧にkubernetes-bootcampが含まれるようになりました。

### サービス詳細表示

```
$ kubectl describe services/kubernetes-bootcamp
Name:                   kubernetes-bootcamp
Namespace:              default
Labels:                 run=kubernetes-bootcamp
Selector:               run=kubernetes-bootcamp
Type:                   NodePort
IP:                     10.0.0.228
Port:                   <unset> 8080/TCP
NodePort:               <unset> 31123/TCP
Endpoints:              172.17.0.4:8080
Session Affinity:       None
No events.
```

### ノードのポート取得

この後参照するため、ノードのポートを取得して環境変数 NODE_PORT に設定しておきます。

```
$ export NODE_PORT=$(kubectl get services/kubernetes-bootcamp -o go-template='{{(index .spec.ports 0).nodePort}}')
$ echo NODE_PORT=$NODE_PORT
NODE_PORT=31123
```

[Module 4のインタラクティブチュートリアル](https://kubernetesbootcamp.github.io/kubernetes-bootcamp/4-2.html)ではこの後 `curl host01:$NODE_PORT` でアクセスしているのですが、手元の環境では `host01` というホスト名ではアクセスできません。

そこで、以下のコマンドを実行してノードのIPアドレスを取得し、環境変数 NODE_IP に設定します。

```
$ export NODE_IP=$(minikube ip)
$ echo NODE_IP=$NODE_IP
NODE_IP=192.168.99.100
```

以下のコマンドでMacからKubernetesのノードに直接アクセスします。

```
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-390780338-6j8fn | v=1
```

Module 4のStep 2でラベルを付けて、Step 3でサービス削除するのですが、この記事を書く時は飛ばしてしまったので、Module 6の後に行います。

## Module 5: アプリをスケールアップする

概念の説明は [Running multiple instances of an app](https://kubernetesbootcamp.github.io/kubernetes-bootcamp/5-1.html) を参照してください。

### デプロイされたアプリのスケールアップ前のレプリカ数を確認

`kubectl get deployments` の結果にはデプロイごとにアプリのレプリカ（複製）の数が表示されます。

```
$ kubectl get deployments
NAME                  DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
kubernetes-bootcamp   1         1         1            1           46m
```

この結果ではPodの数は1です。

* DESIRED: デプロイ時に指定したレプリカ数。desireの意味は「切望する」なので、デプロイ時に希望した数ということでしょう。
* CURRENT: 現在実行中のレプリカ数。
* UP-TO-DATE: 指定した状態に更新されたレプリカ数。
* AVAILABLE: ユーザが利用可能な（＝ユーザに実際にサービスが提供されている）レプリカ数。

### スケールアップ

このデプロイのレプリカ数を4に増やしてみます。

```
$ kubectl scale deployments/kubernetes-bootcamp --replicas=4
deployment "kubernetes-bootcamp" scaled
```

デプロイ一覧で再度確認するとレプリカ数が4に増えていました。

```
$ kubectl get deployments
NAME                  DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
kubernetes-bootcamp   4         4         4            4           55m
```

Pod一覧を `-o wide` を指定して表示するとIPアドレスとノードを確認できます。

```
$ kubectl get pods -o wide
NAME                                  READY     STATUS    RESTARTS   AGE       IP           NODE
kubernetes-bootcamp-390780338-6j8fn   1/1       Running   0          55m       172.17.0.4   minikube
kubernetes-bootcamp-390780338-jw7cn   1/1       Running   0          7s        172.17.0.5   minikube
kubernetes-bootcamp-390780338-p8jbb   1/1       Running   0          7s        172.17.0.6   minikube
kubernetes-bootcamp-390780338-vq3kx   1/1       Running   0          7s        172.17.0.7   minikube
```

ちなみに `-o wide` 無しの出力結果は以下の通りです。

```
$ kubectl get pods
NAME                                  READY     STATUS    RESTARTS   AGE
kubernetes-bootcamp-390780338-6j8fn   1/1       Running   0          56m
kubernetes-bootcamp-390780338-jw7cn   1/1       Running   0          1m
kubernetes-bootcamp-390780338-p8jbb   1/1       Running   0          1m
kubernetes-bootcamp-390780338-vq3kx   1/1       Running   0          1m
```

### スケールアップ後のデプロイの詳細表示

Events欄にスケールアップした記録が残っています。

```
$ kubectl describe deployments/kubernetes-bootcamp
Name:                   kubernetes-bootcamp
Namespace:              default
CreationTimestamp:      Sat, 31 Dec 2016 17:15:41 +0900
Labels:                 run=kubernetes-bootcamp
Selector:               run=kubernetes-bootcamp
Replicas:               4 updated | 4 total | 4 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  1 max unavailable, 1 max surge
Conditions:
  Type          Status  Reason
  ----          ------  ------
  Available     True    MinimumReplicasAvailable
OldReplicaSets: <none>
NewReplicaSet:  kubernetes-bootcamp-390780338 (4/4 replicas created)
Events:
  FirstSeen     LastSeen        Count   From                            SubObjectPath   Type            Reason                  Message
  ---------     --------        -----   ----                            -------------   --------        ------                  -------
  58m           58m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled up replica set kubernetes-bootcamp-390780338 to 1
  3m            3m              1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled up replica set kubernetes-bootcamp-390780338 to 4
```

### スケールアップ後のアプリにcurlでアクセス

アクセスしてみるとリクエストごとにランダムなPodに振り分けられ、負荷分散されていることが確認できました。

```
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-390780338-6j8fn | v=1
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-390780338-6j8fn | v=1
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-390780338-jw7cn | v=1
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-390780338-p8jbb | v=1
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-390780338-6j8fn | v=1
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-390780338-6j8fn | v=1
```

### スケールダウン

レプリカ数を2に減らします。

```
$ kubectl scale deployments/kubernetes-bootcamp --replicas=2
deployment "kubernetes-bootcamp" scaled
```

デプロイ一覧で2に減ったことを確認しました。

```
$ kubectl get deployments
NAME                  DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
kubernetes-bootcamp   2         2         2            2           1h
```

直後のPod一覧では2つのコンテナのSTATUSがTerminating （終了中）となっていました。

```
$ kubectl get pods -o wide
NAME                                  READY     STATUS        RESTARTS   AGE       IP           NODE
kubernetes-bootcamp-390780338-6j8fn   1/1       Running       0          1h        172.17.0.4   minikube
kubernetes-bootcamp-390780338-jw7cn   1/1       Running       0          12m       172.17.0.5   minikube
kubernetes-bootcamp-390780338-p8jbb   1/1       Terminating   0          12m       172.17.0.6   minikube
kubernetes-bootcamp-390780338-vq3kx   1/1       Terminating   0          12m       172.17.0.7   minikube
```

数十秒程度してから再度Pod一覧を見るとSTATUSがRunningの2つだけになっていました。

```
$ kubectl get pods -o wide
NAME                                  READY     STATUS    RESTARTS   AGE       IP           NODE
kubernetes-bootcamp-390780338-6j8fn   1/1       Running   0          1h        172.17.0.4   minikube
kubernetes-bootcamp-390780338-jw7cn   1/1       Running   0          13m       172.17.0.5   minikube
```

## Module 6: アプリをローリングアップデート

概念の説明は [Performing a rolling update for an app](https://kubernetesbootcamp.github.io/kubernetes-bootcamp/6-1.html) を参照してください。

ローリングアップデートではアプリのダウンタイムをゼロでアプリを更新できるそうです。

### アップデート前の状態確認

Pod一覧。

```
$ kubectl get pods -o wide
NAME                                  READY     STATUS    RESTARTS   AGE       IP           NODE
kubernetes-bootcamp-390780338-6j8fn   1/1       Running   0          1h        172.17.0.4   minikube
kubernetes-bootcamp-390780338-jw7cn   1/1       Running   0          21m       172.17.0.5   minikube
```

Pod詳細情報。

```
$ kubectl describe pods
Name:           kubernetes-bootcamp-390780338-6j8fn
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 17:15:41 +0900
Labels:         pod-template-hash=390780338
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.4
Controllers:    ReplicaSet/kubernetes-bootcamp-390780338
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://f3d04d91e8f27b2b537c20d82253376993483f9bb9c0d1196ba50ecc3a69ff7c
    Image:              docker.io/jocatalin/kubernetes-bootcamp:v1
    Image ID:           docker://sha256:8fafd8af70e9aa7c3ab40222ca4fd58050cf3e49cb14a4e7c0f460cd4f78e9fe
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 17:15:42 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True
  Ready         True
  PodScheduled  True
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
No events.


Name:           kubernetes-bootcamp-390780338-jw7cn
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:10:47 +0900
Labels:         pod-template-hash=390780338
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.5
Controllers:    ReplicaSet/kubernetes-bootcamp-390780338
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://23e8c9c3c2b64701f88a61033b534a23f7f2e4a540afa019eea20050bfd12a39
    Image:              docker.io/jocatalin/kubernetes-bootcamp:v1
    Image ID:           docker://sha256:8fafd8af70e9aa7c3ab40222ca4fd58050cf3e49cb14a4e7c0f460cd4f78e9fe
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 18:10:48 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True
  Ready         True
  PodScheduled  True
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  21m           21m             1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-390780338-jw7cn to minikube
  21m           21m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "docker.io/jocatalin/kubernetes-bootcamp:v1" already present on machine
  21m           21m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id 23e8c9c3c2b6; Security:[seccomp=unconfined]
  21m           21m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id 23e8c9c3c2b6
```

### アプリのバージョンアップ

以下のコマンドでアプリをv1からv2にバージョンアップします。

```
$ kubectl set image deployments/kubernetes-bootcamp kubernetes-bootcamp=jocatalin/kubernetes-bootcamp:v2$ kubectl set image deployments/kubernetes-bootcamp kubernetes-bootcamp=jocatalin/kubernetes-bootcamp:v2
deployment "kubernetes-bootcamp" image updated
```

直後のPods一覧。

```
$ kubectl get pods -o wide
NAME                                   READY     STATUS        RESTARTS   AGE       IP           NODE
kubernetes-bootcamp-2100875782-0jd0d   1/1       Running       0          26s       172.17.0.6   minikube
kubernetes-bootcamp-2100875782-vnxk1   1/1       Running       0          26s       172.17.0.7   minikube
kubernetes-bootcamp-390780338-6j8fn    1/1       Terminating   0          1h        172.17.0.4   minikube
kubernetes-bootcamp-390780338-jw7cn    1/1       Terminating   0          24m       172.17.0.5   minikube
```

十秒程度したあとのPods一覧。

```
$ kubectl get pods -o wide
NAME                                   READY     STATUS    RESTARTS   AGE       IP           NODE
kubernetes-bootcamp-2100875782-0jd0d   1/1       Running   0          55s       172.17.0.6   minikube
kubernetes-bootcamp-2100875782-vnxk1   1/1       Running   0          55s       172.17.0.7   minikube
```

サービス詳細。

```

$ kubectl describe services/kubernetes-bootcamp
Name:                   kubernetes-bootcamp
Namespace:              default
Labels:                 run=kubernetes-bootcamp
Selector:               run=kubernetes-bootcamp
Type:                   NodePort
IP:                     10.0.0.228
Port:                   <unset> 8080/TCP
NodePort:               <unset> 31123/TCP
Endpoints:              172.17.0.6:8080,172.17.0.7:8080
Session Affinity:       None
No events.
```

### アップデート後のアプリにアクセス

curlでアクセスしてみると出力にv=2と表示され、アップデートされたアプリが利用可能になっていることが確認できました。

```
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-2100875782-0jd0d | v=2
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-2100875782-0jd0d | v=2
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-2100875782-vnxk1 | v=2
```

### ローリングアップデート後の状態確認

ローリングアップデートの状態確認。

```
$ kubectl rollout status deployments/kubernetes-bootcamp
deployment "kubernetes-bootcamp" successfully rolled out
```

Pod詳細表示。Imageの値が `jocatalin/kubernetes-bootcamp:v2` と v2になっていることが確認できます。

```
$ kubectl describe pods
Name:           kubernetes-bootcamp-2100875782-0jd0d
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:34:57 +0900
Labels:         pod-template-hash=2100875782
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.6
Controllers:    ReplicaSet/kubernetes-bootcamp-2100875782
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://7438b24d95242018dae9b4e82b93055d772f14650c688203b80204073d67d84b
    Image:              jocatalin/kubernetes-bootcamp:v2
    Image ID:           docker://sha256:b6556396ebd45c517469c522c3c61ecf5ab708cafe0e59df906278d34c255ef8
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 18:34:58 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         True 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  5m            5m              1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-2100875782-0jd0d to minikube
  5m            5m              1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "jocatalin/kubernetes-bootcamp:v2" already present on machine
  5m            5m              1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id 7438b24d9524; Security:[seccomp=unconfined]
  5m            5m              1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id 7438b24d9524


Name:           kubernetes-bootcamp-2100875782-vnxk1
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:34:57 +0900
Labels:         pod-template-hash=2100875782
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.7
Controllers:    ReplicaSet/kubernetes-bootcamp-2100875782
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://54c58841abb18466fb0f79636111ef5ff193226f43a5741d1730efeb4689ba58
    Image:              jocatalin/kubernetes-bootcamp:v2
    Image ID:           docker://sha256:b6556396ebd45c517469c522c3c61ecf5ab708cafe0e59df906278d34c255ef8
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 18:34:58 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         True 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  5m            5m              1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-2100875782-vnxk1 to minikube
  5m            5m              1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "jocatalin/kubernetes-bootcamp:v2" already present on machine
  5m            5m              1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id 54c58841abb1; Security:[seccomp=unconfined]
  5m            5m              1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id 54c58841abb1
```

### アプリのバージョンアップ失敗の例

#### 存在しないタグのイメージにアップデート

次はv10とタグ付けされたイメージにアップデートを試みます。

```
$ kubectl set image deployments/kubernetes-bootcamp kubernetes-bootcamp=jocatalin/kubernetes-bootcamp:v10
deployment "kubernetes-bootcamp" image updated
```

問題なくアップデートされたように見えますが、実はv10というタグのイメージは存在しないのでエラーになります。

デプロイ一覧のレプリカ数を見ると、DESIREDが2に対してAVAILABLEが1であり希望した状態になっていないことがわかります。

```
$ kubectl get deployments
NAME                  DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
kubernetes-bootcamp   2         3         2            1           1h
```

Pods一覧を見ると一部のPodはSTATUSがImagePullBackOffとなっています。

```
$ kubectl get pods -o wide
NAME                                   READY     STATUS             RESTARTS   AGE       IP           NODE
kubernetes-bootcamp-1951388213-lpc3k   0/1       ImagePullBackOff   0          26s       172.17.0.4   minikube
kubernetes-bootcamp-1951388213-mwx9v   0/1       ImagePullBackOff   0          25s       172.17.0.5   minikube
kubernetes-bootcamp-2100875782-0jd0d   1/1       Terminating        0          10m       172.17.0.6   minikube
kubernetes-bootcamp-2100875782-vnxk1   1/1       Running            0          10m       172.17.0.7   minikube
```

間を置いて何度か試していると、STATUSがErrImagePullとなっているときもありました。

```
$ kubectl get pods -o wide
NAME                                   READY     STATUS             RESTARTS   AGE       IP           NODE
kubernetes-bootcamp-1951388213-lpc3k   0/1       ImagePullBackOff   0          1m        172.17.0.4   minikube
kubernetes-bootcamp-1951388213-mwx9v   0/1       ErrImagePull       0          1m        172.17.0.5   minikube
kubernetes-bootcamp-2100875782-vnxk1   1/1       Running            0          11m       172.17.0.7   minikube
```

Pod詳細。
Imageの値が `jocatalin/kubernetes-bootcamp:v10` であるコンテナのEventsを見ると
`Failed to pull image "jocatalin/kubernetes-bootcamp:v10": Tag v10 not found in repository docker.io/jocatalin/kubernetes-bootcamp` というエラーがあり、タグv10はレジストリに無かったことがわかります。

```
$ kubectl describe pods
Name:           kubernetes-bootcamp-1951388213-lpc3k
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:44:43 +0900
Labels:         pod-template-hash=1951388213
                run=kubernetes-bootcamp
Status:         Pending
IP:             172.17.0.4
Controllers:    ReplicaSet/kubernetes-bootcamp-1951388213
Containers:
  kubernetes-bootcamp:
    Container ID:
    Image:              jocatalin/kubernetes-bootcamp:v10
    Image ID:
    Port:               8080/TCP
    State:              Waiting
      Reason:           ImagePullBackOff
    Ready:              False
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         False 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  6m            6m              1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-1951388213-lpc3k to minikube
  6m            36s             6       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulling         pulling image "jocatalin/kubernetes-bootcamp:v10"
  6m            30s             6       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Warning         Failed          Failed to pull image "jocatalin/kubernetes-bootcamp:v10": Tag v10 not found in repository docker.io/jocatalin/kubernetes-bootcamp
  6m            30s             6       {kubelet minikube}                                              Warning         FailedSync      Error syncing pod, skipping: failed to "StartContainer" for "kubernetes-bootcamp" with ErrImagePull: "Tag v10 not found in reposit
ory docker.io/jocatalin/kubernetes-bootcamp"

  6m    2s      22      {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal  BackOff         Back-off pulling image "jocatalin/kubernetes-bootcamp:v10"
  6m    2s      22      {kubelet minikube}                                              Warning FailedSync      Error syncing pod, skipping: failed to "StartContainer" for "kubernetes-bootcamp" with ImagePullBackOff: "Back-off pulling image \"jocatalin/kubernetes-bo
otcamp:v10\""



Name:           kubernetes-bootcamp-1951388213-mwx9v
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:44:44 +0900
Labels:         pod-template-hash=1951388213
                run=kubernetes-bootcamp
Status:         Pending
IP:             172.17.0.5
Controllers:    ReplicaSet/kubernetes-bootcamp-1951388213
Containers:
  kubernetes-bootcamp:
    Container ID:
    Image:              jocatalin/kubernetes-bootcamp:v10
    Image ID:
    Port:               8080/TCP
    State:              Waiting
      Reason:           ImagePullBackOff
    Ready:              False
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         False 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  6m            6m              1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-1951388213-mwx9v to minikube
  6m            2m              5       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulling         pulling image "jocatalin/kubernetes-bootcamp:v10"
  6m            2m              5       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Warning         Failed          Failed to pull image "jocatalin/kubernetes-bootcamp:v10": Tag v10 not found in repository docker.io/jocatalin/kubernetes-bootcamp
  6m            2m              5       {kubelet minikube}                                              Warning         FailedSync      Error syncing pod, skipping: failed to "StartContainer" for "kubernetes-bootcamp" with ErrImagePull: "Tag v10 not found in repository docker.io/jocatalin/kubernetes-bootcamp"

  6m    14s     23      {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal  BackOff         Back-off pulling image "jocatalin/kubernetes-bootcamp:v10"
  6m    14s     23      {kubelet minikube}                                              Warning FailedSync      Error syncing pod, skipping: failed to "StartContainer" for "kubernetes-bootcamp" with ImagePullBackOff: "Back-off pulling image \"jocatalin/kubernetes-bootcamp:v10\""



Name:           kubernetes-bootcamp-2100875782-vnxk1
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:34:57 +0900
Labels:         pod-template-hash=2100875782
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.7
Controllers:    ReplicaSet/kubernetes-bootcamp-2100875782
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://54c58841abb18466fb0f79636111ef5ff193226f43a5741d1730efeb4689ba58
    Image:              jocatalin/kubernetes-bootcamp:v2
    Image ID:           docker://sha256:b6556396ebd45c517469c522c3c61ecf5ab708cafe0e59df906278d34c255ef8
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 18:34:58 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         True 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  16m           16m             1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-2100875782-vnxk1 to minikube
  16m           16m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "jocatalin/kubernetes-bootcamp:v2" already present on machine
  16m           16m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id 54c58841abb1; Security:[seccomp=unconfined]
  16m           16m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id 54c58841abb1
```

#### v10へのローリングアップデートを中止

ローリングアップデートをアンドゥします。

```
$ kubectl rollout undo deployments/kubernetes-bootcamp$ kubectl rollout undo deployments/kubernetes-bootcamp
deployment "kubernetes-bootcamp" rolled back
```

Pod一覧。

```
$ kubectl get pods -o wide
NAME                                   READY     STATUS    RESTARTS   AGE       IP           NODE
kubernetes-bootcamp-2100875782-vnxk1   1/1       Running   0          20m       172.17.0.7   minikube
kubernetes-bootcamp-2100875782-x290l   1/1       Running   0          17s       172.17.0.4   minikube
```

Pod詳細。

Podのレプリカ数は以前指定した2で、2つのPodともImageが `jocatalin/kubernetes-bootcamp:v2` とアップデート前のバージョンに戻ったことが確認できました。

```
$ 
kubectl describe pods$ kubectl describe pods
Name:           kubernetes-bootcamp-2100875782-vnxk1
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:34:57 +0900
Labels:         pod-template-hash=2100875782
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.7
Controllers:    ReplicaSet/kubernetes-bootcamp-2100875782
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://54c58841abb18466fb0f79636111ef5ff193226f43a5741d1730efeb4689ba58
    Image:              jocatalin/kubernetes-bootcamp:v2
    Image ID:           docker://sha256:b6556396ebd45c517469c522c3c61ecf5ab708cafe0e59df906278d34c255ef8
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 18:34:58 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         True 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  21m           21m             1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-2100875782-vnxk1 to minikube
  21m           21m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "jocatalin/kubernetes-bootcamp:v2" already present on machine
  21m           21m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id 54c58841abb1; Security:[seccomp=unconfined]
  21m           21m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id 54c58841abb1


Name:           kubernetes-bootcamp-2100875782-x290l
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:55:31 +0900
Labels:         pod-template-hash=2100875782
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.4
Controllers:    ReplicaSet/kubernetes-bootcamp-2100875782
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://523dca2d5839e832942af50d52fe8008c16862c19ebed553e50293765f4cf12c
    Image:              jocatalin/kubernetes-bootcamp:v2
    Image ID:           docker://sha256:b6556396ebd45c517469c522c3c61ecf5ab708cafe0e59df906278d34c255ef8
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 18:55:32 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         True 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  21m           21m             1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-2100875782-vnxk1 to minikube
  21m           21m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "jocatalin/kubernetes-bootcamp:v2" already present on machine
  21m           21m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id 54c58841abb1; Security:[seccomp=unconfined]
  21m           21m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id 54c58841abb1


Name:           kubernetes-bootcamp-2100875782-x290l
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:55:31 +0900
Labels:         pod-template-hash=2100875782
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.4
Controllers:    ReplicaSet/kubernetes-bootcamp-2100875782
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://523dca2d5839e832942af50d52fe8008c16862c19ebed553e50293765f4cf12c
    Image:              jocatalin/kubernetes-bootcamp:v2
    Image ID:           docker://sha256:b6556396ebd45c517469c522c3c61ecf5ab708cafe0e59df906278d34c255ef8
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 18:55:32 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         True 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  1m            1m              1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-2100875782-x290l to minikube
  1m            1m              1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "jocatalin/kubernetes-bootcamp:v2" already present on machine
  1m            1m              1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id 523dca2d5839; Security:[seccomp=unconfined]
  1m            1m              1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id 523dca2d5839
```

curlでアクセスしてみても v2 と表示されています。

```
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-2100875782-vnxk1 | v=2
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-2100875782-vnxk1 | v=2
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-2100875782-x290l | v=2
$ curl $NODE_IP:$NODE_PORT
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-2100875782-x290l | v=2
```

## Module 4のStep 2: ラベルを付ける

デプロイの詳細表示。
Labelsにrun=kubernetes-bootcampというのがデフォルトで付いていることがわかります。

```
$ kubectl describe deployment
Name:                   kubernetes-bootcamp
Namespace:              default
CreationTimestamp:      Sat, 31 Dec 2016 17:15:41 +0900
Labels:                 run=kubernetes-bootcamp
Selector:               run=kubernetes-bootcamp
Replicas:               2 updated | 2 total | 2 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  1 max unavailable, 1 max surge
Conditions:
  Type          Status  Reason
  ----          ------  ------
  Available     True    MinimumReplicasAvailable
OldReplicaSets: <none>
NewReplicaSet:  kubernetes-bootcamp-2100875782 (2/2 replicas created)
Events:
  FirstSeen     LastSeen        Count   From                            SubObjectPath   Type            Reason                  Message
  ---------     --------        -----   ----                            -------------   --------        ------                  -------
  55m           55m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled up replica set kubernetes-bootcamp-390780338 to 4
  43m           43m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled down replica set kubernetes-bootcamp-390780338 to 2
  31m           31m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled up replica set kubernetes-bootcamp-2100875782 to 1
  31m           31m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled down replica set kubernetes-bootcamp-390780338 to 1
  31m           31m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled down replica set kubernetes-bootcamp-390780338 to 0
  21m           21m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled up replica set kubernetes-bootcamp-1951388213 to 1
  21m           21m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled down replica set kubernetes-bootcamp-2100875782 to 1
  21m           21m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled up replica set kubernetes-bootcamp-1951388213 to 2
  31m           11m             2       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled up replica set kubernetes-bootcamp-2100875782 to 2
  11m           11m             1       {deployment-controller }                        Normal          DeploymentRollback      Rolled back deployment "kubernetes-bootcamp" to revision 2
  11m           11m             1       {deployment-controller }                        Normal          ScalingReplicaSet       Scaled down replica set kubernetes-bootcamp-1951388213 to 0
```

指定したラベルを持つPods一覧表示。

```
$ kubectl get pods -l run=kubernetes-bootcamp
NAME                                   READY     STATUS    RESTARTS   AGE
kubernetes-bootcamp-2100875782-vnxk1   1/1       Running   0          32m
kubernetes-bootcamp-2100875782-x290l   1/1       Running   0          11m
```

指定したラベルを持つサービス一覧表示。

```
$ kubectl get services -l run=kubernetes-bootcamp
NAME                  CLUSTER-IP   EXTERNAL-IP   PORT(S)          AGE
kubernetes-bootcamp   10.0.0.228   <nodes>       8080:31123/TCP   1h
```

Pod名を取得して環境変数POD_NAMEに設定。

```
$ export POD_NAME=$(kubectl get pods -o go-template --template '{{range .items}}{{.metadata.name}}{{"\n"}}{{end}}')
$ echo Name of the Pod: $POD_NAME
Name of the Pod: kubernetes-bootcamp-2100875782-vnxk1
```

Podにapp=v2というラベルを設定。チュートリアルではapp=v1というラベルを指定していますが、この記事ではバージョンアップ後に実行しているのでapp=v2にします。

```
$ kubectl label pod $POD_NAME app=v2
pod "kubernetes-bootcamp-2100875782-vnxk1" labeled
pod "kubernetes-bootcamp-2100875782-x290l" labeled
```

Pod詳細表示。
Labelsにapp=v2が付いています。

```
kubectl describe pods $POD_NAME
Name:           kubernetes-bootcamp-2100875782-vnxk1
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:34:57 +0900
Labels:         app=v2
                pod-template-hash=2100875782
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.7
Controllers:    ReplicaSet/kubernetes-bootcamp-2100875782
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://54c58841abb18466fb0f79636111ef5ff193226f43a5741d1730efeb4689ba58
    Image:              jocatalin/kubernetes-bootcamp:v2
    Image ID:           docker://sha256:b6556396ebd45c517469c522c3c61ecf5ab708cafe0e59df906278d34c255ef8
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 18:34:58 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         True 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  36m           36m             1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-2100875782-vnxk1 to minikube
  36m           36m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "jocatalin/kubernetes-bootcamp:v2" already present on machine
  36m           36m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id 54c58841abb1; Security:[seccomp=unconfined]
  36m           36m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id 54c58841abb1


Name:           kubernetes-bootcamp-2100875782-x290l
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sat, 31 Dec 2016 18:55:31 +0900
Labels:         app=v2
                pod-template-hash=2100875782
                run=kubernetes-bootcamp
Status:         Running
IP:             172.17.0.4
Controllers:    ReplicaSet/kubernetes-bootcamp-2100875782
Containers:
  kubernetes-bootcamp:
    Container ID:       docker://523dca2d5839e832942af50d52fe8008c16862c19ebed553e50293765f4cf12c
    Image:              jocatalin/kubernetes-bootcamp:v2
    Image ID:           docker://sha256:b6556396ebd45c517469c522c3c61ecf5ab708cafe0e59df906278d34c255ef8
    Port:               8080/TCP
    State:              Running
      Started:          Sat, 31 Dec 2016 18:55:32 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:      <none>
Conditions:
  Type          Status
  Initialized   True 
  Ready         True 
  PodScheduled  True 
Volumes:
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath                           Type            Reason          Message
  ---------     --------        -----   ----                    -------------                           --------        ------          -------
  15m           15m             1       {default-scheduler }                                            Normal          Scheduled       Successfully assigned kubernetes-bootcamp-2100875782-x290l to minikube
  15m           15m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Pulled          Container image "jocatalin/kubernetes-bootcamp:v2" already present on machine
  15m           15m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Created         Created container with docker id 523dca2d5839; Security:[seccomp=unconfined]
  15m           15m             1       {kubelet minikube}      spec.containers{kubernetes-bootcamp}    Normal          Started         Started container with docker id 523dca2d5839
```

今つけたラベルを持つPod一覧表示。

```
$ kubectl get pods -l app=v2
NAME                                   READY     STATUS    RESTARTS   AGE
kubernetes-bootcamp-2100875782-vnxk1   1/1       Running   0          40m
kubernetes-bootcamp-2100875782-x290l   1/1       Running   0          19m
```

## Module 4のStep 3: サービスを削除

```
$ kubectl delete service -l run=kubernetes-bootcamp
service "kubernetes-bootcamp" deleted
```

サービス一覧を確認すると kubernetes-bootcamp が消えていることがわかります。

```
$ kubectl get services
NAME         CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE
kubernetes   10.0.0.1     <none>        443/TCP   13h
```

curlでアクセスすると接続拒否という期待される結果になりました。

```
$ curl $NODE_IP:$NODE_PORT
curl: (7) Failed to connect to 192.168.99.100 port 31123: Connection refused
```

Pod一覧を見るとPod自体は存在します。

```
$ kubectl get pods
NAME                                   READY     STATUS    RESTARTS   AGE
kubernetes-bootcamp-2100875782-vnxk1   1/1       Running   0          40m
kubernetes-bootcamp-2100875782-x290l   1/1       Running   0          19m
```

Podに入ってアクセスするとアプリ自体は引き続き稼働中であることがわかります。

```
$ export POD_NAME=kubernetes-bootcamp-2100875782-vnxk1
$ kubectl exec -ti $POD_NAME curl localhost:8080
Hello Kubernetes bootcamp! | Running on: kubernetes-bootcamp-2100875782-vnxk1 | v=2
```
