`bundle_checker.sh` creates support bundle and extract the bundled tar.gz and xz files recursively to a 
directory structure in directory from where bundle_checker.sh is run.
`bundle_checker_outer.sh` waits for inner process and parses all the support bundle files sizes 
for violation against max sizes associative array.

To run the support bundle test
run following command from directory where you want to extract the support bundle.
./bundle_checker_outer.sh

sample output is 
Size of ./SB29c2iqba/hare/iu17-r21.pun.seagate.com/var/log/cluster/corosync.log-20201105.gz 1 within max limit
Size of ./SB29c2iqba/hare/iu17-r21.pun.seagate.com/var/log/cluster/corosync.log-20201106.gz 1 within max limit
Size violation by ./SB29c2iqba/s3/var/log/seagate/s3/audit/audit.log 918
Size violation by ./SB29c2iqba/s3/var/log/haproxy.log 229

To capture size violation only run
`./bundle_checker_outer.sh | grep violation`


