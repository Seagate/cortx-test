ACCESS=mPu032bIQ96kHSG1PTw1uA
SECRET=ZGlCVzmZe8wPGulNhkGDqLIDxvH+/hSUUBGxYAWz


aws:

	@echo "#Install and configure awscli."
	@echo "Server certificate should be exists at /etc/ssl/stx-s3-clients/s3/"
	pip3 install awscli
	pip3 install awscli-plugin-endpoint
	aws configure set plugins.endpoint awscli_plugin_endpoint
	aws configure set s3.endpoint_url https://s3.seagate.com
	aws configure set s3api.endpoint_url https://s3.seagate.com
	aws configure set default.ca_bundle /etc/ssl/stx-s3-clients/s3/ca.crt
	aws configure set aws_access_key_id $(ACCESS)
	aws configure set aws_secret_access_key $(SECRET)
	aws configure set region "US"
	aws configure set output "json"
	@echo "#Installed and configured awscli."


s3cmd:

	@echo "###Installing s3cmd in current machine###"
	yum install -y s3cmd
	touch /root/.s3cfg
	chmod -v 600 /root/.s3cfg
	@echo [default] >>/root/.s3cfg
	@echo access_key = $(ACCESS) >>/root/.s3cfg
	@echo secret_key = $(SECRET) >>/root/.s3cfg
	@echo ca_certs_file = "/etc/ssl/stx-s3-clients/s3/ca.crt" >>/root/.s3cfg
	@echo check_ssl_certificate = True >>/root/.s3cfg
	@echo "###Installed s3cmd in current machine###"


s3fs:

	@echo "###Installing s3fs in current machine###"
	yum install -y s3fs-fuse
	@echo "adding /etc/ssl/stx-s3-clients/s3/ca.crt value into /etc/pki/tls/certs/ca-bundle.crt to work with https"
	trust anchor /etc/ssl/stx-s3-clients/s3/ca.crt
	touch /etc/passwd-s3fs
	chmod -v 600 /etc/passwd-s3fs
	@echo $(ACCESS):$(SECRET) >>/etc/passwd-s3fs
	@echo "###Installed s3fs in current machine###"


minio:

	@echo "###Installing minio client in current machine###"
	wget https://dl.min.io/client/mc/release/linux-amd64/mc
	chmod +x mc
	./mc config host add s3 https://s3.seagate.com $(ACCESS) $(SECRET) --api S3v4
	cp -r /etc/ssl/stx-s3-clients/s3/ca.crt /root/.mc/certs/s3.seagate.com.crt
	@echo "###Installed minio client in current machine###"


jcloud-client:

	@echo "###Installing jCloud and Client in current machine###"
	yum install -y java-1.8.0-openjdk
	@echo "please copy jclient .jar file in /root/jclientCloud."
	mkdir /mnt/nfs
	mount -t nfs cftic2.pun.seagate.com:/cftshare/jclientCloud/ /mnt/nfs
	mkdir /root/jclientCloud
	cp -r /mnt/nfs/* /root/jclientCloud/
	umount -l /mnt/nfs
	rm -rf /mnt/nfs
	@echo "###Installed jcloud-client client in current machine###"


install-tools: aws s3fs minio s3cmd jcloud-client
	@echo "### All tools are installed###"


help :

	@echo "install-tools: Install tools like aws, s3fs, s3cmd, minio, call in case its a new machine."
	@echo "aws          : Install aws tool."
	@echo "s3fs         : Install s3fs tool."
	@echo "s3cmd        : Install s3cmd tools."
	@echo "jcloud-client: Create jcloud-client dir."
	@echo "minio        : Install minio tools and configure credentials. Eg make minio ACCESS=<new-accesskey> SECRET=<new-secretkey>"

