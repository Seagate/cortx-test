#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""All the constants are alphabetically arranged."""
CREATE_FILE = "dd if={} of={} bs={} count={} iflag=fullblock"
FIREWALL_CMD = "firewall-cmd --service={} --get-ports --permanent"
GREP_PCS_SERVICE_CMD = "pcs status | grep {}"
LS_CMD = "ls {}"
LS_LH_CMD = "ls -lhR $dir"
LST_PRVSN_DIR = "ls /opt/seagate/"
LST_RPM_CMD = "rpm -qa | grep eos-prvsnr"
MEM_USAGE_CMD = "python3 -c 'import psutil; print(psutil.virtual_memory().percent)'"
MOTR_START_FIDS = "hctl mero process start --fid {}"
MOTR_STATUS_CMD = "hctl status"
HA_LOG_CMD = "/bin/bash"
HA_LOG_FOLDER = "cat /etc/cortx/log/ha/*/health_monitor.log"
SERVICE_HA_STATUS = "ps -aux"
HA_COPY_CMD = "kubectl cp {} {}:{}"
HA_POD_RUN_SCRIPT = 'kubectl exec {} -- {} {}'
HA_LOG_PVC = "ls /mnt/fs-local-volume/local-path-provisioner/"
HA_CONSUL_STR = 'consul kv get ' \
                '-http-addr=consul-server:8500 ' \
                '--recurse "cortx>ha>v1>cluster_stop_key"'
MOTR_STOP_FIDS = "hctl mero process stop --fid {} --force"
HCTL_STATUS_CMD_JSON = "hctl status --json"
HCTL_DISK_STATUS = "hctl status -d"
NETSAT_CMD = "netstat -tnlp | grep {}"
PCS_CLUSTER_START = "pcs cluster start {}"
PCS_CLUSTER_STOP = "pcs cluster stop {}"
PCS_CLUSTER_STATUS = "pcs cluster status"
PCS_RESOURCES_CLEANUP = "pcs resource cleanup {}"
PCS_RESOURCE_SHOW_CMD = "pcs resource show"
PCS_RESOURCE_RESTART_CMD = "pcs resource restart {}"
PCS_RESOURCE_ENABLE_CMD = "pcs resource enable {}"
PCS_RESOURCE_DISABLE_CMD = "pcs resource disable {}"
PCS_RESOURCE_STONITH_CMD = "pcs resource {0} stonith-srvnode-{1}-clone"
PCS_RESOURCE_CMD = "pcs resource {} {} {}"
PGREP_CMD = "sudo pgrep {}"
PKIL_CMD = "pkill {}"
CORTX_DATA_CLEANUP = "cortx_setup cluster reset --type data"
RPM_GREP_CMD = "rpm -qa | grep {}"
RPM_INSTALL_CMD = "yum install -y {0}"
SYSTEM_CTL_CMD = "systemctl {} {}"
SYSTEM_CTL_STATUS_CMD = "systemctl status {}"
SYSTEM_CTL_RESTART_CMD = "systemctl restart {}"
SYSTEM_CTL_START_CMD = "systemctl start {}"
SYSTEM_CTL_STOP_CMD = "systemctl stop {}"
SYSTEM_CTL_DISABLE_CMD = "systemctl disable {}"
START_MSG_BUS_READER_CMD = "python3 read_message_bus.py"
ADD_SPARES_CMD = "add spares {} disk-group {}"
IP_LINK_CMD = "ip link set {} {}"
IF_CMD = "if{} {}"
CONF_GET_CMD = "conf '{}' get '{}'"
CONF_SET_CMD = "conf '{}' set '{}'"
GET_ALL_NW_IFCS_CMD = 'ls /sys/class/net'
IP_LINK_SHOW_CMD = "ip link show | grep {} | grep -o {}"
CMD_UPDATE_FILE = "echo {} > {}"
CMD_TOUCH_FILE = "touch {}"
LSSCSI_CMD = "lsscsi > {}"
LINUX_STRING_CMD = "sed '/{}/!d' {} > {}"
LINUX_REPLACE_STRING = "sed -i 's/{}/{}/g' {}"
LINUX_EXPORT = "export {}={}"
LINE_COUNT_CMD = "cat {} | wc -l"
DISCONNECT_OS_DRIVE_CMD = "echo 1 > /sys/block/{}/device/delete"
CONNECT_OS_DRIVE_CMD = 'echo "- - -" > /sys/class/scsi_host/host{}/scan'
GET_IFCS_STATUS = "ip -br -c addr show | grep -v lo | grep {}"
GET_INFCS_NAME_CMD = "ip a s | grep {} | awk '{{print $NF}}'"
GET_RAID_ARRAYS_CMD = "grep -oP '\\bmd[0-9]\\b' /proc/mdstat"
RAID_ARRAY_STATE_CMD = "cat /sys/block/{}/md/degraded"
GET_RAID_ARRAY_DETAILS_CMD = "grep -P '\\bmd[0-9]\\b' /proc/mdstat"
FDISK_RAID_PARTITION_CMD = "fdisk -l {} | grep -i raid | awk '{{print $1}}' > {}"
GET_DRIVE_HOST_NUM_CMD = "lsscsi | grep 'ATA' | grep {}: | awk '{{print $NF}}'"
FILE_COMPARE_CMD = "diff {} {}"
CMD_HARE_RESET = "/opt/seagate/cortx/hare/bin/hare_setup reset " \
                 "--config \'json:///opt/seagate/cortx_configs/provisioner_cluster.json\' " \
                 "--file /var/lib/hare/cluster.yaml"
PROV_CLUSTER = "jq . /opt/seagate/cortx_configs/provisioner_cluster.json"
DOS2UNIX_CMD = "yum install dos2unix -y; dos2unix {}"
GET_CLUSTER_PROCESSES_CMD = "consul kv get --recurse processes"

CMD_AWS_INSTALL = "make aws-install --makefile=scripts/s3_tools/Makefile"

# aws s3 commands
BUNDLE_CMD = "sh /opt/seagate/cortx/s3/scripts/s3_bundle_generate.sh"
CRASH_COMMANDS = ["ls -l /var/crash", "ls -lR /var/motr | grep core"]
S3_UPLOAD_FILE_CMD = "aws s3 cp {0} s3://{1}/{2}"
S3_UPLOAD_FOLDER_CMD = "aws s3 cp {0} s3://{1}/ --recursive --profile {2}"
S3_DOWNLOAD_BUCKET_CMD = "aws s3 cp --recursive s3://{} {} --profile {}"

# Commands used in RAS libs
SHOW_DISKS_CMD = "show disks"
"""File consists of the commands used in all the components."""
# RAS Commands
PCS_RESOURCE_DISABLE_ENABLE = "pcs resource {} {}"
SYSTEMCTL_STATUS = "systemctl status {}"
START_RABBITMQ_READER_CMD = "python3 /root/rabbitmq_reader.py {} {} {}"
REMOVE_UNWANTED_CONSUL = "/usr/bin/consul kv delete --recurse SSPL_"
CMD_SHOW_DISK_GROUP = "show disk-groups"
CMD_SHOW_XP_STATUS = "show expander-status"
CMD_SHOW_VOLUMES = "show volumes"
CMD_CLEAR_METADATA = "clear disk-metadata {}"
CHECK_SSPL_LOG_FILE = "tail -f /var/log/cortx/sspl/sspl.log > '{}' 2>&1 &"
SSPL_SERVICE_CMD = "journalctl -xefu sspl-ll.service"
SET_DRIVE_STATUS_CMD = "set expander-phy encl {} controller {} type drive phy {} {}"
ENCRYPT_PASSWORD_CMD = "python3 encryptor.py encrypt {} {} storage_enclosure"
GET_CLUSTER_ID_CMD = "salt-call grains.get cluster_id"
COPY_FILE_CMD = "cp -rfv {} {}"
KILL_PROCESS_CMD = "pkill -f {}"
UPDATE_STAT_FILE_CMD = "echo 'state=active' > {}"
FILE_MODE_CHANGE_CMD = "chmod +x {}"
SET_DEBUG_CMD = "set protocol debug enabled"
SIMULATE_FAULT_CTRL_CMD = "simulatefrufault -enclId {} -pos {} -fruIndex " \
                          "{} -cr {} -contrl {}"
COPY_LOGS_BACKUP = "cat {} >> {}"
EMPTY_FILE_CMD = "truncate -s 0 {}"
EXTRACT_LOG_CMD = "cat {} | grep '{}' > '/root/extracted_alert.log'"
SEL_INFO_CMD = "ipmitool sel info"
SEL_LIST_CMD = "ipmitool sel list"
IEM_LOGGER_CMD = "logger -i -p local3.err {}"
INSTALL_SCREEN_CMD = "yum -y install screen"
INSTALL_SSH_PASS_CMD = "yum -y install sshpass"  # nosec
SCREEN_CMD = "screen -d -m -L -S 'screen_RMQ' {}"
SSH_CMD = "sshpass -p {} ssh -o 'StrictHostKeyChecking no' {}@{} {}"
RESOLVE_FAN_FAULT = "ipmitool event {} {} deassert"
CPU_USAGE_CMD = "python3 -c 'import psutil; print(psutil.cpu_percent(interval=1))'"
CPU_USAGE_KEY = "cpu_usage_threshold"
STRING_MANIPULATION = "echo '{}' | tr -dc '[:alnum:]-'"
REBOOT_NODE_CMD = "init 6"
GENERATE_FAN_FAULT = "ipmitool event {} {}"
MDADM_CMD = "mdadm {}"
MDADM_UPDATE_CONFIG = "--detail --scan >"
MDADM_CREATE_ARRAY = "--create {} --run --level=1 --raid-devices={}"
MDADM_ASSEMBLE = "--assemble"
MDADM_STOP = "--stop"
MDADM_MANAGE = "--manage"
MDADM_FAIL = "--fail"
MDADM_REMOVE = "--remove"
MDADM_ADD = "--add"
IPMI_SDR_TYPE_CMD = "ipmitool sdr type"
IPMI_EVENT_CMD = "ipmitool event"

# BMC commands.
CHECK_IPMITOOL = "rpm -qa | grep ipmitool"
INSTALL_IPMITOOL = "yum install ipmitool -y"
CMD_LAN_INFO = "ipmitool lan print"
CMD_SET_LAN_IP_ADDR = "ipmitool lan set 1 ipaddr {}"  # parameter: IP address.
MSG_SET_LAN_IP_ADDR = "Setting LAN IP Address to {}"  # parameter: IP address.
CMD_PING = "ping -c1 -W1 -q {}"  # parameter: IP address.

# Fan fault/resolve commands.
CMD_FAN_FAULT = "fan_fault"
CMD_FAN_SPEED = "fan_set {} speed {}"
CMD_FAN_SET_NORMAL = "fan_set {} normal"
MDADM_ZERO_SUPERBLOCK = "--zero-superblock"
WIPE_DISK_CMD = "dd if=/dev/zero of={} &"
KILL_WIPE_DISK_PROCESS = "-x dd"
PCS_STATUS_CMD = "pcs status"
SELINUX_STATUS_CMD = "sestatus > {}"
IPMI_SDR_LIST_CMD = "ipmitool sdr list"

# Mock monitor commands.
PUBLISH_CMD = "{} publish -f {}"
GET_DATA_NODE_ID_CMD = "{} -gdt"
GET_SERVER_NODE_ID_CMD = "{} -gs"
GET_DISK_ID_CMD = "{} get-disks -n {}"
GET_CVG_ID_CMD = "{} get-cvgs -n {}"

# All the constants are alphabetically arranged.
"""All the constants are alphabetically arranged."""
PCS_RESOURCE_STATUS_CMD = "pcs resource show {}"
SYSTEM_CTL_RELOAD_CMD = "systemctl reload {}"
GET_PID_CMD = "systemctl status {}.service | grep PID"
KILL_CMD = "kill -9 {}"
PIDOF_CMD = "pidof {}"

# CORTXCLI Commands
CMD_LOGIN_CORTXCLI = "cortxcli"
CMD_LOGOUT_CORTXCLI = "exit"
CMD_CREATE_CSM_USER = "users create"
CMD_DELETE_CSM_USER = "users delete"
CMD_UPDATE_ROLE = "users update"
CMD_RESET_PWD = "users password"  # nosec
CMD_LIST_CSM_USERS = "users show"
CMD_HELP_OPTION = "-h"
CMD_S3ACC = "s3accounts"
CMD_CREATE_S3ACC = "s3accounts create"
CMD_SHOW_S3ACC = "s3accounts show"
CMD_DELETE_S3ACC = "s3accounts delete {}"
CMD_RESET_S3ACC_PWD = "s3accounts password {}"  # nosec
CMD_S3BKT_HELP = "s3buckets -h"
CMD_CREATE_BUCKET = "s3buckets create {}"
CMD_SHOW_BUCKETS = "s3buckets show"
CMD_DELETE_BUCKET = "s3buckets delete {}"
CREATE_IAM_USER = "s3iamusers create"
LIST_IAM_USER = "s3iamusers show"
DELETE_IAM_USER = "s3iamusers delete"
CMD_GENERATE_SUPPORT_BUNDLE = "support_bundle generate"
CMD_GENERATE_SUPPORT_BUNDLE_OS = "support_bundle generate {0} --os"
CMD_SUPPORT_BUNDLE_STATUS = "support_bundle status"
CMD_CREATE_BUCKET_POLICY = "s3bucketpolicy create"
CMD_DELETE_BUCKET_POLICY = "s3bucketpolicy delete"
CMD_SHOW_BUCKET_POLICY = "s3bucketpolicy show"
CMD_SYSTEM_STATUS = "system status"
CMD_SYSTEM_START = "system start"
CMD_SYSTEM_STOP = "system stop"
CMD_SYSTEM_SHUTDOWN = "system shutdown"
CMD_NODE_OPERATION = "cluster_management node {} -i {}"
CMD_CREATE_S3ACC_ACCESS_KEY = "s3accesskeys create {}"
CMD_SHOW_S3ACC_ACCESS_KEY = "s3accesskeys show {}"
CMD_CREATE_ACCESS_KEY = "s3accesskeys create -iu"
CMD_DELETE_ACCESS_KEY = "s3accesskeys delete"
CMD_SHOW_ACCESS_KEY = "s3accesskeys show -iu"
CMD_UPDATE_ACCESS_KEY = "s3accesskeys update"
CMD_HEALTH_SHOW = "health show \"{}\""
CMD_HEALTH_ID = "health show \"{}\" -i \"{}\""
CMD_RESET_IAM_PWD = "s3iamusers password {}"  # nosec

# Linux System Commands
CMD_MKDIR = "mkdir -p {}"
CMD_MOUNT = "mount -t nfs {} {}"
CMD_UMOUNT = "umount {}"
CMD_TAR = "tar -zxvf {} -C {}"
CMD_REMOVE_DIR = "rm -rf {}"
CMD_IFACE_IP = "netstat -ie | grep -B1 \"{}\" | head -n1 | awk '{{print $1}}'"
CMD_GET_IP_IFACE = "/sbin/ifconfig \"{}\" | awk '/inet / {{print $2}}'"
CMD_HOSTS = "cat /etc/hosts"
CMD_GET_NETMASK = "ifconfig | grep \"{}\" | awk '{{print $4}}'"
# Provisioner commands
CMD_LSBLK = "lsblk -S | grep disk | wc -l"
CMD_LSBLK_SIZE = "lsblk -r |grep disk| awk '{print $4}'"
CMD_NUM_CPU = "nproc"
CMD_OS_REL = "cat /etc/redhat-release"
CMD_KRNL_VER = "uname -r"
CMD_PRVSNR_VER = "provisioner --version"
CMD_LIST_DEVICES = "lsblk -nd -o NAME -e 11|grep -v sda|sed 's|sd|/dev/sd|g'|paste -s -d, -"
CMD_SETUP_PRVSNR = "provisioner setup_provisioner --logfile " \
                   "--logfile-filename /var/log/seagate/provisioner/setup.log --source rpm " \
                   "--config-path {0} " \
                   "--dist-type bundle " \
                   "--target-build {1} "
CMD_CONFIGURE_SETUP = "provisioner configure_setup {0} {1}"
CMD_CONFSTORE_EXPORT = "provisioner confstore_export"
CMD_DEPLOY_VM = "provisioner deploy_vm --setup-type {} --states {}"
CMD_PILLAR_DATA = "salt \"{}\" grains.get {}"
CMD_GET_SYSTEM_NTP = "salt \"{}\" pillar.get system"
CMD_SET_SYSTEM_NTP = "provisioner set_ntp --server {} --timezone '{}'"
GET_CHRONY = "grep '{}' /etc/chrony.conf"
CMD_CONFSTORE_TMPLT = "cat /opt/seagate/cortx_configs/provisioner_cluster.json | grep {}"
CMD_WGET = "wget {}"
CMD_SW_VER = "provisioner get_release_version"
CMD_SW_SET_REPO = "provisioner set_swupgrade_repo {0} --sig-file {1} --gpg-pub-key {2}"
CMD_ISO_VER = "provisioner get_iso_version"
CMD_SW_UP = "provisioner sw_upgrade --offline"
CMD_SPACE_CHK = "df -h"
CMD_FIND_FILE = "find /etc/cortx/ -name *.gz"
SET_NAMESPACE = "kubectl config set-context --current --namespace={}"

# Deployment commands
CMD_YUM_UTILS = "yum install -y yum-utils"
CMD_ADD_REPO_3RDPARTY = "yum-config-manager --add-repo \"{0}/3rd_party/\""
CMD_ADD_REPO_CORTXISO = "yum-config-manager --add-repo \"{0}/cortx_iso/\""
CMD_INSTALL_JAVA = "yum install --nogpgcheck -y java-1.8.0-openjdk-headless"
CMD_INSTALL_CORTX_PRE_REQ = "yum install --nogpgcheck -y python3 cortx-prereq sshpass"
CMD_INSTALL_PRVSNR_PRE_REQ = "yum install --nogpgcheck -y python36-m2crypto salt salt-master " \
                             "salt-minion"
CMD_INSTALL_PRVSNR_API = "yum install --nogpgcheck -y python36-cortx-prvsnr"
CMD_RM_3RD_PARTY_REPO = "rm -rf /etc/yum.repos.d/*3rd_party*.repo"
CMD_RM_CORTXISO_REPO = "rm -rf /etc/yum.repos.d/*cortx_iso*.repo"
CMD_YUM_CLEAN_ALL = "yum clean all"
CMD_RM_YUM_CACHE = "rm -rf /var/cache/yum/"
CMD_RM_PIP_CONF = "rm -rf /etc/pip.conf"
CMD_DEPLOY_SINGLE_NODE = "sshpass -p \"{0}\" provisioner auto_deploy_vm srvnode-1:{1} " \
                         "--logfile --logfile-filename /var/log/seagate/provisioner/setup.log " \
                         "--source rpm --config-path {2} --dist-type bundle " \
                         "--target-build {3}"
CMD_SALT_PILLAR_ENCRYPT = "salt-call state.apply components.system.config.pillar_encrypt"
CMD_SALT_PING = "salt '*' test.ping "
CMD_SALT_STOP_PUPPET = "salt '*' service.stop puppet"
CMD_SALT_DISABLE_PUPPET = "salt '*' service.disable puppet"
CMD_SALT_GET_RELEASE = "salt '*' pillar.get release"
CMD_SALT_GET_NODE_ID = "salt '*' grains.get node_id"
CMD_SALT_GET_CLUSTER_ID = "salt '*' grains.get cluster_id"
CMD_SALT_GET_ROLES = "salt '*' grains.get roles"
CMD_START_CLSTR = "cortx cluster start"
CMD_START_CLSTR_NEW = "cortx_setup cluster start"
CMD_STATUS_CLSTR = "cortx_setup cluster status"
CMD_STOP_CLSTR = "cortx cluster stop"
CMD_RD_LOG = "cat {0}"
CMD_PCS_STATUS_FULL = "pcs status --full"
CMD_PCS_SERV = "pcs status | grep {}"
CMD_PCS_GET_XML = "pcs status xml"
CMD_PCS_GREP = "pcs status --full | grep {}"
CMD_SALT_GET_HOST = 'salt "*" grains.get host'
# LDAP commands
CMD_GET_S3CIPHER_CONST_KEY = "s3cipher generate_key --const_key cortx"
CMD_DECRYPT_S3CIPHER_CONST_KEY = "s3cipher decrypt --key {} --data {}"

# S3 awscli  Commands
CMD_AWSCLI_CREATE_BUCKET = "aws s3 mb s3://{0}"
CMD_AWSCLI_DELETE_BUCKET = "aws s3 rb s3://{0}"
CMD_AWSCLI_LIST_BUCKETS = "aws s3 ls"
CMD_AWSCLI_PUT_OBJECT = "aws s3 cp {0} s3://{1}/{2}"
CMD_AWSCLI_HEAD_BUCKET = "aws s3api head-bucket --bucket {0}"
CMD_AWSCLI_GET_BUCKET_LOCATION = "aws s3api get-bucket-location --bucket {0}"
CMD_AWSCLI_LIST_OBJECTS = "aws s3 ls s3://{0}"
CMD_AWSCLI_REMOVE_OBJECTS = "aws s3 rm s3://{0}/{1}"
CMD_AWSCLI_RECURSIVE_FLAG = "--recursive"
CMD_AWSCLI_EXCLUDE_FLAG = "--exclude '{}'"
CMD_AWSCLI_INCLUDE_FLAG = "--include '{}'"
CMD_AWSCLI_CREATE_MULTIPART_UPLOAD = "aws s3api create-multipart-upload --bucket {0} --key {1}"
CMD_AWSCLI_LIST_MULTIPART_UPLOADS = "aws s3api list-multipart-uploads --bucket {0}"
CMD_AWSCLI_UPLOAD_PARTS = "aws s3api upload-part --bucket {0} --key {1} --part-number {2} " \
                          "--body {3} --upload-id {4}"
CMD_AWSCLI_LIST_PARTS = "aws s3api list-parts --bucket {0} --key {1} --upload-id {2}"
CMD_AWSCLI_COMPLETE_MULTIPART = "aws s3api complete-multipart-upload --multipart-upload " \
                                "file://{0} --bucket {1} --key {2} --upload-id {3}"
CMD_AWSCLI_DOWNLOAD_OBJECT = "aws s3 cp s3://{0}/{1} {2}"
CMD_AWS_CONF_KEYS = "make aws-configure --makefile=scripts/s3_tools/Makefile ACCESS={} SECRET={}"
CMD_AWS_CONF_KEYS_RGW = "make aws-rgw --makefile=scripts/s3_tools/Makefile ACCESS={} SECRET={} " \
                        "endpoint={}"
CMD_AWSCLI_CONF = "aws configure"
# Upload directory recursively to s3.
CMD_AWSCLI_UPLOAD_DIR_TO_BUCKET = "aws s3 sync {0} s3://{1}"
CMD_AWSCLI_LIST_OBJECTS_V2_BUCKETS = "aws s3api list-objects-v2 --bucket {0}"
CMD_AWSCLI_LIST_OBJECTS_V2_OPTIONS_BUCKETS = "aws s3api list-objects-v2 --bucket {0} {1}"

# jCloud commands.
CMD_KEYTOOL1 = "`keytool -delete -alias s3server -keystore /etc/pki/java/cacerts -storepass " \
               "changeit >/dev/null`"
# ca.crt path.
CMD_KEYTOOL2 = "`keytool -import -trustcacerts -alias s3server -noprompt -file {} -keystore " \
               "/etc/pki/java/cacerts -storepass changeit`"

# cortx_setup commands
CMD_RESOURCE_DISCOVER = "cortx_setup resource discover"
CMD_RESOURCE_SHOW_HEALTH = "cortx_setup resource show --health"
CMD_RESOURCE_SHOW_HEALTH_RES = "cortx_setup resource show --health --resource_type"

# FailtTolerance commands.
UPDATE_FAULTTOLERANCE = 'curl -i -H "x-seagate-faultinjection:{},offnonm,motr_obj_write_fail,2,1"' \
                        ' -X PUT http://127.0.0.1:28081'

# VM power operations:
CMD_VM_POWER_ON = "python3 scripts/ssc_cloud/ssc_vm_ops.py -a \"power_on\" " \
                  "-u \"{0}\" -p \"{1}\" -v \"{2}\""
CMD_VM_POWER_OFF = "python3 scripts/ssc_cloud/ssc_vm_ops.py -a \"power_off\" " \
                   "-u \"{0}\" -p \"{1}\" -v \"{2}\""
CMD_VM_INFO = "python3 scripts/ssc_cloud/ssc_vm_ops.py -a \"get_vm_info\" " \
              "-u \"{0}\" -p \"{1}\" -v \"{2}\""
CMD_VM_REVERT = "python3 scripts/ssc_cloud/ssc_vm_ops.py -a \"revert_vm_snap\" " \
                "-u \"{0}\" -p \"{1}\" -v \"{2}\""
CMD_VM_REFRESH = "python3 scripts/ssc_cloud/ssc_vm_ops.py -a \"refresh_vm\" " \
                 "-u \"{0}\" -p \"{1}\" -v \"{2}\""

CPU_COUNT = "cat /sys/devices/system/cpu/online"
CPU_FAULT = "echo 0 > /sys/devices/system/cpu/cpu{}/online"
CPU_RESOLVE = "echo 1 > /sys/devices/system/cpu/cpu{}/online"

CMD_BLOCKING_PROCESS = "yes > /dev/null &"
CMD_CPU_UTILIZATION = "python3 -c 'import psutil; print(psutil.cpu_percent(interval={0}))'"
CMD_GREP_PID = " ps | grep {0}"

CMD_AVAIL_MEMORY = "python3 -c 'import psutil; print(psutil.virtual_memory().available)'"
CMD_INSTALL_TOOL = "yum install {0}"
CMD_INCREASE_MEMORY = "stress --vm {0} --vm-bytes {1} --vm-keep -t {2}"
CMD_MEMORY_UTILIZATION = "python3 -c 'import psutil; print(psutil.virtual_memory().percent)'"
JMX_CMD = "sh {}/jmeter.sh -n -t {} -l {} -f -e -o {}"
SET_PIPEFAIL = "set -eu -o pipefail"

# Expect utils
CMD_PDU_POWER_ON = "expect scripts/expect_utils/expect_power_on.exp {0} {1} {2} {3}"
CMD_PDU_POWER_OFF = "expect scripts/expect_utils/expect_power_off.exp {0} {1} {2} {3}"
CMD_PDU_POWER_CYCLE = "expect scripts/expect_utils/expect_power_cycle.exp {0} {1} {2} {3} {4}"

# Ldap commands to fetch user, password.
LDAP_USER = "s3confstore properties:///opt/seagate/cortx/auth/resources/authserver.properties " \
            "getkey --key ldapLoginDN"
LDAP_PWD = ("s3cipher decrypt --data "  # nosec
            "$(s3confstore properties:///opt/seagate/cortx/auth/resources/"
            "authserver.properties getkey --key ldapLoginPW) --key $(s3cipher generate_key"
            " --const_key cortx)")

# Motr commands
M0CP = "m0cp -l {} -H {} -P {} -p {} -s {} -c {} -o {} -L {} {}"
M0CP_U = "m0cp -G -l {} -H {} -P {} -p {} -s {} -c {} -o {} -L {} -O {} -u {}"
# m0cp from data unit aligned offset 0
# m0cp -G -l inet:tcp:cortx-client-headless-svc-ssc-vm-rhev4-2620@21201
# -H inet:tcp:cortx-client-headless-svc-ssc-vm-rhev4-2620@22001 -p 0x7000000000000001:0x110
# -P 0x7200000000000001:0xae -s 4096 -c 10 -o 1048583 /root/infile -L 3
#
# m0cp -G -l inet:tcp:cortx-client-headless-svc-ssc-vm-rhev4-2620@21201
# -H inet:tcp:cortx-client-headless-svc-ssc-vm-rhev4-2620@22001 -p 0x7000000000000001:0x110
# -P 0x7200000000000001:0xae -s 4096 -c 1 -o 1048583 /root/myfile -L 3 -u -O 0


M0CAT = "m0cat -l {} -H {} -P {} -p {} -s {} -c {} -o {} -L {} {}"
M0UNLINK = "m0unlink -l {} -H {} -P {} -p {} -o {} -L {}"
M0KV = "m0kv -l {} -h {} -f {} -p {} {}"
DIFF = "diff {} {}"
MD5SUM = "md5sum {} {}"
GET_MD5SUM = "md5sum {}"
GETRPM = "rpm -qa| grep {}"
LIBFAB_VERSION = "fi_info --version | grep libfabric: |cut -d ' ' -f 2 | tr -d [:space:]"
LIBFAB_TCP = "fi_info -p tcp"
LIBFAB_SOCKET = "fi_info -p sockets"
LIBFAB_VERBS = "fi_info -p verbs"
FI_SERVER_CMD = "fi_pingpong -e msg -p {}"
FI_CLIENT_CMD = "fi_pingpong {} -e msg -p {}"

# Support Bundle
R2_CMD_GENERATE_SUPPORT_BUNDLE = "support_bundle generate"

# Deployment using Factory and Field
CMD_GET_PROV_INSTALL = "curl --create-dirs " \
                       "--output /mnt/cortx/install.sh {}; chmod +x /mnt/cortx/install.sh "
CMD_INSTALL_CORTX_RPM = "sh /mnt/cortx/install.sh -t {}"
CMD_SERVER_CFG = "cortx_setup server config --name {} --type {}"  # server name, type - VM/HW
CMD_GET_NETWORK_INTERFACE = "netstat -i | grep eth | awk '{print $1}'"
PUPPET_SERV = "puppet.service"
NETWORK_CFG_TRANSPORT = "cortx_setup network config --transport {} --mode tcp"
NETWORK_CFG_INTERFACE = "cortx_setup network config --interfaces {} --type {}"
NETWORK_CFG_BMC = "cortx_setup network config --bmc {} --user {} --password {}"
STORAGE_CFG_CONT = "cortx_setup storage config --controller virtual --mode {} " \
                   "--ip 127.0.0.1 --port 80 --user 'admin' --password 'admin'"
STORAGE_CFG_NAME = "cortx_setup storage config --name {} --type virtual"
STORAGE_CFG_CVG = "cortx_setup storage config --cvg {} --data-devices {} --metadata-devices {}"
SECURITY_CFG = "cortx_setup security config --certificate {}"
FEATURE_CFG = "cortx_setup config set --key {} --val {}"
FEATURE_GET_CFG = "cortx_setup config get --key {}"
INITIALIZE_NODE = "cortx_setup node initialize"
SET_NODE_SIGN = "cortx_setup signature set --key LR_SIGNATURE --value {}"
NODE_FINALIZE = "cortx_setup node finalize --force"
PREPARE_NODE = "cortx_setup node prepare server --site_id {} --rack_id {} --node_id {}"
PREPARE_NETWORK = "cortx_setup node prepare network --hostname {} --search_domains {} " \
                  "--dns_servers {}"
PREPARE_NETWORK_TYPE = "cortx_setup node prepare network --type {} --ip_address {} --netmask {} " \
                       "--gateway {}"
CFG_FIREWALL = "cortx_setup node prepare firewall --config {}"
CFG_NTP = "cortx_setup node prepare time --server time.seagate.com --timezone {}"
NODE_PREP_FINALIZE = "cortx_setup node prepare finalize"
CLUSTER_CREATE = "cortx_setup cluster create {} --name cortx_cluster --site_count 1 " \
                 "--storageset_count 1 --virtual_host {} --target_build {}"
CLUSTER_CREATE_SINGLE_NODE = "cortx_setup cluster create {} --name cortx_cluster --site_count 1 " \
                             "--storageset_count 1 --target_build {}"
CLUSTER_PREPARE = "cortx_setup cluster prepare"

STORAGE_SET_CREATE = "cortx_setup storageset create --name {} --count {}"
STORAGE_SET_ADD_NODE = "cortx_setup storageset add node {} {}"
STORAGE_SET_ADD_ENCL = "cortx_setup storageset add enclosure {} {}"
STORAGE_SET_CONFIG = "cortx_setup storageset config durability {} --type {} --data {} " \
                     "--parity {} --spare {}"
CLUSTER_CFG_COMP = "cortx_setup cluster config component --type {}"
CORTX_SETUP_HELP = "cortx_setup -h"
CORTX_CLUSTER_SHOW = "cortx_setup cluster show"
CLSTR_RESET_COMMAND = "cortx_setup cluster reset --type all"
CLSTR_RESET_H_COMMAND = "cortx_setup cluster reset -h"

# Maintenance mode for DI
HCTL_MAINTENANCE_MODE_CMD = "hctl node maintenance --all"
HCTL_UNMAINTENANCE_MODE_CMD = "hctl node unmaintenance --all"

# DI Flags
RUN_FI_FLAG = 'curl -X PUT -H "x-seagate-faultinjection: {},always,{},0,0" {}'
S3_FI_FLAG_DC_ON_WRITE = 'di_data_corrupted_on_write'
S3_FI_FLAG_DC_ON_READ = 'di_data_corrupted_on_read'
S3_FI_FLAG_CSUM_CORRUPT = 'di_obj_md5_corrupted'

S3_SRV_PORT = S3_SRV_START_PORT = 28081

# corrupts file before storing;
DI_DATA_CORRUPT_ON_WRITE = 'di_data_corrupted_on_write'

# corrupts file during retrieval;
DI_DATA_CORRUPT_ON_READ = 'di_data_corrupted_on_read'

# instead of md5 hash of the object stores md5 hash of empty string.
DI_MD5_CORRUPT = 'di_obj_md5_corrupted'

FI_ENABLE = 'enable'
FI_DISABLE = 'disable'
FI_TEST = 'test'
# Kubernetes commands to interact with service/pods.
LDAP_SEARCH_DATA = ("ldapsearch -x -b \"dc=s3,dc=seagate,dc=com\" -H ldap://{0}"
                    + " -D \"cn={1},dc=seagate,dc=com\" -w {2}")
K8S_LDAP_CMD = "kubectl exec -it openldap-0 -- /bin/bash -c \"{}\""
K8S_SVC_CMD = "kubectl get svc"
K8S_TAINT_NODE = "kubectl taint node {} node-role.kubernetes.io/master=:NoSchedule"
K8S_REMOVE_TAINT_NODE = "kubectl taint node {} node-role.kubernetes.io/master=:NoSchedule-"
K8S_CHK_TAINT = "kubectl describe node {} | grep Taints"
K8S_CP_TO_LOCAL_CMD = "kubectl cp {}:{} {} -c {}"
K8S_CP_PV_FILE_TO_LOCAL_CMD = "kubectl cp {}:{} {}"
K8S_CP_TO_CONTAINER_CMD = "kubectl cp {} {}:{} -c {}"
K8S_GET_PODS = "kubectl get pods"
K8S_GET_MGNT = "kubectl get pods -o wide"
K8S_DELETE_POD = "kubectl delete pod {}"
K8S_HCTL_STATUS = "kubectl exec -it {} -c cortx-hax -- hctl status --json"
K8S_WORKER_NODES = "kubectl get nodes -l node-role.kubernetes.io/worker=worker | awk '{print $1}'"
K8S_MASTER_NODE = "kubectl get nodes -l node-role.kubernetes.io/master | awk '{print $1}'"
K8S_GET_SVC_JSON = "kubectl get svc -o json"
K8S_POD_INTERACTIVE_CMD = "kubectl exec -it {} -c cortx-hax -- {}"
K8S_DATA_POD_SERVICE_STATUS = "consul kv get -recurse | grep s3 | grep name"
K8S_CONSUL_UPDATE_CMD = 'kubectl exec -it {} -c {} -- {}'
GET_STATS = "consul kv get -recurse stats"
GET_BYTECOUNT = "consul kv get -recurse bytecount"

# Kubectl command prefix
KUBECTL_CMD = "kubectl {} {} -n {} {}"
KUBECTL_GET_DEPLOYMENT = "kubectl get deployment"
KUBECTL_GET_POD_CONTAINERS = "kubectl get pods {} -o jsonpath='{{.spec.containers[*].name}}'"
KUBECTL_GET_POD_IPS = 'kubectl get pods --no-headers -o ' \
                      'custom-columns=":metadata.name,:.status.podIP"'
KUBECTL_GET_POD_NAMES = 'kubectl get pods --no-headers -o custom-columns=":metadata.name"'
KUBECTL_GET_REPLICASET = "kubectl get rs | grep '{}'"
KUBECTL_GET_POD_DETAILS = "kubectl get pods --show-labels | grep '{}'"
KUBECTL_CREATE_REPLICA = "kubectl scale --replicas={} deployment/{}"
KUBECTL_DEL_DEPLOY = "kubectl delete deployment {}"
KUBECTL_DEPLOY_BACKUP = "kubectl get deployment {} -o yaml > {}"
KUBECTL_RECOVER_DEPLOY = "kubectl create -f {}"
KUBECTL_GET_POD_HOSTNAME = "kubectl exec -it {} -c cortx-hax -- hostname"
KUBECTL_GET_RECENT_POD = "kubectl get pods --sort-by=.metadata.creationTimestamp -o " \
                         "jsonpath='{{.items[-1:].metadata.name}}'"
KUBECTL_GET_POD_DEPLOY = "kubectl get pods -l app={} -o custom-columns=:metadata.name"
KUBECTL_GET_RECENT_POD_DEPLOY = "kubectl get pods -l app={} -o custom-columns=:metadata.name " \
                                "--sort-by=.metadata.creationTimestamp -o " \
                                "jsonpath='{{.items[-1:].metadata.name}}'"

KUBECTL_GET_RPM = "kubectl exec -it {} -c {} -- rpm -qa|grep -i {}"
KUBECTL_SET_CONTEXT = "kubectl config set-context --current --namespace={}"
KUBECTL_GET_TAINT_NODES = "kubectl get nodes -o custom-columns=" \
                          "NAME:.metadata.name,TAINTS:.spec.taints --no-headers > {}"
KUBECTL_GET_ALL = "kubectl get all -A >> {}"
KUBECTL_GET_SCT = "kubectl get {} -A >> {}"
KUBECTL_GET_PVC = "kubectl get pvc -A >> {}"
KUBECTL_GET_PV = "kubectl get pv >> {}"
GET_IMAGE_VERSION = "kubectl describe po {} | grep Image:"
K8S_CHANGE_POD_NODE = "kubectl patch deploy/{} --type='json' "\
                      "-p='[{{\"op\":\"replace\", \"path\":\"/spec/template/spec/nodeSelector\", "\
                      "\"value\":{{\"kubernetes.io/hostname\":{}}} }}]'"
KUBECTL_CREATE_NAMESPACE = "kubectl create ns {}"
KUBECTL_GET_NAMESPACE = "kubectl get ns"
KUBECTL_DEL_NAMESPACE = "kubectl delete ns {}"

# Fetch logs of a pod/service in a namespace.
FETCH_LOGS = ""

# Helm commands
HELM_LIST = "helm list"
HELM_STATUS = "helm status {}"
HELM_HISTORY = "helm history {}"
HELM_ROLLBACK = "helm rollback {} {}"
HELM_GET_VALUES = "helm get values {}"

# LC commands
CLSTR_START_CMD = "cd {}; ./start-cortx-cloud.sh"
CLSTR_STOP_CMD = "cd {}; ./shutdown-cortx-cloud.sh"
CLSTR_STATUS_CMD = "cd {}; ./status-cortx-cloud.sh"
CLSTR_LOGS_CMD = "cd {}; ./logs-cortx-cloud.sh"
PRE_REQ_CMD = "cd $dir; ./prereq-deploy-cortx-cloud.sh -p -d $disk"
DEPLOY_CLUSTER_CMD = "cd $path; ./deploy-cortx-cloud.sh > $log"
DESTROY_CLUSTER_CMD = "cd $dir; ./destroy-cortx-cloud.sh --force"
UPGRADE_CLUSTER_CMD = "cd $dir; ./upgrade-cortx-cloud.sh start -p $pod"

# Incomplete commands
UPGRADE_NEG_CMD = "cd $dir; ./upgrade-cortx-cloud.sh"

CMD_POD_STATUS = "kubectl get pods"
CMD_SRVC_STATUS = "kubectl get services"
CMD_GET_NODE = "kubectl get nodes"

# LC deployment
CMD_MKFS_EXT4 = "mkfs.ext4 -F {}"
CMD_MOUNT_EXT4 = "mount -t ext4 {} {}"
CMD_CURL = "curl -o $file $url"

# Git commands
CMD_GIT_CLONE = "git clone {}"
CMD_GIT_CLONE_TEMPLATE = "git clone"
CMD_GIT_CLONE_D = "git clone {} {}"
CMD_GIT_CHECKOUT = "git checkout {}"

# docker commands
CMD_DOCKER_LOGIN = "docker login -u '{}' -p '{}'"
CMD_DOCKER_PULL = "docker pull {}"

# Deployment using Field User
FIELD_PREPARE_NODE = "node prepare server --site_id {} --rack_id {} --node_id {}"
FIELD_PREPARE_NETWORK = "node prepare network --hostname {} --search_domains {} " \
                        "--dns_servers {}"
FIELD_PREPARE_NETWORK_TYPE = "node prepare network --type {} --ip_address {} --netmask {} " \
                             "--gateway {}"
FIELD_CFG_FIREWALL = "node prepare firewall --config {}"
FIELD_CFG_NTP = "node prepare time --server time.seagate.com --timezone {}"
FIELD_NODE_PREP_FINALIZE = "node prepare finalize"
FIELD_CLUSTER_CREATE = "cluster create {} --name cortx_cluster --site_count 1 " \
                       "--storageset_count 1 --virtual_host {} --target_build {}"
FIELD_CLUSTER_CREATE_SINGLE_NODE = "cluster create {} --name cortx_cluster --site_count 1 " \
                                   "--storageset_count 1 --target_build {}"
FIELD_STORAGE_SET_CREATE = "storageset create --name {} --count {}"
FIELD_STORAGE_SET_ADD_NODE = "storageset add node {} {}"
FIELD_STORAGE_SET_ADD_ENCL = "storageset add enclosure {} {}"
FIELD_STORAGE_SET_CONFIG = "storageset config durability {} --type {} --data {} " \
                           "--parity {} --spare {}"
FIELD_CLUSTER_PREPARE = "cluster prepare"
FIELD_CLUSTER_CFG_COMP = "cluster config component --type {}"

# LC Support Bundle
SUPPORT_BUNDLE_LC = "/opt/seagate/cortx/utils/bin/cortx_support_bundle generate " \
                    "-c yaml:///etc/cortx/cluster.conf -t {} -b {} -m \"{}\""
SUPPORT_BUNDLE_STATUS_LC = "/opt/seagate/cortx/utils/bin/cortx_support_bundle get_status -b {}"

# SNS repair
SNS_REPAIR_CMD = "hctl repair {}"
SNS_REBALANCE_CMD = "hctl rebalance {}"
CHANGE_DISK_STATE_USING_HCTL = "hctl drive-state --json $(jq --null-input --compact-output "\
                                " '{node : \"cortx_nod\", source_type : \"drive\", "\
                                " device : \"device_val\", state : \"status_val\"}')"
# Procpath Collection
PROC_CMD = "pid=$(echo $(pgrep m0d; pgrep radosgw; pgrep hax) | sed -z 's/ /,/g'); procpath " \
           "record -i 45 -d {} -p $pid"
