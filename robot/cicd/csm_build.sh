#!/usr/bin/env bash
set -e
BUILD_START_TIME=$(date +%s)
BASE_DIR=$(realpath "$(dirname $0)/..")
PROG_NAME=$(basename $0)
DIST=$(realpath $BASE_DIR/dist)
CORTX_PATH="/opt/seagate/cortx/"
CSM_PATH="${CORTX_PATH}csm"
DEBUG="DEBUG"
INFO="INFO"


print_time() {
    printf "%02d:%02d:%02d\n" $(( $1 / 3600 )) $(( ( $1 / 60 ) % 60 )) $(( $1 % 60 ))
}


rpm_build() {
echo "rpm build CSM $1 RPM"
echo rpmbuild --define "version $VER" --define "dist $BUILD" --define "_topdir $TOPDIR" \
        -bb "$TMPDIR/$2.spec"
rpmbuild --define "version $VER" --define "dist $BUILD" --define "_topdir $TOPDIR" -bb "$TMPDIR/$2.spec"
}

gen_tar_file(){
TAR_START_TIME=$(date +%s)
cd $BASE_DIR
cd ${DIST}
echo "Creating tar for $1 build from $2 folder"
    tar -czf "${DIST}/rpmbuild/SOURCES/${PRODUCT}-$1-${VER}.tar.gz" "$2"
TAR_END_TIME=$(($(date +%s) - TAR_START_TIME))
TAR_TOTAL_TIME=$((TAR_TOTAL_TIME + TAR_END_TIME))
}


usage() {
    echo """
usage: $PROG_NAME [-v <csm version>]
                            [-b <build no>]
                            [-p <product_name>]
Options:
    -v : Build rpm with version
    -b : Build rpm with build number
    -p : Provide product name default cortx
        """ 1>&2;
    exit 1;
}

while getopts ":v:b:p" o; do
    case "${o}" in
        v)
            VER=${OPTARG}
            ;;
        b)
            BUILD=${OPTARG}
            ;;
        p)
            PRODUCT=${OPTARG}
            ;;

    esac
done

cd $BASE_DIR
[ -z $"$BUILD" ] && BUILD="$(git rev-parse --short HEAD)" \
        || BUILD="${BUILD}_$(git rev-parse --short HEAD)"
[ -z "$VER" ] && VER=$(cat $BASE_DIR/VERSION)
[ -z "$PRODUCT" ] && PRODUCT="cortx"


echo "Using  VERSION=${VER} BUILD=${BUILD} PRODUCT=${PRODUCT} ..."

################### COPY FRESH DIR ##############################

# Create fresh one to accomodate all packages.
COPY_START_TIME=$(date +%s)
DIST="$BASE_DIR/dist"
TMPDIR="$DIST/tmp"
[ -d "$TMPDIR" ] && {
    rm -rf ${TMPDIR}
}
mkdir -p $TMPDIR

cd $BASE_DIR
rm -rf "${DIST}/rpmbuild"
mkdir -p "${DIST}/rpmbuild/SOURCES"
COPY_END_TIME=$(date +%s)


################### CSM_Test ##############################
yum install -y tree

cp "$BASE_DIR/cicd/csm_test.spec" "$TMPDIR"
# Build CSM Test
ls -la $TMPDIR
CORE_BUILD_START_TIME=$(date +%s)
mkdir -p "$DIST/csm_test" "$DIST/csm_test/lib"

# Copy CSM Test files
cp -rf "$BASE_DIR/reports" "$BASE_DIR/resources"  "$BASE_DIR/testsuites" "$BASE_DIR/utils" "$BASE_DIR/cicd/csm_test.py" "$DIST/csm_test"
cp -f "$BASE_DIR/cicd/csm_test.py" "$DIST/csm_test/lib/csm_gui_test"
chmod +x "$DIST/csm_test/lib/"*
ls -la $DIST/csm_test
chmod +x "$DIST/csm_test"*
cd "$TMPDIR"
tree -L 3 $DIST
################## Add CSM_PATH #################################

# Genrate spec file for CSM
sed -i -e "s/<RPM_NAME>/${PRODUCT}-csm_test/g" \
    -e "s|<CSM_PATH>|${CSM_PATH}|g" \
    -e "s/<PRODUCT>/${PRODUCT}/g" "$TMPDIR/csm_test.spec"


gen_tar_file csm_test csm_test
rm -rf "${TMPDIR}/csm_test/"*

################### RPM BUILD ##############################

# Generate RPMs
RPM_BUILD_START_TIME=$(date +%s)
TOPDIR=$(realpath ${DIST}/rpmbuild)

# CSM test RPM
rpm_build csm_test csm_test

RPM_BUILD_END_TIME=$(date +%s)

# Remove temporary directory
\rm -rf "${DIST}/csm_test"
\rm -rf "${TMPDIR}"
BUILD_END_TIME=$(date +%s)

echo "CSM TEST RPMs ..."
find "$BASE_DIR" -name "*.rpm"


printf "COPY TIME:      \t\t"
print_time $(( COPY_END_TIME - COPY_START_TIME ))

printf "Time taken in creating RPM: \t"
print_time $(( RPM_BUILD_END_TIME - RPM_BUILD_START_TIME ))

printf "Total build time: \t\t"
print_time $(( BUILD_END_TIME - BUILD_START_TIME ))
