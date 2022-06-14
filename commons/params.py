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
# -*- coding: utf-8 -*-
# !/usr/bin/python
"""Constants
"""
import os
import tempfile

LOG_FILE = 'cortx-test.log'

SCRIPT_HOME = os.getcwd()  # Fetches you CWD of the pytest or runner process.
CONFIG_DIR = 'config'
LOG_DIR_NAME = 'log'
LATEST_LOG_FOLDER = 'latest'
LOG_DIR = os.path.join(SCRIPT_HOME, LOG_DIR_NAME)
TEST_DATA_FOLDER = os.path.join(LOG_DIR, 'TestData')
VAR_LOG_SYS = '/var/log/'

COMMON_CONFIG = os.path.join(CONFIG_DIR, 'common_config.yaml')
S3_CONFIG = os.path.join(CONFIG_DIR, 's3', 's3_config.yaml')
S3_MPART_CFG_PATH = os.path.join(CONFIG_DIR, "s3", "test_multipart_upload.yaml")
S3_TEMP_CRED_CONFIG_PATH = os.path.join(CONFIG_DIR, "s3", "test_delete_account_temp_cred.yaml")
S3_BLACK_BOX_CONFIG_PATH = os.path.join(CONFIG_DIR, "blackbox", "test_blackbox.yaml")
S3_USER_ACC_MGMT_CONFIG_PATH = os.path.join(
    CONFIG_DIR, 's3', 's3_user_acc_management_test_config.yaml')
S3_OBJ_TEST_CONFIG = os.path.join(CONFIG_DIR, 's3', 's3_object_test.yaml')
S3_BKT_TEST_CONFIG = os.path.join(CONFIG_DIR, "s3", "s3_bucket_test.yaml")
S3CMD_TEST_CONFIG = os.path.join(CONFIG_DIR, "blackbox", "test_blackbox.yaml")
S3_LDAP_TEST_CONFIG = os.path.join(CONFIG_DIR, "s3", "test_openldap.yaml")
RAS_CONFIG_PATH = "config/ras_config.yaml"
SSPL_TEST_CONFIG_PATH = "config/ras_test.yaml"
PROV_TEST_CONFIG_PATH = "config/prov/prov_test.yaml"
DEPLOY_TEST_CONFIG_PATH = "config/prov/deploy_config.yaml"
COMMON_DESTRUCTIVE_CONFIG_PATH = "config/common_destructive.yaml"
DI_CONFIG_PATH = os.path.join(CONFIG_DIR, 'di_config.yaml')
DATA_PATH_CONFIG_PATH = os.path.join(CONFIG_DIR, 's3/test_data_path_validate.yaml')
HA_TEST_CONFIG_PATH = "config/ha_test.yaml"
DEL_CFG_PATH = os.path.join(CONFIG_DIR, "s3", "test_delayed_delete.yaml")
IAM_POLICY_CFG_PATH = os.path.join(CONFIG_DIR, "s3", "s3_iam_policy_test.yaml")
PROV_CONFIG_PATH = "config/prov/test_prov_config.yaml"
DTM_TEST_CFG_PATH = os.path.join(CONFIG_DIR, "test_dtm_config.yaml")
DURABILITY_CFG_PATH = os.path.join(CONFIG_DIR, "durability_test.yaml")

TEST_DATA_PATH = os.path.join(os.getcwd(), TEST_DATA_FOLDER)
JIRA_TEST_LIST = 'test_lists.csv'
CSM_CONFIG_PATH = os.path.join(CONFIG_DIR, 'csm', 'csm_config.yaml')
JIRA_TEST_META_JSON = 'test_meta_data.json'
JIRA_TEST_COLLECTION = 'test_collection.csv'
JIRA_SELECTED_TESTS = 'selected_test_lists.csv'
JIRA_DIST_TEST_LIST = 'dist_test_lists.csv'

# Kafka Config Params
# Schema Registry (http(s)://host[:port]
SCHEMA_REGISTRY = "http://cftic2.pun.seagate.com:8081"
# cftic2.pun.seagate.com:9092 Bootstrap broker(s) (host[:port])
BOOTSTRAP_SERVERS = "cftic2.pun.seagate.com:9092"
# 'cortx-test-exec-topic'
TEST_EXEC_TOPIC = 'cortx-test-execution-topic1'
# Read by all semantics
TEST_ABORT_TOPIC = 'cortx-test-abort-topic'


CSM_DIR = os.path.join(CONFIG_DIR, 'csm')
CSM_CONFIG = os.path.join(CSM_DIR, 'csm_config.yaml')
SETUPS_FPATH = os.path.join(LOG_DIR_NAME, "setups.json")

NFS_SERVER_DIR = "cftic2.pun.seagate.com:/cftshare_temp"
NFS_BASE_DIR = "automation"
MOUNT_DIR = os.path.join("/root", "nfs_share")
DB_HOSTNAME = """cftic1.pun.seagate.com:27017,
cftic2.pun.seagate.com:27017,
apollojenkins.pun.seagate.com:27017/
?authSource=cft_test_results&replicaSet=rs0"""
DB_NAME = "cft_test_results"
SYS_INFO_COLLECTION = "r2_systems"
LOCAL_LOG_PATH = "/root/pytest_logs"
VM_COLLECTION = "r2_vm_pool"

# Jenkins url for deployment
JENKINS_URL = "https://eos-jenkins.colo.seagate.com/job/QA/"

REPORT_SRV = "http://cftic2.pun.seagate.com:5000/"
SETUP_DEFAULTS = "tools/setup_update/setup_entry.json"

# DI Params
DI_LOG_FILE = 'diframework.log'
NWORKERS = 32
NGREENLETS = 32
NUSERS = 10
DATAGEN_HOME = '/var/log/datagen/'
META_DATA_HOME = os.path.join(LOG_DIR, 'meta_data')
S3_ENDPOINT = "https://s3.seagate.com"
DATASET_FILES = "/var/log/datagen/createdfile.txt"
USER_JSON = '_usersdata'
USER_META_JSON = '_user_metadata'
UPLOADED_FILES = "uploadInfo.csv"
DELETE_OP_FILE_NAME = "deleteInfo.csv"
COM_DELETE_OP_FILENAME = "combinedDeleteInfo.csv"
UPLOAD_DONE_FILE = UPLOADED_FILES
UPLOAD_FINISHED_FILENAME = "upload_done.txt"
FAILED_FILES = "FailedFiles.csv"
FAILED_FILES_SERVER_ERROR = "FailedFilesServerError.csv"
DESTRUCTIVE_TEST_RESULT = "/root/result_summary.csv"
DELETE_PERCENTAGE = 10
DOWNLOAD_HOME = '/var/log/'

S3_INSTANCES_PER_NODE = 1
LOCAL_S3_CONFIG = os.path.join(tempfile.gettempdir(), 's3config.yaml')
DT_PATTERN_PREFIX = '%Y%m%d-%H%M%S'

PROV_SKIP_TEST_FILES_HEALTH_CHECK_PREFIX = ['test_prov', 'test_failure_domain',
                                            'test_multiple_config_deploy', 'test_cont_deployment',
                                            "test_di_deployment", 'test_namespace_deployment']

# Ceph s3-tests Runner Params
S3TESTS_DIR = "s3-tests"
S3TESTS_CONF_ENV = "S3TEST_CONF"
S3TESTS_CONF_FILE = "s3tests.conf"
REPORTS_DIR = "reports"
VIRTUALENV_DIR = "virtualenv"

# IAM paths
IAM_USER = "/admin/user"
