Name: <RPM_NAME>
Version: %{version}
Release: %{dist}
Summary: CSM Test RPM IS TO TEST AND VALIDATE THE CSM GUI TEST CASES ON TARGTE MACHINE
License: Seagate
URL: https://github.com/Seagate/cortx-test
Source0: <PRODUCT>-csm_test-%{version}.tar.gz
%define debug_package %{nil}

%description
CSM Tools

%prep
%setup -c csm_test
# Nothing to do here


%install
mkdir -p ${RPM_BUILD_ROOT}<CSM_PATH>
cp -rp . ${RPM_BUILD_ROOT}<CSM_PATH>
exit 0

%post
# Use csm_setup cli for csm directory, permission services
CSM_DIR=<CSM_PATH>
PRODUCT=<PRODUCT>
# Move binary file
[ -d "${CSM_DIR}/lib" ] && {

    ln -sf $CSM_DIR/csm_test/lib/csm_gui_test /usr/bin/csm_gui_test

}
exit 0

%postun
[ $1 -eq 1 ] && exit 0
rm -f /usr/bin/csm_gui_test 2> /dev/null;
rm -rf <CSM_PATH>/csm_test 2> /dev/null;

exit 0


%files
%defattr(-, root, root, -)
<CSM_PATH>/*


%changelog
* Thu May 31 2021 Ashish Dhavalikar <ashish.dhavalikar@seagate.com> - 1.0.0
- Initial spec file
