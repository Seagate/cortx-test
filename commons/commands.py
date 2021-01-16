# All the constants are alphabetically arranged.
CPU_USAGE_CMD = "python3 -c 'import psutil; print(psutil.cpu_times_percent(interval=1)[2])'"
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
NETSAT_CMD = "netstat -tnlp | grep {}"
PCS_CLUSTER_START = "pcs cluster start {}"
PCS_CLUSTER_STOP = "pcs cluster stop {}"
PCS_RESOURCES_CLEANUP = "pcs resource cleanup {}"
PCS_RESOURCE_SHOW_CMD = "pcs resource show"
PCS_RESOURCE_RESTART_CMD = "pcs resource restart {}"
PCS_RESOURCE_ENABLE_CMD = "pcs resource enable {}"
PCS_RESOURCE_DISABLE_CMD = "pcs resource disable {}"
PGREP_CMD = "sudo pgrep {}"
PKIL_CMD = "pkill {}"
RPM_GREP_CMD = "rpm -qa | grep {}"
RPM_INSTALL_CMD = "yum install -y {0}"
SYSTEM_CTL_CMD = "systemctl {} {}"
SYSTEM_CTL_STATUS_CMD = "systemctl status {}"
SYSTEM_CTL_RESTART_CMD = "systemctl restart {}"
SYSTEM_CTL_START_CMD = "systemctl start {}"
SYSTEM_CTL_STOP_CMD = "systemctl stop {}"

# S3IAMCLI Commands
CREATE_ACC_USR_S3IAMCLI = "s3iamcli CreateUser -n {} --access_key={} --secret_key={}"
CMD_LIST_ACC = "s3iamcli Listaccounts --ldapuser={} --ldappasswd={}"
CMD_LST_USR = "s3iamcli ListUsers --access_key={} --secret_key={}"
CMD_CREATE_ACC = "s3iamcli CreateAccount -n {} -e {} --ldapuser={} --ldappasswd={}"
CMD_DEL_ACC = "s3iamcli deleteaccount -n {} --access_key={} --secret_key={}"
CMD_DEL_ACC_FORCE = "s3iamcli deleteaccount -n {} --access_key={} --secret_key={} --force"
UPDATE_ACC_LOGIN_PROFILE = "s3iamcli UpdateAccountLoginProfile -n {} --access_key={} --secret_key={}"
UPDATE_USR_LOGIN_PROFILE = "s3iamcli UpdateUserLoginProfile -n {} --access_key={} --secret_key={}"
GET_ACC_PROFILE = "s3iamcli GetAccountLoginProfile -n {} --access_key={} --secret_key={}"
GET_TEMP_ACC_DURATION = "s3iamcli GetTempAuthCredentials -a {} --password {} -d {}"
GET_TEMP_ACC = "s3iamcli GetTempAuthCredentials -a {} --password {}"
GET_TEMP_USR_DURATION = "s3iamcli GetTempAuthCredentials -a {} -n {} --password {} -d {}"
GET_TEMP_USR = "s3iamcli GetTempAuthCredentials -a {} -n {} --password {}"
CMD_CHANGE_PWD = "s3iamcli ChangePassword --old_password {} --new_password {} --access_key={} " \
    "--secret_key={}"

CREATE_USR_PROFILE_PWD_RESET = "s3iamcli CreateUserLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --password-reset-required"
CREATE_USR_PROFILE_NO_PWD_RESET = "s3iamcli CreateUserLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --no-password-reset-required"
CREATE_ACC_PROFILE_PWD_RESET = "s3iamcli CreateAccountLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --password-reset-required"
CREATE_ACC_PROFILE_WITHOUT_BOTH_RESET = "s3iamcli CreateAccountLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={}"
CREATE_ACC_RROFILE_NO_PWD_RESET = "s3iamcli CreateAccountLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --no-password-reset-required"
CREATE_ACC_RROFILE_WITH_BOTH_RESET = "s3iamcli CreateAccountLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --password-reset-required --no-password-reset-required"
UPDATE_ACC_PROFILE_RESET = "s3iamcli UpdateAccountLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --password-reset-required"
UPDATE_ACC_PROFILE_NO_RESET = "s3iamcli UpdateAccountLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --no-password-reset-required"
UPDATE_ACC_PROFILE_BOTH_RESET = "s3iamcli UpdateAccountLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --password-reset-required --no-password-reset-required"
UPDATE_USR_PROFILE_RESET = "s3iamcli UpdateUserLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --password-reset-required"
UPDATE_ACC_PROFILE = "s3iamcli UpdateUserLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --no-password-reset-required"
UPDATE_USR_PROFILE_BOTH_RESET = "s3iamcli UpdateUserLoginProfile -n {0} --password={1} --access_key={2} --secret_key={3} " \
    "--password-reset-required --no-password-reset-required"
GET_USRLOGING_PROFILE = "s3iamcli GetUserLoginProfile -n {} --access_key={} --secret_key={}"
CREATE_USR_LOGIN_PROFILE_NO_RESET = "s3iamcli CreateUserLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={} --password-reset-required --no-password-reset-required"
CREATE_USR_LOGIN_PROFILE = "s3iamcli CreateUserLoginProfile -n {} --password={} --access_key={} " \
    "--secret_key={}"
RESET_ACCESS_ACC = "s3iamcli resetaccountaccesskey -n {} --ldapuser={} --ldappasswd={}"
DEL_ACNT_USING_TEMP_CREDS = "s3iamcli deleteaccount -n {} --access_key={} --secret_key={} --session_token={}"
DEL_ACNT_USING_TEMP_CREDS_FORCE = "s3iamcli deleteaccount -n {} --access_key={} --secret_key={} --session_token={}" \
                                  " --force"
S3_UPLOAD_FILE_CMD = "aws s3 cp {0} s3://{1}/{2}"
S3_UPLOAD_FOLDER_CMD = "aws s3 cp {0} s3://{1}/ --recursive --profile {2}"
S3_DOWNLOAD_BUCKET_CMD = "aws s3 cp --recursive s3://{} {} --profile {}"
