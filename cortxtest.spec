###############################################################################
# Spec file for cortx test
################################################################################

%define name cortxtest
%define version 1.0.0
%define release 1
%define python /usr/local/bin/python3.7
%define pip /usr/local/bin/pip3.7
Summary: Python distribution for cortx-text
Name: %{name}
Version: %{version}
Release: %{release}
License: Seagate
Group: Development/Libraries
Packager: Divya Kachhwaha
BuildRoot: /root/rpmbuild/
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Seagate <seagate.com>
Url: https://github.com/Seagate/cortx-test

# Build with the following syntax:
# rpmbuild -bb utils.spec

%description
Cortx-test automation test installation package

%prep
rm -rf %{buildroot}/cortxtest/
mkdir -p %{buildroot}/cortxtest/
cp -r /root/dk/cortx/cortx-test/ %{buildroot}/cortxtest/
rm -rf %{buildroot}/cortxtest/log
find . \( -name '__pycache__' -or -name '*.pyc' \) -delete
exit

%files
%defattr(-,root,root,-)
%dir /cortxtest/cortx-test/
/cortxtest/cortx-test/
# executable
%attr(0777, root, root) /cortxtest/cortx-test/testrunner.py
%attr(0777, root, root) /cortxtest/cortx-test/drunner.py
%attr(0777, root, root) /cortxtest/cortx-test/scripts/locust/locust_runner.py
%attr(0777, root, root) /cortxtest/cortx-test/scripts/s3_bench/s3bench.py

%build
cd %{buildroot}/cortxtest/cortx-test/
%{python} setup.py build

%post
%{python} -V
if [ "$?" = "0" ]; then
    echo "python 3.7 is installed"
else
    yum -y update
    yum history new
    yum -y groupinstall "Development Tools"
    yum install xz-devel python-backports-lzma sqlite-devel -y
    yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel
    yum install epel-release
    cd /usr/src
    wget https://www.python.org/ftp/python/3.7.9/Python-3.7.9.tgz
    tar -xzf Python-3.7.9.tgz
    cd Python-3.7.9
    make clean
    ./configure --enable-optimizations --with-ssl --enable-loadable-sqlite-extensions
    make altinstall
    rm -rf /usr/src/Python-3.7.9.tgz
    %{python} -V
fi
yum install -y python34-setuptools
easy_install-3.4 pip
%{pip} install --upgrade pip
%{pip} install -r /cortxtest/cortx-test/requirements.txt
find /cortxtest/cortx-test \( -name '__pycache__' -or -name '*.pyc' \) -delete

ln -s /cortxtest/cortx-test /usr/local/lib/python3.7/site-packages/cortx-test

script_list=("scripts/s3_bench/s3bench" "scripts/locust/locust_runner" "testrunner" "drunner")
short_array=("pys3bench" "runlocust" "testrunner" "drunner")
for i in "${!script_list[@]}";
do
    aliasmsg=ALIAS_MSG_${short_array[$i]}
    aliasmsg="alias ${short_array[$i]}='%{python} /cortxtest/cortx-test/${script_list[$i]}.py'"
    alias_msg_array[$i]="$aliasmsg"
done
CT_PROFILED=/etc/profile.d/ct.sh
if [ ! -f "$CT_PROFILED" ]
then
    for n in "${alias_msg_array[@]}"
    do
       echo -e "$n" >> "$CT_PROFILED" 
    done
else
    TMP_CT_PROFILED=/tmp/ct.sh.$$
    cp "$CT_PROFILED" "$TMP_CT_PROFILED"
    for n in "${alias_msg_array[@]}"
    do 
       grep -q "$n" "$TMP_CT_PROFILED" || echo -e "$n" >> "$TMP_CT_PROFILED"
    done
    cp "$TMP_CT_PROFILED" "$CT_PROFILED"
    rm -f "$TMP_CT_PROFILED"
fi
source /etc/profile.d/ct.sh
cd /cortxtest/cortx-test/
echo "Installing setup.py"
%{python} setup.py install
echo "developing setup.py"
%{python} setup.py develop
echo "Installation completed"

%postun
if [ "$1" = "0" ]; then
    unlink /usr/local/lib/python3.7/site-packages/cortx-test
    CT_PROFILED=/etc/profile.d/ct.sh
	script_list=("scripts/s3_bench/s3bench" "scripts/locust/locust_runner")
    if [ -f "$CT_PROFILED" ]
    then 
        TMP_CT_PROFILED=/tmp/ct.sh.$$
        cp "$CT_PROFILED" "$TMP_CT_PROFILED"
        for (( i=0; i<${#script_list[@]}; i++ ));
        do
            script_list[$i]=${script_list[$i]%,}
            sed -i '/${script_list[$i]}/d' "$TMP_CT_PROFILED"
        done
        cp "$TMP_CT_PROFILED" "$CT_PROFILED"
        rm -f "$TMP_CT_PROFILED"
    fi
    
    echo 'To complete the uninstall,please re-login to the system'
fi
rm -rf /etc/profile.d/ct.sh

%clean
rm -rf %{buildroot}/SOURCES/cortxtest/
