Title: daemontoolsのインストール手順
Date: 2012-06-21 00:00
Category: blog
Tags: daemontools, centos
Slug: 2012/06/21/how-to-install-daemontools

CentOS6.2で確認。

OS起動時にdaemontoolsを起動する設定は[How to start daemontools](http://cr.yp.to/daemontools/start.html)を参照。

```
yum install -y make gcc rpm-build &&
rpm -ivh http://mirrors.qmailtoaster.com/daemontools-toaster-0.76-1.3.6.src.rpm &&
rpmbuild -ba /root/rpmbuild/SPECS/daemontools-toaster.spec &&
rpm -ivh /root/rpmbuild/RPMS/x86_64/daemontools-toaster-0.76-1.3.6.x86_64.rpm &&
cat > /etc/init/svscan.conf <<EOF &&
start on runlevel [12345]
stop on runlevel [^12345]
respawn
exec /command/svscanboot
EOF
/command/svscanboot &
```
