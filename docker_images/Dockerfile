FROM centos:7

# Enter PAT of your github account
ARG GIT_TOKEN
#ARG ACCESS_KEY
#ARG SECRET_KEY
RUN yum update -y
RUN yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make
RUN cd /usr/src && wget https://www.python.org/ftp/python/3.7.9/Python-3.7.9.tgz && tar xzf Python-3.7.9.tgz && rm Python-3.7.9.tgz
RUN cd /usr/src/Python-3.7.9 && ./configure --prefix=/usr --enable-optimizations --enable-shared
RUN cd /usr/src/Python-3.7.9 && make altinstall
RUN echo 'alias python="/usr/bin/python3.7"' >> ~/.bashrc
RUN echo 'alias python3="/usr/bin/python3.7"' >> ~/.bashrc
RUN yum install -y git
RUN git clone https://$GIT_TOKEN@github.com/Seagate/cortx-test.git
WORKDIR /cortx-test
RUN git checkout dev
RUN yum install -y python3-devel
RUN yum install -y librdkafka
RUN yum install -y nfs-utils
RUN python -m pip install pip
RUN python -m pip install --upgrade pip
RUN python -m pip install --ignore-installed -r requirements.txt
RUN python -m pip install awscli
#RUN aws configure set aws_access_key_id $ACCESS_KEY
#RUN aws configure set aws_secret_access_key $SECRET_KEY
#RUN aws configure set default.region US
#RUN aws configure set default.output json
#RUN pip3 install awscli-plugin-endpoint
#RUN aws configure set plugins.endpoint awscli_plugin_endpoint
#RUN aws configure set s3.endpoint_url https://s3.seagate.com
COPY secrets.json .
COPY ca.crt /etc/ssl/stx-s3-clients/s3/
#RUN aws configure set ca_bundle /etc/ssl/stx-s3-clients/s3/ca.crt
# CMD ["pytest", "--collect-only", "--target", "automation"]
