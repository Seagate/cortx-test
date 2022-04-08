#!/bin/sh
secrets_json_path=/root/secrets.json
WORKSPACE=/root
cp $secrets_json_path "$WORKSPACE/cortx-test/secrets.json"
cd cortx-test

function check_installation {
  pckarr=(unzip, google-chrome-stable_current_x86_64.rpm )
  for i in  ${pckarr[*]}
   do
   isinstalled=$(rpm -q $i)
   if [ !  "$isinstalled" == "package $i is not installed" ];
   then
     echo Package  $i already installed
   else
     echo $i is not installed!
     yum install -y $i
   fi
   done
}

function unmount_robot_gui_tools {
  # create & mount file://cftic2.pun.seagate.com/cftshare/tools/robot_gui
  umount -t nfs robot_chrome
  rm -fd robot_chrome
}

function mount_robot_gui_tools {
  # create & mount file://cftic2.pun.seagate.com/cftshare/tools/robot_gui
  mkdir -p robot_chrome
  mount -t nfs cftic2.pun.seagate.com:/cftshare/tools/robot_gui/ robot_chrome
}

function install_chrome {
  # remove if any existing chrome is installed
  rpm -e google-chrome-stable
  if [[ -e "robot_chrome/google-chrome-stable_current_x86_64.rpm" ]]
  then
    echo '... google-chrome found on mounted dir, starting localinstall'
    yes | sudo yum localinstall robot_chrome/google-chrome-stable_current_x86_64.rpm
  else
    echo '... google-chrome not found on mounted dir'
    wget -N https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
    check_installation
  fi
  google-chrome --version
}

function install_chrome_driver {
  # copy chromedriver to bin & make it executable
  if [[ -e "robot_chrome/chromedriver" ]]
  then
    echo '... chromedriver found on mounted dir'
    yes | cp -rf  robot_chrome/chromedriver /usr/bin/
    chmod +x /usr/bin/chromedriver
  else
    echo '... chromedriver not found on mounted dir'
    VERSION=$(curl http://chromedriver.storage.googleapis.com/LATEST_RELEASE)
    wget -N https://chromedriver.storage.googleapis.com/"$VERSION"/chromedriver_linux64.zip
    yes | unzip chromedriver_linux64.zip
    yes | cp -rf  chromedriver /usr/bin/chromedriver
    chmod +x /usr/bin/chromedriver
  fi
  if [[ -d "./virenv/bin" ]]
  then
    echo '... virenv/bin dir found'
    yes | cp -rf  /usr/bin/chromedriver ./virenv/bin/
  fi
  chromedriver --version
}

#yum update -y
yum install -y nfs-utils

mkdir -p /etc/ssl/stx-s3-clients/s3/
cp ci_tools/ca.crt /etc/ssl/stx-s3-clients/s3/


yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make sqlite-devel
if [[ ! -f "/usr/bin/python3.7" ]]
then
  cd /usr/src && wget https://www.python.org/ftp/python/3.7.9/Python-3.7.9.tgz && tar xzf Python-3.7.9.tgz && rm -f Python-3.7.9.tgz
  cd /usr/src/Python-3.7.9 && ./configure --prefix=/usr --enable-optimizations --enable-loadable-sqlite-extensions
  cd /usr/src/Python-3.7.9 && make altinstall
  echo 'alias python3="/usr/bin/python3.7"' >> ~/.bashrc
fi

cd /usr/bin

if [[ -f "/usr/bin/python3.7" ]]
then
  ln -s /usr/bin/python3.7 python37
fi

if [[ -f "/usr/local/bin/python3.7" ]]
then
  ln -s /usr/local/bin/python3.7 python3.7

fi

yum install -y python3-devel librdkafka python3-tkinter

python3.7 -m venv virenv
source virenv/bin/activate
pip install --upgrade pip
if ${Need_pip_source}; then
pip3 install -r requirements.txt -i https://pypi.python.org/simple/
else
pip3 install -r requirements.txt
fi
export PYTHONPATH=$WORKSPACE:$WORKSPACE/cortx-test:$PYTHONPATH


cd "$WORKSPACE/cortx-test/scripts/s3_tools/"
make clean
make install-tools

cd "$WORKSPACE/cortx-test/"

mount_robot_gui_tools
install_chrome
install_chrome_driver
unmount_robot_gui_tools