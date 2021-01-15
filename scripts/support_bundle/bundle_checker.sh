#!/usr/bin/bash
USER_HOME=$(pwd)
BUNDLE_HOME="$USER_HOME/cortx_bundle"
alias ls="ls --block-size=M"
NOW=$(date +"%m-%d-%Y")
CMD_OUT=
echo "Removing $BUNDLE_HOME"
rm -rf $BUNDLE_HOME
[ -d $BUNDLE_HOME ] && echo "Directory $BUNDLE_HOME exists." || mkdir $BUNDLE_HOME


CMD_OUT=$(sudo cortxcli support_bundle generate supp_bundle_$NOW -c all)

# Build support bundle file
echo "Wait till cortxcli support bundle generate is running..."

while true
do
  CHECK_PS=$(ps -aef | grep "cortxcli bundle_generate" | grep -v grep > /dev/null)
  if [ $? -eq 0 ]; then
    echo "cortxcli support_bundle generate is running."
	sleep 10
  else
    echo "cortxcli support_bundle generate is not running."
	break
  fi
done

# Extract the support bundle id and extract bundle tar in CD
echo "Bundle id is $CMD_OUT"
CMD_OUT=$(echo $CMD_OUT | awk '{print $16}') 

status=$(sudo cortxcli support_bundle status $CMD_OUT | awk -F'|' '{print $6}' |grep -iE "fail|error")

if [ $? eq 1 ]
then
	echo "Support bundle failed to create for one or more components"
	exit 1
fi

tar -xzvf /tmp/support_bundle/SUPPORT_BUNDLE.$CMD_OUT > /dev/null 2>&1
find . -name '*.tar.gz' -execdir tar -xzvf '{}' \; > /dev/null 2>&1
#Extract remaining xz files
find . -name '*.tar.xz' -execdir xz -d '{}' \; > /dev/null 2>&1
find . -name '*.tar' -execdir tar -xvf '{}' \; > /dev/null 2>&1

BUNDLE_SZ=$(find ./$CMD_OUT -type f -exec du -ch {} + | grep total$)

echo "Total bundle size is $BUNDLE_SZ"

#list=$(find ./$CMD_OUT -type f -exec du -ch --block-size=1M {} \; | awk '{print $2 $1}')

find ./$CMD_OUT -type f -exec du -sh --block-size=1M {} \; | while read -r line;
do 
   awk '{file=$2; sz=$1 ;print file,sz }';
done

exit 0


