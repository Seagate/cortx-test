#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
# -*- coding: utf-8 -*-
# !/usr/bin/python
"""Constants
"""
import os

LOG_FILE = 'cortx-test.log'

SCRIPT_HOME = os.getcwd()  # Fetches you CWD of the pytest or runner process.
CONFIG_DIR = 'config'
LOG_DIR_NAME = 'log'
LATEST_LOG_FOLDER = 'latest'
LOG_DIR = os.path.join(SCRIPT_HOME, LOG_DIR_NAME)
TEST_DATA_FOLDER = 'TestData'

COMMON_CONFIG = os.path.join(CONFIG_DIR, 'common_config.yaml')
S3_CONFIG = os.path.join(CONFIG_DIR, 's3', 's3_config.yaml')
S3_USER_ACC_MGMT_CONFIG_PATH = os.path.join(CONFIG_DIR, 's3', 's3_user_acc_management_test_config.yaml')
S3_OBJ_TEST_CONFIG = os.path.join(CONFIG_DIR, 's3', 's3_object_test.yaml')
S3_BKT_TEST_CONFIG = os.path.join(CONFIG_DIR, "s3", "s3_bucket_test.yaml")
S3CMD_TEST_CONFIG = os.path.join(CONFIG_DIR, "blackbox", "test_blackbox.yaml")
S3_LDAP_TEST_CONFIG = os.path.join(CONFIG_DIR, "s3", "test_openldap.yaml")
RAS_CONFIG_PATH = "config/ras_config.yaml"
SSPL_TEST_CONFIG_PATH = "config/ras_test.yaml"
PROV_TEST_CONFIG_PATH = "config/prov/prov_test.yaml"
COMMON_DESTRUCTIVE_CONFIG_PATH = "config/common_destructive.yaml"
DI_CONFIG_PATH = os.path.join(CONFIG_DIR, 'di_config.yaml')
DATA_PATH_CONFIG_PATH = os.path.join(CONFIG_DIR, 's3/test_data_path_validate.yaml')

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
TEST_EXEC_TOPIC = 'TutorialTopic3'
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
JENKINS_URL = "http://eos-jenkins.mero.colo.seagate.com/job/QA/"

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

DT_PATTERN_PREFIX = '%Y%m%d-%H%M%S'
