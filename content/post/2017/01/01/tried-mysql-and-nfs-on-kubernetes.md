Title: Kuberntesでデータ領域をNFSマウントしてMySQLを動かしてみた
Date: 2017-01-01 12:38
Category: blog
Tags: kubernetes
Slug: 2017/01/01/tried-mysql-and-nfs-on-kubernetes

## はじめに

[minikubeとVirtualBoxでNFSのpersistent volumeを試してみた · hnakamur's blog at github](/blog/2017/01/01/use-nfs-persistent-volume-on-minikube-virtualbox/)の結果を踏まえて、 [Running a Single-Instance Stateful Application - Kubernetes](http://kubernetes.io/docs/tutorials/stateful-application/run-stateful-application/) のチュートリアルを試してみたのでメモです。

## 設定ファイル

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
    path: /Users/hnakamur/kube-data/mysql
    server: 192.168.99.1
```

```
$ cat mysql-pvc.yml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: mysql-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 15Gi
```

```
$ cat mysql-deploy.yml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: mysql
spec:
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - image: mysql:5.6
        name: mysql
        env:
          # Use secret in real usage
        - name: MYSQL_ROOT_PASSWORD
          value: password
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: mysql-persistent-storage
          mountPath: /var/lib/mysql
      volumes:
      - name: mysql-persistent-storage
        persistentVolumeClaim:
          claimName: mysql-pvc
```

```
$ cat mysql-svc.yml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  ports:
    - port: 3306
  selector:
    app: mysql
  clusterIP: None
```

ハマった点としては、persistent volumeとpersistent volume claimのaccessModesは合わせないとうまく行きませんでした。具体的には `kubectl describe pvc mysql-pvc` で確認したときにStatusがPendingになっていました。

[Access Modes](http://kubernetes.io/docs/user-guide/persistent-volumes/#access-modes)にアクセスモードについての説明があります。

## サービスの作成と公開

```
kubectl create -f persistent-volume-nfs.yml
kubectl create -f mysql-pvc.yml
kubectl create -f mysql-deploy.yml
kubectl create -f mysql-svc.yml
```

## MySQLに接続してみる

まずMySQLコンテナのIPアドレスを調べます。

```
$ kubectl get pods -o wide -l app=mysql
NAME                     READY     STATUS    RESTARTS   AGE       IP           NODE
mysql-4160924354-c5x2l   1/1       Running   0          3m        172.17.0.5   minikube
```

mysqlクライアントのイメージを使ってmysqlに接続します。
`If you don't see a command prompt, try pressing enter.` とある通り、そのままではプロンプトが表示されなかったのでエンターキーを押すと表示されました。

試しにデータベースをテーブルを作成してみます。その後 Control-D を押してmysqlクライアントを抜けます。

```
$ kubectl run -it --rm --image=mysql:5.6 mysql-client -- mysql -h 172.17.0.5 -ppassword
Waiting for pod default/mysql-client-1703061864-g1p4s to be running, status is Pending, pod ready: false
If you don't see a command prompt, try pressing enter.

mysql> create database test1;
Query OK, 1 row affected (0.00 sec)

mysql> use test1;
Database changed
mysql> create table table1 (id integer);
Query OK, 0 rows affected (0.02 sec)

mysql> ^DBye
Session ended, resume using 'kubectl attach mysql-client-1703061864-g1p4s -c mysql-client -i -t' command when the pod is running
deployment "mysql-client" deleted
```

## MySQLサーバのPodを更新してみる

mysql-deploy.yml を書き変えて `kubectl apply` で更新してみます。

最初MYSQL_ROOT_PASSWORDの値を変えてみようかと思って試したのですが、よく考えるとこれはデータベース作成時に設定されてNFSでマウントしたデータ領域はそのまま残るので、この値を変えても更新できませんでした。

そこで、ラベルに `ver=5.6` というのを追加してみました。
最初5.6はダブルクォートで囲まずにyamlファイルに書いてみたのですが、エラーになったのでダブルクォートで囲んでいます。

```
$ cat mysql-deploy.yml
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: mysql
spec:
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app: mysql
        ver: "5.6"
    spec:
      containers:
      - image: mysql:5.6
        name: mysql
        env:
          # Use secret in real usage
        - name: MYSQL_ROOT_PASSWORD
          value: password
        ports:
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: mysql-persistent-storage
          mountPath: /var/lib/mysql
      volumes:
      - name: mysql-persistent-storage
        persistentVolumeClaim:
          claimName: mysql-pvc
```

以下のコマンドで反映しました。

```
kubectl apply -f mysql-deploy.yml
```

再度mysqlに接続して、先ほど作成したデータベースとテーブルがあるかを確認します。

まずMySQLコンテナのIPアドレスを調べます。
spec.strategyがRecreateなので、コンテナが作り直されてIPアドレスも先程とは変わっています。

```
$ kubectl get pods -o wide -l app=mysql
NAME                     READY     STATUS    RESTARTS   AGE       IP           NODE
mysql-1726459224-c5gps   1/1       Running   0          10s       172.17.0.6   minikube
```

`kubectl describe po -l app=mysql` を実行してStateのStartedやEventsの時刻を見るとコンテナが作り直されたことがわかります。

mysqlに接続して、データベースとテーブルを確認します。

```
$ kubectl run -it --rm --image=mysql:5.6 mysql-client -- mysql -h 172.17.0.6 -pmypassword
Waiting for pod default/mysql-client-1775806825-vxjgf to be running, status is Pending, pod ready: false
If you don't see a command prompt, try pressing enter.

mysql> show databases;
+--------------------+
| Database           |
+--------------------+
| information_schema |
| mysql              |
| performance_schema |
| test1              |
+--------------------+
4 rows in set (0.01 sec)

mysql> use test1;
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A

Database changed
mysql> show tables;
+-----------------+
| Tables_in_test1 |
+-----------------+
| table1          |
+-----------------+
1 row in set (0.00 sec)

mysql> exit
Bye
Session ended, resume using 'kubectl attach mysql-client-1775806825-vxjgf -c mysql-client -i -t' command when the pod is running
deployment "mysql-client" deleted
```
