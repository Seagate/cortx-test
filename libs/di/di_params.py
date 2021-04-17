# -*- coding: utf-8 -*-
# !/usr/bin/python
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

LOG_FILE = 'diframework.log'
NWORKERS = 32
NGREENLETS = 32
NUSERS = 10

S3_ENDPOINT = "https://s3.seagate.com"
DATAGEN_HOME = '/var/log/datagen/'
DATASET_FILES = "/var/log/datagen/createdfile.txt"
USER_JSON = '_usersdata'
UPLOADED_FILES = "uploadInfo.csv"
deleteOpFileName = "deleteInfo.csv"
comDeleteOpFileName = "combinedDeleteInfo.csv"
uploadDoneFile = UPLOADED_FILES
uploadFinishedFileName = "upload_done.txt"
FailedFiles = "FailedFiles.csv"
FailedFilesServerError = "FailedFilesServerError.csv"
destructiveTestResult = "/root/result_summary.csv"

deletePercentage = 10
DOWNLOAD_HOME = '/var/log/'

#avocado commands
SAS_HBA_FAULT_CMD = 'avocado run tests/ras/destructive/test_sas_hba_faults.py:SASFault.test_sas_hba_fault -p loop_iteration=1'
PUBLIC_DATA_NETWORK_FAULT_CMD = 'avocado run tests/ras/destructive/test_network_faults.py:NetworkFault.test_public_data_network_fault -p loop_iteration=1'
POWER_FAILURE_FAULT_CMD = 'avocado run tests/ras/destructive/test_power_failure.py -p loop_iteration=1'
CONTROLLER_A_FAULT_CMD = 'avocado run tests/ras/destructive/test_controller_fault.py:ControllerFault.test_controller_a_faults -p loop_iteration=1 -p di_test=True'
CONTROLLER_B_FAULT_CMD = 'avocado run tests/ras/destructive/test_controller_fault.py:ControllerFault.test_controller_b_faults -p loop_iteration=1 -p di_test=True'
