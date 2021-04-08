###############################################################################
# Spec file for cortx test
################################################################################

%define name cortxtest
%define version 1.0.0
%define release 1
%define pyver 3.7.9
%define python /usr/local/bin/python3.7
%define pip /usr/local/bin/pip3.7
%define basedir /cortxtest/cortx-test
Summary: Python distribution for cortx-text
Name: %{name}
Version: %{version}
Release: %{release}
License: Apache 2.0
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
%{basedir}/
# executable
%attr(0777, root, root) %{basedir}/testrunner.py
%attr(0777, root, root) %{basedir}/drunner.py
%attr(0777, root, root) %{basedir}/scripts/locust/locust_runner.py
%attr(0777, root, root) %{basedir}/scripts/s3_bench/s3bench.py

%build
cd %{buildroot}%{basedir}/
%{python} setup.py build 

%post
%{python} -V
if [ "$?" = "0" ]; then
    echo "python 3.7 is installed"
else
    yum clean all
    rm -f /var/lib/rpm/.rpm.lock
    rpm --rebuilddb
    yum -y update
    yum history new
    rm -f /var/lib/rpm/.rpm.lock
    rpm --rebuilddb
    yum -y groupinstall "Development Tools"
    yum install -y xz-devel python-backports-lzma sqlite-devel epel-release
    yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel
    cd /usr/src
    wget https://www.python.org/ftp/python/%{pyver}/Python-%{pyver}.tgz
    tar -xzf Python-%{pyver}.tgz
    cd Python-%{pyver}
    make clean
    ./configure --enable-optimizations --with-ssl --enable-loadable-sqlite-extensions
    make altinstall
    rm -rf /usr/src/Python-%{pyver}.tgz
    %{python} -V
fi
yum install -y python34-setuptools
easy_install-3.4 pip

%{pip} install --upgrade pip
%{pip} install wheel
%{pip} install -r %{basedir}/requirements.txt
find %{basedir} \( -name '__pycache__' -or -name '*.pyc' \) -delete
echo "Installing setup.py"
cd %{basedir}/
%{python} setup.py install
echo "developing setup.py"
%{python} setup.py develop
rm -rf build/

ln -s %{basedir} /usr/local/lib/python3.7/site-packages/cortx-test

script_list=("scripts/s3_bench/s3bench" "scripts/locust/locust_runner" "testrunner" "drunner")
short_array=("pys3bench" "runlocust" "testrunner" "drunner")
for i in "${!script_list[@]}";
do
    aliasmsg=ALIAS_MSG_${short_array[$i]}
    aliasmsg="alias ${short_array[$i]}='%{python} %{basedir}/${script_list[$i]}.py'"
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
rm -rf %{basedir}/

%clean
rm -rf %{buildroot}/SOURCES/cortxtest/
