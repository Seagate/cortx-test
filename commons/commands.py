"""All the constants are alphabetically arranged."""
CREATE_FILE = "dd if={} of={} bs={} count={}"
FIREWALL_CMD = "firewall-cmd --service={} --get-ports --permanent"
GREP_PCS_SERVICE_CMD = "pcs status | grep {}"
LS_CMD = "ls {}"
LST_PRVSN_DIR = "ls /opt/seagate/"
LST_RPM_CMD = "rpm -qa | grep eos-prvsnr"
MEM_USAGE_CMD = "python3 -c 'import psutil; print(psutil.virtual_memory().percent)'"
MOTR_START_FIDS = "hctl mero process start --fid {}"
MOTR_STATUS_CMD = "hctl status"
MOTR_STOP_FIDS = "hctl mero process stop --fid {} --force"
HCTL_STATUS_CMD_JSON = "hctl status --json"
NETSAT_CMD = "netstat -tnlp | grep {}"
PCS_CLUSTER_START = "pcs cluster start {}"
PCS_CLUSTER_STOP = "pcs cluster stop {}"
PCS_CLUSTER_STATUS = "pcs cluster status"
PCS_RESOURCES_CLEANUP = "pcs resource cleanup {}"
PCS_RESOURCE_SHOW_CMD = "pcs resource show"
PCS_RESOURCE_RESTART_CMD = "pcs resource restart {}"
PCS_RESOURCE_ENABLE_CMD = "pcs resource enable {}"
PCS_RESOURCE_DISABLE_CMD = "pcs resource disable {}"
PCS_RESOURCE_CMD = "pcs resource {} {} {}"
PGREP_CMD = "sudo pgrep {}"
PKIL_CMD = "pkill {}"
RPM_GREP_CMD = "rpm -qa | grep {}"
RPM_INSTALL_CMD = "yum install -y {0}"
SYSTEM_CTL_CMD = "systemctl {} {}"
SYSTEM_CTL_STATUS_CMD = "systemctl status {}"
SYSTEM_CTL_RESTART_CMD = "systemctl restart {}"
SYSTEM_CTL_START_CMD = "systemctl start {}"
SYSTEM_CTL_STOP_CMD = "systemctl stop {}"
START_MSG_BUS_READER_CMD = "python3 read_message_bus.py"
ADD_SPARES_CMD = "add spares {} disk-group {}"
IP_LINK_CMD = "ip link set {} {}"
CONF_GET_CMD = "conf '{}' get '{}'"
CONF_SET_CMD = "conf '{}' set '{}'"
GET_ALL_NW_IFCS_CMD = 'ls /sys/class/net'
IP_LINK_SHOW_CMD = "ip link show | grep {} | grep -o {}"
CMD_UPDATE_FILE = "echo {} > {}"
CMD_TOUCH_FILE = "touch {}"
LSSCSI_CMD = "lsscsi > {}"
LINUX_STRING_CMD = "sed '/{}/!d' {} > {}"
LINE_COUNT_CMD = "cat {} | wc -l"
DISCONNECT_OS_DRIVE_CMD = "echo 1 > /sys/block/{}/device/delete"
CONNECT_OS_DRIVE_CMD = 'echo "- - -" > /sys/class/scsi_host/host{}/scan'
GET_IFCS_STATUS = "ip -br -c addr show | grep -v lo | grep {}"
GET_RAID_ARRAYS_CMD = "grep -oP '\\bmd[0-9]\\b' /proc/mdstat"
RAID_ARRAY_STATE_CMD = "cat /sys/block/{}/md/degraded"
GET_RAID_ARRAY_DETAILS_CMD = "grep -P '\\bmd[0-9]\\b' /proc/mdstat"
FDISK_RAID_PARTITION_CMD = "fdisk -l {} | grep -i raid | awk '{{print $1}}' > {}"
GET_DRIVE_HOST_NUM_CMD = "lsscsi | grep 'ATA' | grep {}: | awk '{{print $NF}}'"
FILE_COMPARE_CMD = "diff {} {}"


# S3IAMCLI Commands
BUNDLE_CMD = "sh /opt/seagate/cortx/s3/scripts/s3_bundle_generate.sh"
CRASH_COMMANDS = ["ls -l /var/crash", "ls -lR /var/motr | grep core"]
CREATE_ACC_USR_S3IAMCLI = "s3iamcli CreateUser -n {} --access_key={} --secret_key={}"
CMD_LIST_ACC = "s3iamcli Listaccounts --ldapuser={} --ldappasswd={}"
CMD_LST_USR = "s3iamcli ListUsers --access_key={} --secret_key={}"
CMD_CREATE_ACC = "s3iamcli CreateAccount -n {} -e {} --ldapuser={} --ldappasswd={}"
CMD_DEL_ACC = "s3iamcli deleteaccount -n {} --access_key={} --secret_key={}"
CMD_DEL_ACC_FORCE = "s3iamcli deleteaccount -n {} --access_key={} --secret_key={} --force"
UPDATE_ACC_LOGIN_PROFILE = "s3iamcli UpdateAccountLoginProfile -n {} --access_key={}" \
                           " --secret_key={}"
UPDATE_USR_LOGIN_PROFILE = "s3iamcli UpdateUserLoginProfile -n {} --access_key={} --secret_key={}"
GET_ACC_PROFILE = "s3iamcli GetAccountLoginProfile -n {} --access_key={} --secret_key={}"
GET_TEMP_ACC_DURATION = "s3iamcli GetTempAuthCredentials -a {} --password {} -d {}"
GET_TEMP_ACC = "s3iamcli GetTempAuthCredentials -a {} --password {}"
GET_TEMP_USR_DURATION = "s3iamcli GetTempAuthCredentials -a {} -n {} --password {} -d {}"
GET_TEMP_USR = "s3iamcli GetTempAuthCredentials -a {} -n {} --password {}"
CMD_CHANGE_PWD = "s3iamcli ChangePassword --old_password {} --new_password {} --access_key={} " \
                 "--secret_key={}"
CREATE_USR_PROFILE_PWD_RESET = "s3iamcli CreateUserLoginProfile -n {} --password={}" \
                               " --access_key={} --secret_key={} --password-reset-required"
CREATE_USR_PROFILE_NO_PWD_RESET = "s3iamcli CreateUserLoginProfile -n {} --password={} " \
                                  "--access_key={} --secret_key={} --no-password-reset-required"
CREATE_ACC_PROFILE_PWD_RESET = "s3iamcli CreateAccountLoginProfile -n {} --password={} " \
                               "--access_key={} --secret_key={} --password-reset-required"
CREATE_ACC_PROFILE_WITHOUT_BOTH_RESET = "s3iamcli CreateAccountLoginProfile -n {} --password={}" \
                                        " --access_key={} --secret_key={}"
CREATE_ACC_RROFILE_NO_PWD_RESET = "s3iamcli CreateAccountLoginProfile -n {} --password={} " \
                                  "--access_key={} --secret_key={} --no-password-reset-required"
CREATE_ACC_RROFILE_WITH_BOTH_RESET = "s3iamcli CreateAccountLoginProfile -n {} --password={} " \
                                     "--access_key={} --secret_key={} --password-reset-required " \
                                     "--no-password-reset-required"
UPDATE_ACC_PROFILE_RESET = "s3iamcli UpdateAccountLoginProfile -n {} --password={} " \
                           "--access_key={} --secret_key={} --password-reset-required"
UPDATE_ACC_PROFILE_NO_RESET = "s3iamcli UpdateAccountLoginProfile -n {} --password={} " \
                              "--access_key={} --secret_key={} --no-password-reset-required"
UPDATE_ACC_PROFILE_BOTH_RESET = "s3iamcli UpdateAccountLoginProfile -n {} --password={} " \
                                "--access_key={} --secret_key={} --password-reset-required " \
                                "--no-password-reset-required"
UPDATE_USR_PROFILE_RESET = "s3iamcli UpdateUserLoginProfile -n {} --password={} --access_key={} " \
                           "--secret_key={} --password-reset-required"
UPDATE_ACC_PROFILE = "s3iamcli UpdateUserLoginProfile -n {} --password={} --access_key={} " \
                     "--secret_key={} --no-password-reset-required"
UPDATE_USR_PROFILE_BOTH_RESET = "s3iamcli UpdateUserLoginProfile -n {0} --password={1} " \
                                "--access_key={2} --secret_key={3} --password-reset-required " \
                                "--no-password-reset-required"
GET_USRLOGING_PROFILE = "s3iamcli GetUserLoginProfile -n {} --access_key={} --secret_key={}"
CREATE_USR_LOGIN_PROFILE_NO_RESET = "s3iamcli CreateUserLoginProfile -n {} --password={} " \
                                    "--access_key={} --secret_key={} --password-reset-required " \
                                    "--no-password-reset-required"
CREATE_USR_LOGIN_PROFILE = "s3iamcli CreateUserLoginProfile -n {} --password={} --access_key={} " \
                           "--secret_key={}"
RESET_ACCESS_ACC = "s3iamcli resetaccountaccesskey -n {} --ldapuser={} --ldappasswd={}"
DEL_ACNT_USING_TEMP_CREDS = "s3iamcli deleteaccount -n {} --access_key={} --secret_key={} " \
                            "--session_token={}"
DEL_ACNT_USING_TEMP_CREDS_FORCE = "s3iamcli deleteaccount -n {} --access_key={} --secret_key={} " \
                                  "--session_token={} --force"
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
SET_DRIVE_STATUS_CMD = "set expander-phy encl {} controller {} type drive phy" \
                       " {} {}"
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
INSTALL_SSH_PASS_CMD = "yum -y install sshpass"
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

# BMC commands.
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

# All the constants are alphabetically arranged.
"""All the constants are alphabetically arranged."""
PCS_RESOURCE_STATUS_CMD = "pcs resource show {}"
SYSTEM_CTL_RELOAD_CMD = "systemctl reload {}"
GET_PID_CMD = "systemctl status {}.service | grep PID"
KILL_CMD = "kill -9 {}"

# CORTXCLI Commands
CMD_LOGIN_CORTXCLI = "cortxcli"
CMD_LOGOUT_CORTXCLI = "exit"
CMD_CREATE_CSM_USER = "users create"
CMD_DELETE_CSM_USER = "users delete"
CMD_UPDATE_ROLE = "users update"
CMD_RESET_PWD = "users password"
CMD_LIST_CSM_USERS = "users show"
CMD_HELP_OPTION = "-h"
CMD_S3ACC = "s3accounts"
CMD_CREATE_S3ACC = "s3accounts create"
CMD_SHOW_S3ACC = "s3accounts show"
CMD_DELETE_S3ACC = "s3accounts delete {}"
CMD_RESET_S3ACC_PWD = "s3accounts password {}"
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
CMD_CREATE_S3ACC_ACCESS_KEY = "s3accesskeys create {}"
CMD_SHOW_S3ACC_ACCESS_KEY = "s3accesskeys show {}"
CMD_CREATE_ACCESS_KEY = "s3accesskeys create -iu"
CMD_DELETE_ACCESS_KEY = "s3accesskeys delete"
CMD_SHOW_ACCESS_KEY = "s3accesskeys show -iu"
CMD_UPDATE_ACCESS_KEY = "s3accesskeys update"
CMD_HEALTH_SHOW = "health show \"{}\""
CMD_HEALTH_ID = "health show \"{}\" -i \"{}\""
CMD_RESET_IAM_PWD = "s3iamusers password {}"

# Linux System Commands
CMD_MKDIR = "mkdir -p {}"
CMD_MOUNT = "mount -t nfs {} {}"
CMD_UMOUNT = "umount {}"
CMD_TAR = "tar -zxvf {} -C {}"
CMD_REMOVE_DIR = "rm -rf {}"
CMD_IFACE_IP = "netstat -ie | grep -B1 \"{}\" | head -n1 | awk '{{print $1}}'"
CMD_HOSTS = "cat /etc/hosts"

# Provisioner commands
CMD_LSBLK = "lsblk -S | grep disk | wc -l"
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

# Deployment commands
CMD_YUM_UTILS = "yum install -y yum-utils"
CMD_ADD_REPO_3RDPARTY = "yum-config-manager --add-repo \"{0}/3rd_party/\""
CMD_ADD_REPO_CORTXISO = "yum-config-manager --add-repo \"{0}/cortx_iso/\""
CMD_INSTALL_JAVA = "yum install --nogpgcheck -y java-1.8.0-openjdk-headless"
CMD_INSTALL_CORTX_PRE_REQ = "yum install --nogpgcheck -y python3 cortx-prereq sshpass"
CMD_INSTALL_PRVSNR_PRE_REQ = "yum install --nogpgcheck -y python36-m2crypto salt salt-master salt-minion"
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
CMD_RD_LOG = "cat {0}"
CMD_PCS_STATUS_FULL = "pcs status --full"
CMD_PCS_SERV = "pcs status | grep {}"
CMD_PCS_GET_XML = "pcs status xml"
CMD_PCS_GREP = "pcs status --full | grep {}"
CMD_SALT_GET_HOST = 'salt "*" grains.get host'
# LDAP commands
CMD_GET_S3CIPHER_CONST_KEY = "s3cipher generate_key --const_key cortx"
CMD_DECRYPT_S3CIPHER_CONST_KEY = "s3cipher decrypt --key {​}​ --data {​}​"

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
# Upload directory recursively to s3.
CMD_AWSCLI_UPLOAD_DIR_TO_BUCKET = "aws s3 sync {0} s3://{1}"
CMD_AWSCLI_LIST_OBJECTS_V2_BUCKETS = "aws s3api list-objects-v2 --bucket {0}"
CMD_AWSCLI_LIST_OBJECTS_V2_OPTIONS_BUCKETS = "aws s3api list-objects-v2 --bucket {0} {1}"

# jCloud commands.
CMD_KEYTOOL1 = "`keytool -delete -alias s3server -keystore /etc/pki/java/cacerts -storepass changeit >/dev/null`"
# ca.crt path.
CMD_KEYTOOL2 = "`keytool -import -trustcacerts -alias s3server -noprompt -file {} -keystore /etc/pki/java/cacerts -storepass changeit`"

# S3 bench
CMD_S3BENCH = "go run s3bench -accessKey={} -accessSecret={} -bucket={} -endpoint={} " \
              "-numClients={} -numSamples={} -objectNamePrefix={} -objectSize={}"

#cortx_setup commands
CMD_RESOURCE_DISCOVER = "cortx_setup resource discover"
CMD_RESOURCE_SHOW_HEALTH = "cortx_setup resource show --health"

# FailtTolerance commands.
UPDATE_FAULTTOLERANCE = 'curl -i -H "x-seagate-faultinjection:{},offnonm,motr_obj_write_fail,2,1"' \
                        ' -X PUT http://127.0.0.1:28081​'

# VM power operations:
CMD_VM_POWER_ON = "python3 scripts/ssc_cloud/ssc_vm_ops.py -a \"power_on\" " \
                  "-u \"{0}\" -p \"{1}\" -v \"{2}\""
CMD_VM_POWER_OFF = "python3 scripts/ssc_cloud/ssc_vm_ops.py -a \"power_off\" " \
                  "-u \"{0}\" -p \"{1}\" -v \"{2}\""
CMD_VM_INFO = "python3 scripts/ssc_cloud/ssc_vm_ops.py -a \"get_vm_info\" " \
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
CMD_BLOCKING_PROCESS = "yes > /dev/null &"
CMD_CPU_UTILIZATION = "python3 -c 'import psutil; print(psutil.cpu_percent(interval=30))'"
CMD_GREP_PID = " ps | grep {0}"
