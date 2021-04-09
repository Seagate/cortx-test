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
from pathlib import Path

BASE =Path(__file__).parent.parent
LOG_FILE = os.path.join(BASE,'cortx-test.log')
USER_JSON = os.path.join(BASE,'_usersdata')
CONFIG_DIR = os.path.join(BASE,'config')
LOG_DIR_NAME = os.path.join(BASE,'log')
LATEST_LOG_FOLDER = os.path.join(BASE,'latest')

COMMON_CONFIG = os.path.join(CONFIG_DIR, 'common_config.yaml')
S3_CONFIG = os.path.join(CONFIG_DIR, 's3', 's3_config.yaml')
S3_OBJ_TEST_CONFIG = os.path.join(CONFIG_DIR, 's3', 's3_object_test.yaml')
RAS_CONFIG_PATH = os.path.join(CONFIG_DIR, "ras_config.yaml")
SSPL_TEST_CONFIG_PATH = os.path.join(CONFIG_DIR, "ras_test.yaml")
PROV_TEST_CONFIG_PATH = os.path.join(CONFIG_DIR, "prov_test.yaml")
COMMON_DESTRUCTIVE_CONFIG_PATH = os.path.join(CONFIG_DIR, "common_destructive.yaml")
CSM_CONFIG_PATH = os.path.join(CONFIG_DIR, 'csm', 'csm_config.yaml')
CSM_DIR = os.path.join(CONFIG_DIR, 'csm')
CSM_CONFIG = os.path.join(CSM_DIR, 'csm_config.yaml')
SETUPS_FPATH = os.path.join(LOG_DIR_NAME, "setups.json")

JIRA_TEST_LIST = os.path.join(BASE,'test_lists.csv')
JIRA_TEST_META_JSON = os.path.join(BASE,'test_meta_data.json')
JIRA_TEST_COLLECTION = os.path.join(BASE,'test_collection.csv')
JIRA_SELECTED_TESTS = os.path.join(BASE,'selected_test_lists.csv')
JIRA_DIST_TEST_LIST = os.path.join(BASE,'dist_test_lists.csv')
# Kafka Config Params
# Schema Registry (http(s)://host[:port]
SCHEMA_REGISTRY = "http://cftic2.pun.seagate.com:8081"
# cftic2.pun.seagate.com:9092 Bootstrap broker(s) (host[:port])
BOOTSTRAP_SERVERS = "cftic2.pun.seagate.com:9092"
# 'cortx-test-exec-topic'
TEST_EXEC_TOPIC = 'TutorialTopic3'
# Read by all semantics
TEST_ABORT_TOPIC = 'cortx-test-abort-topic'



NFS_SERVER_DIR = "cftic2.pun.seagate.com:/cftshare"
NFS_BASE_DIR = "automation"
MOUNT_DIR = os.path.join("/root", "nfs_share")
DB_HOSTNAME = """cftic1.pun.seagate.com:27017,
cftic2.pun.seagate.com:27017,
apollojenkins.pun.seagate.com:27017/
?authSource=cft_test_results&replicaSet=rs0"""
DB_NAME = "cft_test_results"
SYS_INFO_COLLECTION = "r2_systems"
LOCAL_LOG_PATH = "/root/pytest_logs"

# Jenkins url for deployment
JENKINS_URL = "http://eos-jenkins.mero.colo.seagate.com/job/QA/"

REPORT_SRV = "http://cftic2.pun.seagate.com:5000/"

