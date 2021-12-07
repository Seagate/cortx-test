#!/bin/bash
yum install gcc pcre-devel tar make -y
yum install openssl-devel pcre-devel -y

yum-config-manager --add-repo http://cortx-storage.colo.seagate.com/releases/cortx/third-party-deps/centos/centos-7.9.2009-2.0.0-k8/commons/haproxy-packages/
yum install haproxy22 --nogpgcheck -y

#sudo mkdir -p /etc/haproxy
sudo mkdir -p /var/lib/haproxy
sudo touch /var/lib/haproxy/stats
# sudo ln -s /usr/local/sbin/haproxy /usr/sbin/haproxy
# sudo cp ~/haproxy-2.4.2/examples/haproxy.init /etc/init.d/haproxy
# sudo chmod 755 /etc/init.d/haproxy
# sudo systemctl daemon-reload
sudo useradd -r haproxy
haproxy -v
systemctl stop firewalld
sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
puppet agent --disable
