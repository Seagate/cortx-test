#!/bin/bash
yum install gcc pcre-devel tar make -y
yum install openssl-devel pcre-devel -y
wget http://www.haproxy.org/download/2.4/src/haproxy-2.4.2.tar.gz
tar xzvf ~/haproxy-2.4.2.tar.gz -C ~/
cd haproxy-2.4.2/
make TARGET=linux-glibc USE_PCRE=1 USE_OPENSSL=1 USE_ZLIB=1 USE_CRYPT_H=1 USE_LIBCRYPT=1 # This set of flags is needed to support SSL requests
make install

sudo mkdir -p /etc/haproxy
sudo mkdir -p /var/lib/haproxy
sudo touch /var/lib/haproxy/stats
sudo ln -s /usr/local/sbin/haproxy /usr/sbin/haproxy
sudo cp ~/haproxy-2.4.2/examples/haproxy.init /etc/init.d/haproxy
sudo chmod 755 /etc/init.d/haproxy
sudo systemctl daemon-reload
sudo useradd -r haproxy
systemctl stop firewalld
sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
puppet agent --disable
