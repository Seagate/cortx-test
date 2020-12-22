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

# parameter needed for test framework and tests
# These can be formed at runtime based on basic/common configuration files

NUSERS = 10

UPLOADED_FILES = "uploadInfo.csv"

DATAGEN_HOME = '/var/log/datagen/'

DATASET_FILES = "/var/log/datagen/createdfile.txt"

deleteOpFileName = "deleteInfo.csv"

comDeleteOpFileName = "combinedDeleteInfo.csv"

uploadDoneFile = UPLOADED_FILES

uploadFinishedFileName = "upload_done.txt"

FailedFiles = "FailedFiles.csv"

FailedFilesServerError = "FailedFilesServerError.csv"

destructiveTestResult = "/root/result_summary.csv"

deletePercentage = 10

DOWNLOAD_HOME = '/var/log/'
