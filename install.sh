PYVER=3.7.9
PYPATH="/usr/local/bin/"
PYTHON="${PYPATH}python${PYVER%.*}"
PIP="${PYPATH}pip${PYVER%.*}"

#yum -y update
${PYTHON} -V
if [ "$?" = "0" ]; then
    echo "python ${PYVER%.*} is installed"
else
    yum clean all
    yum history new
    rm -f /var/lib/rpm/.rpm.lock
    rpm --rebuilddb
    yum -y groupinstall "Development Tools"
    yum install -y xz-devel python-backports-lzma sqlite-devel epel-release
    yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel
    cd /usr/src
    wget https://www.python.org/ftp/python/${PYVER}/Python-${PYVER}.tgz
    tar -xzf Python-${PYVER}.tgz
    cd Python-${PYVER}
    make clean
    ./configure --enable-optimizations --with-ssl --enable-loadable-sqlite-extensions
    make altinstall
    rm -rf /usr/src/Python-${PYVER}.tgz
    ${PYPATH} -V
fi
yum install -y python34-setuptools
easy_install pip

${PIP} install --upgrade pip
${PIP} install wheel
rpm -e cortxtest-1.0.0-1.noarch
rpm -i cortxtest-1.0.0-1.noarch.rpm
cd /usr/local/lib/python3.7/site-packages/cortx-test
${PIP} install -r /usr/local/lib/python3.7/site-packages/cortx-test/requirements.txt
echo "Installing setup.p"
${PYTHON} /usr/local/lib/python3.7/site-packages/cortx-test/setup.py install
echo "developing setup.py"
${PYTHON} /usr/local/lib/python3.7/site-packages/cortx-test/setup.py develop
