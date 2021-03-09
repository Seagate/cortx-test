"""File consists of the commands used in all the components."""
# RAS Commands
PCS_RESOURCE_DISABLE_ENABLE = "pcs resource {} {}"
SYSTEMCTL_STATUS = "systemctl status {}"
START_RABBITMQ_READER_CMD = "python3 /root/rabbitmq_reader.py {} {} {}"
REMOVE_UNWANTED_CONSUL = "/usr/bin/consul kv delete --recurse SSPL_"
SHOW_DISKS_CMD = "show disks"
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
CPU_USAGE_CMD = "python3 -c 'import psutil; print(psutil." \
                "cpu_times_percent(interval=1)[2])'"
CPU_USAGE_KEY = "cpu_usage_threshold"
STRING_MANIPULATION = "echo '{}' | tr -dc '[:alnum:]-'"
REBOOT_NODE_CMD = "init 6"
GENERATE_FAN_FAULT = "ipmitool event {} {}"
MEM_USAGE_CMD = "python3 -c 'import psutil; " \
                "print(psutil.virtual_memory().percent)'"
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
CREATE_FILE = "dd if={} of={} bs={} count={}"
FIREWALL_CMD = "firewall-cmd --service={} --get-ports --permanent"
GREP_PCS_SERVICE_CMD = "pcs status | grep {}"
LS_CMD = "ls {}"
LST_PRVSN_DIR = "ls /opt/seagate/"
LST_RPM_CMD = "rpm -qa | grep eos-prvsnr"
MOTR_START_FIDS = "hctl mero process start --fid {}"
MOTR_STATUS_CMD = "hctl status"
MOTR_STOP_FIDS = "hctl mero process stop --fid {} --force"
NETSAT_CMD = "netstat -tnlp | grep {}"
PCS_CLUSTER_START = "pcs cluster start {}"
PCS_CLUSTER_STOP = "pcs cluster stop {}"
PCS_RESOURCES_CLEANUP = "pcs resource cleanup {}"
PCS_RESOURCE_SHOW_CMD = "pcs resource show"
PCS_RESOURCE_RESTART_CMD = "pcs resource restart {}"
PCS_RESOURCE_ENABLE_CMD = "pcs resource enable {}"
PCS_RESOURCE_DISABLE_CMD = "pcs resource disable {}"
PCS_RESOURCE_STATUS_CMD = "pcs resource show {}"
PGREP_CMD = "sudo pgrep {}"
PKIL_CMD = "pkill {}"
RPM_GREP_CMD = "rpm -qa | grep {}"
RPM_INSTALL_CMD = "yum install -y {0}"
SYSTEM_CTL_CMD = "systemctl {} {}"
SYSTEM_CTL_STATUS_CMD = "systemctl status {}"
SYSTEM_CTL_RESTART_CMD = "systemctl restart {}"
SYSTEM_CTL_START_CMD = "systemctl start {}"
SYSTEM_CTL_STOP_CMD = "systemctl stop {}"
GET_PID_CMD = "systemctl status {}.service | grep PID"
KILL_CMD = "kill -9 {}"

# S3IAMCLI Commands
BUNDLE_CMD = "sh /opt/seagate/cortx/s3/scripts/s3_bundle_generate.sh"
CRASH_COMMANDS = ["ls -l /var/crash", "ls -lR /var/motr | grep core"]
CREATE_ACC_USR_S3IAMCLI = "s3iamcli CreateUser -n {} --access_key={} " \
                          "--secret_key={}"
CMD_LIST_ACC = "s3iamcli Listaccounts --ldapuser={} --ldappasswd={}"
CMD_LST_USR = "s3iamcli ListUsers --access_key={} --secret_key={}"
CMD_CREATE_ACC = "s3iamcli CreateAccount -n {} -e {} --ldapuser={} " \
                 "--ldappasswd={}"
CMD_DEL_ACC = "s3iamcli deleteaccount -n {} --access_key={} --secret_key={}"
CMD_DEL_ACC_FORCE = "s3iamcli deleteaccount -n {} --access_key={} " \
                    "--secret_key={} --force"
UPDATE_ACC_LOGIN_PROFILE = "s3iamcli UpdateAccountLoginProfile -n {} " \
                           "--access_key={} --secret_key={}"
UPDATE_USR_LOGIN_PROFILE = "s3iamcli UpdateUserLoginProfile -n {} " \
                           "--access_key={} --secret_key={}"
GET_ACC_PROFILE = "s3iamcli GetAccountLoginProfile -n {} --access_key={} " \
                  "--secret_key={}"
GET_TEMP_ACC_DURATION = "s3iamcli GetTempAuthCredentials -a {} --password {} " \
                        "-d {}"
GET_TEMP_ACC = "s3iamcli GetTempAuthCredentials -a {} --password {}"
GET_TEMP_USR_DURATION = "s3iamcli GetTempAuthCredentials -a {} -n {} " \
                        "--password {} -d {}"
GET_TEMP_USR = "s3iamcli GetTempAuthCredentials -a {} -n {} --password {}"
CMD_CHANGE_PWD = "s3iamcli ChangePassword --old_password {} --new_password " \
                 "{} --access_key={} --secret_key={}"
CREATE_USR_PROFILE_PWD_RESET = "s3iamcli CreateUserLoginProfile -n {} " \
                               "--password={} --access_key={} --secret_key={}" \
                               " --password-reset-required"
CREATE_USR_PROFILE_NO_PWD_RESET = "s3iamcli CreateUserLoginProfile -n {} " \
                                  "--password={} --access_key={} " \
                                  "--secret_key={} --no-password-reset-required"
CREATE_ACC_PROFILE_PWD_RESET = "s3iamcli CreateAccountLoginProfile -n {} " \
                               "--password={} --access_key={} --secret_key={}" \
                               " --password-reset-required"
CREATE_ACC_PROFILE_WITHOUT_BOTH_RESET = "s3iamcli CreateAccountLoginProfile " \
                                        "-n {} --password={} --access_key={} " \
                                        "--secret_key={}"
CREATE_ACC_RROFILE_NO_PWD_RESET = "s3iamcli CreateAccountLoginProfile -n {} " \
                                  "--password={} --access_key={} " \
                                  "--secret_key={} --no-password-reset-required"
CREATE_ACC_RROFILE_WITH_BOTH_RESET = "s3iamcli CreateAccountLoginProfile -n " \
                                     "{} --password={} --access_key={} " \
                                     "--secret_key={} " \
                                     "--password-reset-required " \
                                     "--no-password-reset-required"
UPDATE_ACC_PROFILE_RESET = "s3iamcli UpdateAccountLoginProfile -n {} " \
                           "--password={} --access_key={} --secret_key={} " \
                           "--password-reset-required"
UPDATE_ACC_PROFILE_NO_RESET = "s3iamcli UpdateAccountLoginProfile -n {} " \
                              "--password={} --access_key={} --secret_key={} " \
                              "--no-password-reset-required"
UPDATE_ACC_PROFILE_BOTH_RESET = "s3iamcli UpdateAccountLoginProfile -n {} " \
                                "--password={} --access_key={} " \
                                "--secret_key={} --password-reset-required " \
                                "--no-password-reset-required"
UPDATE_USR_PROFILE_RESET = "s3iamcli UpdateUserLoginProfile -n {} " \
                           "--password={} --access_key={} " \
                           "--secret_key={} --password-reset-required"
UPDATE_ACC_PROFILE = "s3iamcli UpdateUserLoginProfile -n {} --password={} " \
                     "--access_key={} --secret_key={} " \
                     "--no-password-reset-required"
UPDATE_USR_PROFILE_BOTH_RESET = "s3iamcli UpdateUserLoginProfile -n {0} " \
                                "--password={1} --access_key={2} " \
                                "--secret_key={3} --password-reset-required " \
                                "--no-password-reset-required"
GET_USRLOGING_PROFILE = "s3iamcli GetUserLoginProfile -n {} --access_key={} " \
                        "--secret_key={}"
CREATE_USR_LOGIN_PROFILE_NO_RESET = "s3iamcli CreateUserLoginProfile -n {} " \
                                    "--password={} --access_key={} " \
                                    "--secret_key={} " \
                                    "--password-reset-required " \
                                    "--no-password-reset-required"
CREATE_USR_LOGIN_PROFILE = "s3iamcli CreateUserLoginProfile -n {} " \
                           "--password={} --access_key={} --secret_key={}"
RESET_ACCESS_ACC = "s3iamcli resetaccountaccesskey -n {} --ldapuser={} " \
                   "--ldappasswd={}"
DEL_ACNT_USING_TEMP_CREDS = "s3iamcli deleteaccount -n {} --access_key={} " \
                            "--secret_key={} --session_token={}"
DEL_ACNT_USING_TEMP_CREDS_FORCE = "s3iamcli deleteaccount -n {} " \
                                  "--access_key={} --secret_key={} " \
                                  "--session_token={} --force"
S3_UPLOAD_FILE_CMD = "aws s3 cp {0} s3://{1}/{2}"
S3_UPLOAD_FOLDER_CMD = "aws s3 cp {0} s3://{1}/ --recursive --profile {2}"
S3_DOWNLOAD_BUCKET_CMD = "aws s3 cp --recursive s3://{} {} --profile {}"

# CORTXCLI Commands
CMD_LOGIN_CORTXCLI = "cortxcli"
CMD_LOGOUT_CORTXCLI = "exit"
CMD_CREATE_CSM_USER = "users create"
CMD_DELETE_CSM_USER = "users delete"
CMD_UPDATE_ROLE = "users update"
CMD_RESET_PWD = "users reset_password"
CMD_LIST_CSM_USERS = "users show"
CMD_HELP_OPTION = "-h"
CMD_CREATE_S3ACC = "s3accounts create"
CMD_SHOW_S3ACC = "s3accounts show"
CMD_DELETE_S3ACC = "s3accounts delete {}"
CMD_RESET_S3ACC_PWD = "s3accounts reset_password {}"
CMD_CREATE_BUCKET = "s3buckets create {}"
CMD_SHOW_BUCKETS = "s3buckets show"
CMD_DELETE_BUCKET = "s3buckets delete {}"
CREATE_IAM_USER = "s3iamusers create"
LIST_IAM_USER = "s3iamusers show"
DELETE_IAM_USER = "s3iamusers delete"
CMD_GENERATE_SUPPORT_BUNDLE = "support_bundle generate"
CMD_GENERATE_SUPPORT_BUNDLE_OS = "support_bundle generate {0} --os"
CMD_SUPPORT_BUNDLE_STATUS = "support_bundle status"

# Linux System Commands
CMD_MKDIR = "mkdir -p {}"
CMD_MOUNT = "mount -t nfs {} {}"
CMD_UMOUNT = "umount {}"
CMD_TAR = "tar -zxvf {} -C {}"
CMD_REMOVE_DIR = "rm -rf {}"

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
CMD_AWSCLI_COMPLETE_MULTIPART = "aws s3api complete-multipart-upload --multipart-upload file://{0} " \
                                "--bucket {1} --key {2} --upload-id {3}"
CMD_AWSCLI_DOWNLOAD_OBJECT = "aws s3 cp s3://{0}/{1} {2}"
