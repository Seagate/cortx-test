FROM centos:7

# Enter PAT of your github account
ARG GIT_TOKEN
RUN yum update -y
RUN yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make sqlite-devel sudo
RUN cd /usr/src && wget https://www.python.org/ftp/python/3.7.9/Python-3.7.9.tgz && tar xzf Python-3.7.9.tgz && rm Python-3.7.9.tgz
RUN cd /usr/src/Python-3.7.9 && ./configure --prefix=/usr --enable-optimizations --enable-shared --enable-loadable-sqlite-extensions
RUN cd /usr/src/Python-3.7.9 && make altinstall
RUN echo 'alias python="/usr/bin/python3.7"' >> ~/.bashrc
RUN echo 'alias python3="/usr/bin/python3.7"' >> ~/.bashrc
RUN yum install -y git
RUN git clone --branch dev https://$GIT_TOKEN@github.com/Seagate/cortx-test.git
RUN mkdir -p /etc/ssl/stx-s3-clients/s3/
COPY ca.crt /etc/ssl/stx-s3-clients/s3/
RUN mkdir /root/.aws
WORKDIR /cortx-test
RUN yum install -y python3-devel librdkafka nfs-utils python3-tkinter
RUN python3.7 -m pip install --upgrade pip
RUN python3.7 -m pip install pysqlite3
RUN python3.7 -m pip install --ignore-installed -r requirements.txt
RUN python3.7 -m pip install awscli awscli-plugin-endpoint
RUN aws configure set plugins.endpoint awscli_plugin_endpoint
RUN aws configure set s3.endpoint_url https://s3.seagate.com
RUN aws configure set s3api.endpoint_url https://s3.seagate.com
RUN aws configure set default.ca_bundle /etc/ssl/stx-s3-clients/s3/ca.crt
ENV AWS_ACCESS_KEY_ID=AKIATovwzXJMRbKhU0hI0szGQA
ENV AWS_SECRET_ACCESS_KEY=ly13PG6ky4lZhxJ3PvvAbjQgvWcKeRGlORLiwXaH
ENV AWS_DEFAULT_REGION=US
ENV AWS_DEFAULT_OUTPUT=json
ENV JIRA_ID=0
ENV JIRA_PASSWORD=AA
ENV TEST_PLAN_NUMBER=00000
ENV BUILD=000
ENV BUILD_TYPE=AA
ENV SETUP_TYPE=regular
ENV TARGET_NODE=ssc-vm-4308
ENV COMMENT_JIRA=00000
ENV DB_UPDATE=True
ENV SEQUENTIAL_EXECUTION=False
ENV BRANCH=stable
ENV NODES=1
ENV SERVER_TYPE=AA
ENV ENCLOSURE_TYPE=5u84
ENV SKIP_TE=None
ENV PYTHON_VAR=python3.7
COPY secrets.json .
