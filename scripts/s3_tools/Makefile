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
ENDPOINT=https://s3.seagate.com
CA_CRT=/etc/ssl/stx-s3-clients/s3/ca.crt
NFS_SHARE=cftic2.pun.seagate.com:/cftshare/jclientCloud/


aws:

	@echo "#Install and configure awscli."
	@echo "Server certificate should be exists at /etc/ssl/stx-s3-clients/s3/"
	pip3 install awscli
	pip3 install awscli-plugin-endpoint
	aws configure set plugins.endpoint awscli_plugin_endpoint
	aws configure set s3.endpoint_url $(ENDPOINT)
	aws configure set s3api.endpoint_url $(ENDPOINT)
	aws configure set default.ca_bundle $(CA_CRT)
	aws configure set aws_access_key_id $(ACCESS)
	aws configure set aws_secret_access_key $(SECRET)
	aws configure set region "US"
	aws configure set output "json"
	@echo "#Installed and configured awscli."


s3cmd:

	@echo "###Installing s3cmd in current machine###"
	yum install -y s3cmd
	rm -rf /root/.s3cfg
	s3cmd --configure --access_key=$(ACCESS) --secret_key=$(SECRET) -s --no-encrypt --dump-config >/root/.s3cfg
	sed -i 's|^ca_certs_file =.*|ca_certs_file = "$(CA_CRT)"|g' /root/.s3cfg
	sed -i 's|^progress_meter =.*|	progress_meter = True|g' /root/.s3cfg
	sed -i 's|^proxy_port =.*|proxy_port = 0|g' /root/.s3cfg
	sed -i 's|^host_base =.*|host_base = s3.seagate.com|g' /root/.s3cfg
	sed -i 's|^host_bucket =.*|host_bucket = s3.seagate.com|g' /root/.s3cfg
	@echo "###Installed s3cmd in current machine###"


s3fs:

	@echo "###Installing s3fs in current machine###"
	yum install -y epel-release
	yum install -y s3fs-fuse
	@echo "adding /etc/ssl/stx-s3-clients/s3/ca.crt value into /etc/pki/tls/certs/ca-bundle.crt to work with https"
	trust anchor $(CA_CRT)
	rm -rf /etc/passwd-s3fs
	touch /etc/passwd-s3fs
	chmod -v 600 /etc/passwd-s3fs
	@echo $(ACCESS):$(SECRET) >>/etc/passwd-s3fs
	@echo "###Installed s3fs in current machine###"


minio:

	@echo "###Installing minio client in current machine###"
	rm -rf mc
	wget https://dl.min.io/client/mc/release/linux-amd64/mc
	chmod +x mc
	./mc config host add s3 https://s3.seagate.com $(ACCESS) $(SECRET) --api S3v4
	cp -r $(CA_CRT) /root/.mc/certs/s3.seagate.com.crt
	@echo "###Installed minio client in current machine###"


jcloud-client:

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


install-tools: aws s3fs minio s3cmd jcloud-client
	@echo "### All tools are installed###"


clean:

	@echo "clean-tools: Remove tools like s3fs, s3cmd, minio in case its a new machine."
	yum remove -y s3cmd
	rm -rf /root/.s3cfg
	yum remove -y s3fs-fuse
	rm -rf /etc/passwd-s3fs
	rm -rf mc
	rm -rf /root/jclientCloud/
	@echo "cleanup-tools completed."


help :

	@echo "install-tools: Install tools like aws, s3fs, s3cmd, minio, call in case its a new machine."
	@echo "aws          : Install & configure aws tool."
	@echo "s3fs         : Install & configure s3fs tool."
	@echo "s3cmd        : Install & configure s3cmd tool."
	@echo "jcloud-client: Setup jcloud-client."
	@echo "minio        : Install & configure minio tool. credentials: Eg make minio ACCESS=<new-accesskey> SECRET=<new-secretkey>"
