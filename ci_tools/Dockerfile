FROM centos:7

# Enter PAT of your github account
ARG GIT_TOKEN
RUN yum update -y
RUN yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make sqlite-devel
RUN cd /usr/src && wget https://www.python.org/ftp/python/3.7.9/Python-3.7.9.tgz && tar xzf Python-3.7.9.tgz && rm Python-3.7.9.tgz
RUN cd /usr/src/Python-3.7.9 && ./configure --prefix=/usr --enable-optimizations --enable-shared --enable-loadable-sqlite-extensions
RUN cd /usr/src/Python-3.7.9 && make altinstall
RUN echo 'alias python="/usr/bin/python3.7"' >> ~/.bashrc
RUN echo 'alias python3="/usr/bin/python3.7"' >> ~/.bashrc
RUN yum install -y git
RUN git clone --branch dev https://$GIT_TOKEN@github.com/Seagate/cortx-test.git
WORKDIR /cortx-test
RUN yum install -y python3-devel librdkafka nfs-utils python3-tkinter
RUN python3.7 -m pip install --upgrade pip
RUN python3.7 -m pip install --ignore-installed -r requirements.txt
COPY secrets.json .
