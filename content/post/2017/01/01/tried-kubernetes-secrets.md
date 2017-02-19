Title: KubernetesのSecrets機能を試してみた
Date: 2017-01-01 16:31
Category: blog
Tags: kubernetes
Slug: blog/2017/01/01/tried-kubernetes-secrets

## はじめに
[Running a Single-Instance Stateful Application - Kubernetes](http://kubernetes.io/docs/tutorials/stateful-application/run-stateful-application/) ではMySQLのrootユーザのパスワードを設定のyamlファイルに直接書いていましたが、 安全に管理するためには[Secrets - Kubernetes](http://kubernetes.io/docs/user-guide/secrets/) を使うべきとのことなので試してみました。

## パスワードをsecretとして作成

[Secrets - Kubernetes](http://kubernetes.io/docs/user-guide/secrets/) ではユーザ名とパスワードを作っていますが、ここではrootユーザのパスワードだけにしてみました。

以下のような内容でmysql-secrets.ymlというファイルを作成します。

```
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
type: Opaque
data:
  rootPassword: MWYyZDFlMmU2N2Rm
```

data.rootPasswordの値は指定したいパスワードをbase64エンコードした値を書いています。

```
$ echo -n "1f2d1e2e67df" | base64
MWYyZDFlMmU2N2Rm
```

以下のコマンドでsecretを作成します。

```
$ k create -f mysql-secrets.yml
secret "mysql-secret" created
```

## 作成したsecretを確認

```
$ kubectl get secrets mysql-secret -o yaml
apiVersion: v1
data:
  rootPassword: MWYyZDFlMmU2N2Rm
kind: Secret
metadata:
  creationTimestamp: 2017-01-01T07:56:48Z
  name: mysql-secret
  namespace: default
  resourceVersion: "70478"
  selfLink: /api/v1/namespaces/default/secrets/mysql-secret
  uid: d8fe8b5f-cff7-11e6-8be9-aece81f30d69
type: Opaque
```

## secretをPodから利用する

[Kuberntesでデータ領域をNFSマウントしてMySQLを動かしてみた · hnakamur's blog at github](/blog/2017/01/01/tried-mysql-and-nfs-on-kubernetes/)のmysql-deploy.ymlを以下のように変更しました。

```
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
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: rootPassword
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

serviceとdeployを一旦削除し、mac上のデータディレクトリも一旦消してから、イカのコマンドで作り直しました。

```
$ kubectl create -f mysql-deploy.yml
deployment "mysql" created
$ kubectl create -f mysql-svc.yml
service "mysql" created
```

## 作成したPodの詳細情報を確認

```
$ kubectl describe po -l app=mysql
Name:           mysql-1289358488-80g5n
Namespace:      default
Node:           minikube/192.168.99.100
Start Time:     Sun, 01 Jan 2017 17:07:51 +0900
Labels:         app=mysql
                pod-template-hash=1289358488
                ver=5.6
Status:         Running
IP:             172.17.0.5
Controllers:    ReplicaSet/mysql-1289358488
Containers:
  mysql:
    Container ID:       docker://928c7f98bdc8241830ec564d3fb31656647bc2c1e020b257bb1364de1d4e9435
    Image:              mysql:5.6
    Image ID:           docker://sha256:e1406e1f7c42c7e664e138c2cedfcd4c09eef6d4859df1f93fd54d87ed3ba1a1
    Port:               3306/TCP
    State:              Running
      Started:          Sun, 01 Jan 2017 17:07:52 +0900
    Ready:              True
    Restart Count:      0
    Volume Mounts:
      /var/lib/mysql from mysql-persistent-storage (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-qqsb7 (ro)
    Environment Variables:
      MYSQL_ROOT_PASSWORD:      <set to the key 'rootPassword' in secret 'mysql-secret'>
Conditions:
  Type          Status
  Initialized   True
  Ready         True
  PodScheduled  True
Volumes:
  mysql-persistent-storage:
    Type:       PersistentVolumeClaim (a reference to a PersistentVolumeClaim in the same namespace)
    ClaimName:  mysql-pvc
    ReadOnly:   false
  default-token-qqsb7:
    Type:       Secret (a volume populated by a Secret)
    SecretName: default-token-qqsb7
QoS Class:      BestEffort
Tolerations:    <none>
Events:
  FirstSeen     LastSeen        Count   From                    SubObjectPath           Type            Reason          Message
  ---------     --------        -----   ----                    -------------           --------        ------          -------
  1m            1m              1       {default-scheduler }                            Normal          Scheduled       Successfully as
signed mysql-1289358488-80g5n to minikube
  1m            1m              1       {kubelet minikube}      spec.containers{mysql}  Normal          Pulled          Container image
 "mysql:5.6" already present on machine
  1m            1m              1       {kubelet minikube}      spec.containers{mysql}  Normal          Created         Created contain
er with docker id 928c7f98bdc8; Security:[seccomp=unconfined]
  1m            1m              1       {kubelet minikube}      spec.containers{mysql}  Normal          Started         Started contain
er with docker id 928c7f98bdc8
```

MYSQL_ROOT_PASSWORDの説明が `<set to the key 'rootPassword' in secret 'mysql-secret'>` となっていて問題なく使えているようです。

### mysqlクライアントで接続

mysqlのクライアントで指定したパスワードで接続できることが確認できました。

```
$ kubectl run -it --rm --image=mysql:5.6 mysql-client -- mysql -h 172.17.0.5 -p1f2d1e2e67df
Waiting for pod default/mysql-client-992258208-c9wm3 to be running, status is Pending, pod ready: false
If you don't see a command prompt, try pressing enter.

mysql> create database db1;
Query OK, 1 row affected (0.01 sec)

mysql> exit
Bye
Session ended, resume using 'kubectl attach mysql-client-992258208-c9wm3 -c mysql-client -i -t' command when the pod is running
deployment "mysql-client" deleted
```
