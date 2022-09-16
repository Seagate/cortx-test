#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

# This file will install & configure s3 tools.
# Commands:
#	1. make help # To check supported tools by this script.
#	2. make install-tools ACCESS="xyz" SECRET="abc" # Install all tools.
#	3. make aws ACCESS="xyz" SECRET="abc"  # Install specific tools from help.
# Note: Please provide existing s3account user access, secret key through command line.

ACCESS=None
SECRET=None
ENDPOINT=s3.seagate.com
VERIFY_SSL=True
VALIDATE_CERTS=True
CA_CRT=/etc/ssl/stx-s3-clients/s3/ca.crt
NFS_SHARE=cftic2.pun.seagate.com:/cftshare/jclientCloud/
APACHE_J_METER=apache-jmeter-5.5.tgz

ifeq ($(VERIFY_SSL), True)
   ssl=--ssl
   endpoint=https://$(ENDPOINT)
   iam_port=9443
else
   ssl=--no-ssl
   endpoint=http://$(ENDPOINT)
   iam_port=9080
endif

ifeq ($(VALIDATE_CERTS), True)
   certificate=--check-certificate
else
   certificate=--no-check-certificate
endif

aws-install:

	@echo "### Install awscli. ###"
	pip3 install awscli
	pip3 install awscli-plugin-endpoint
	@echo "### Installed awscli. ###"


aws-configure:

	@echo "### configure awscli. ###"
	@echo "Server certificate should be exists at /etc/ssl/stx-s3-clients/s3/"
	aws configure set plugins.endpoint awscli_plugin_endpoint
	aws configure set s3.endpoint_url $(endpoint)
	aws configure set s3api.endpoint_url $(endpoint)
	aws configure set iam.endpoint_url $(endpoint):$(iam_port)
	aws configure set default.ca_bundle $(CA_CRT)
	aws configure set aws_access_key_id $(ACCESS)
	aws configure set aws_secret_access_key $(SECRET)
	aws configure set region "US"
	aws configure set output "json"
	@echo "### configured awscli. ###"

aws-configure-rgw:

	@echo "### configure awscli. ###"
	@echo "Server certificate should be exists at /etc/ssl/stx-s3-clients/s3/"
	aws configure set plugins.endpoint awscli_plugin_endpoint
	aws configure set s3.endpoint_url $(endpoint)
	aws configure set s3api.endpoint_url $(endpoint)
	aws configure set default.ca_bundle $(CA_CRT)
	aws configure set aws_access_key_id $(ACCESS)
	aws configure set aws_secret_access_key $(SECRET)
	aws configure set region "default"
	aws configure set output "json"
	@echo "### configured awscli. ###"

s3cmd-install:

	@echo "###Installing s3cmd in current machine###"
	yum install -y s3cmd
	@echo "###Installed s3cmd in current machine###"


s3cmd-configure:

	@echo "###Configure s3cmd in current machine###"
	rm -rf /root/.s3cfg
	s3cmd --configure --access_key=$(ACCESS) --secret_key=$(SECRET) -s --no-encrypt $(ssl) $(certificate) --dump-config >/root/.s3cfg
	sed -i 's|^ca_certs_file =.*|ca_certs_file = "$(CA_CRT)"|g' /root/.s3cfg
	sed -i 's|^progress_meter =.*|	progress_meter = True|g' /root/.s3cfg
	sed -i 's|^proxy_port =.*|proxy_port = 0|g' /root/.s3cfg
	sed -i 's|^host_base =.*|host_base = $(ENDPOINT)|g' /root/.s3cfg
	sed -i 's|^host_bucket =.*|host_bucket = $(ENDPOINT)|g' /root/.s3cfg
	sed -i 's|^check_ssl_certificate =.*|check_ssl_certificate = $(VALIDATE_CERTS)|g' /root/.s3cfg
	sed -i 's|^use_https =.*|use_https = $(VERIFY_SSL)|g' /root/.s3cfg
	@echo "###Configured s3cmd in current machine###"


s3fs-install:

	@echo "###Installing s3fs in current machine###"
	yum install -y epel-release
	yum install -y s3fs-fuse
	@echo "###Installing s3fs in current machine###"


s3fs-configure:

	@echo "###configure s3fs in current machine###"
	@echo "adding /etc/ssl/stx-s3-clients/s3/ca.crt value into /etc/pki/tls/certs/ca-bundle.crt to work with https"
	-trust anchor $(CA_CRT)
	rm -rf /etc/passwd-s3fs
	touch /etc/passwd-s3fs
	chmod -v 600 /etc/passwd-s3fs
	@echo $(ACCESS):$(SECRET) >>/etc/passwd-s3fs
	@echo "###configured s3fs in current machine###"


minio-install:

	@echo "###Installing minio client in current machine###"
	rm -rf mc
	wget https://dl.min.io/client/mc/release/linux-amd64/mc
	chmod +x mc
	@echo "###Installed minio client in current machine###"


minio-configure:

	@echo "###Configure minio client in current machine###"
	./mc config host add s3 $(endpoint) $(ACCESS) $(SECRET) --api S3v4
	-cp -r $(CA_CRT) /root/.mc/certs/s3.seagate.com.crt
	@echo "###configured minio client in current machine###"


jcloud-client-install:

	@echo "###Installing jCloud and Client in current machine###"
	yum install -y java-1.8.0-openjdk
	@echo "copy jclient .jar file from $(NFS_SHARE) in /root/jclientCloud."
	-umount -lf /mnt/nfs
	mkdir -p /mnt/nfs
	mount -t nfs $(NFS_SHARE) /mnt/nfs
	mkdir -p /root/jclientCloud
	cp -r /mnt/nfs/* /root/jclientCloud/
	-umount -lf /mnt/nfs
	@echo "###Installed jcloud-client client in current machine###"


s3bench-install:

	@echo "###Installing s3bench tool###"
	wget -O /usr/bin/s3bench https://github.com/Seagate/s3bench/releases/download/v2022-03-14/s3bench.2022-03-14
	chmod +x /usr/bin/s3bench
	@echo "###Installed s3bench tool###"

warp-install:

	@echo "###Installing warp tool###"
	yum install -y https://github.com/minio/warp/releases/download/v0.5.5/warp_0.5.5_Linux_x86_64.rpm
	@echo "###Installed warp tool###"

hsbench-install:

	@echo "###Installing hsbench tool###"
	rm -rf /root/go/src/github.com/markhpc/hsbench
	sudo yum install -y go
	go get github.com/markhpc/hsbench
	cd /root/go/src/github.com/markhpc/hsbench
	go build
	@echo "###Installed s3bench tool###"

bashrc-configure:
	@echo "###Configuring bashrc for setting ulimit for avoiding file-descriptor out of range issue###"
	echo 'ulimit -n 999999' >> ~/.bashrc
	source ~/.bashrc

aws: aws-install aws-configure
	@echo "### Installed & configured aws tool. ###"

aws-rgw: aws-install aws-configure-rgw
	@echo "### Installed & configured aws tool. ###"

s3fs: s3fs-install s3fs-configure
	@echo "### Installed & configured s3fs tool. ###"


s3cmd: s3cmd-install s3cmd-configure
	@echo "### Installed & configured s3cmd tool. ###"


minio: minio-install minio-configure
	@echo "### Installed & configured minio tool. ###"


install-tools: aws-install s3fs-install s3cmd-install minio-install jcloud-client-install s3bench-install
	@echo "### All tools are installed. ###"


configure-tools: aws-configure s3fs-configure s3cmd-configure minio-configure
	@echo "### All tools are configured. ###"


apache-jmeter-install:
	@echo "###Installing apache-jmeter in current machine###"
	yum install -y java-1.8.0-openjdk
	wget https://downloads.apache.org//jmeter/binaries/$(APACHE_J_METER)
	tar -zxf $(APACHE_J_METER) -C /usr/
	mv /usr/apache-jmeter-5.5 /usr/apachejmeter
	rm -rf $(APACHE_J_METER)
	@echo "###Installed apache jmeter in current machine###"


all: clean aws s3fs s3cmd minio jcloud-client-install s3bench-install warp-install apache-jmeter-install bashrc-configure
	@echo "### All tools are installed & configured. ###"

all-rgw: clean aws-rgw s3fs s3cmd minio jcloud-client-install s3bench-install warp-install apache-jmeter-install bashrc-configure
	@echo "### All tools are installed & configured. ###"


clean:

	@echo "clean-tools: Remove tools like s3fs, s3cmd, minio in case its a new machine."
	yum remove -y s3cmd
	rm -rf /root/.s3cfg
	yum remove -y s3fs-fuse
	rm -rf /etc/passwd-s3fs
	rm -rf mc
	rm -rf /root/jclientCloud/
	rm -rf /root/go/src/s3bench
	rm -rf /usr/apachejmeter
	@echo "cleanup-tools completed."


help :

	@echo "all: Install & configure tools like aws, s3fs, s3cmd, minio, s3bench call in case its a new machine. Eg: make all --makefile=<makefile_path> ACCESS=<new-accesskey> SECRET=<new-secretkey>"
	@echo "all-rgw: Install & configure tools like aws-rgw, s3fs, s3cmd, minio, s3bench call in case its a new machine. Eg: make all --makefile=<makefile_path> ACCESS=<new-accesskey> SECRET=<new-secretkey> endpoint=<IP:PORT>"
	@echo "clean: Remove installed tools like s3fs, s3cmd, minio, jclientcloud, s3bench. Eg: make clean --makefile=<makefile_path>"
	@echo "install-tools: Install tools like aws, s3fs, s3cmd, minio, s3bench call in case its a new machine. Eg: make install-tools --makefile=<makefile_path>"
	@echo "configure-tools: Install tools like aws, s3fs, s3cmd, minio, call in case its a new machine. Eg: make configure-tools --makefile=<makefile_path> ACCESS=<new-accesskey> SECRET=<new-secretkey>"
	@echo "aws: Install & configure aws tool. Eg: make aws --makefile=<makefile_path> ACCESS=<new-accesskey> SECRET=<new-secretkey>"
	@echo "aws-rgw: Install & configure aws tool. Eg: make aws --makefile=<makefile_path> ACCESS=<new-accesskey> SECRET=<new-secretkey> endpoint=<IP:PORT>"
	@echo "s3fs: Install & configure s3fs tool. Eg: make s3fs --makefile=<makefile_path> ACCESS=<new-accesskey> SECRET=<new-secretkey>"
	@echo "s3cmd: Install & configure s3cmd tool. Eg: make s3cmd --makefile=<makefile_path> ACCESS=<new-accesskey> SECRET=<new-secretkey>"
	@echo "jcloud-client-install: Setup jcloud-client. Eg: make jcloud-client --makefile=<makefile_path>"
	@echo "minio: Install & configure minio tool. Eg: make minio --makefile=<makefile_path> ACCESS=<new-accesskey> SECRET=<new-secretkey>"
	@echo "s3bench-install: Setup s3bench tool. Eg: make s3bench-install --makefile=<makefile_path>"
	@echo "apache-jmeter-install: Setup apache-jmeter-install tool. Eg: make apache-jmeter-install --makefile=<makefile_path>"
	@echo "bashrc-configure: Setup ulimit to maximum size for allowing open file descriptors. Eg:make bashrc-configure --makefile=<makefile_path>"