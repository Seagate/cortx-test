# -*- coding: utf-8 -*-
# !/usr/bin/python
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

import os

LOG_FILE = 'diframework.log'
NWORKERS = 32
NGREENLETS = 32
NUSERS = 10


DATAGEN_HOME = '/var/log/datagen/'
DATASET_FILES = "/var/log/datagen/createdfile.txt"
USER_JSON = '_usersdata'
UPLOADED_FILES = os.path.join(DATAGEN_HOME, "uploadInfo.csv")
deleteOpFileName = os.path.join(DATAGEN_HOME, "deleteInfo.csv")
comDeleteOpFileName = os.path.join(DATAGEN_HOME, "combinedDeleteInfo.csv")
uploadDoneFile = UPLOADED_FILES
uploadFinishedFileName = "upload_done.txt"
FailedFiles = "FailedFiles.csv"
FailedFilesServerError = "FailedFilesServerError.csv"
destructiveTestResult = "/var/log/datagen/result_summary.csv"

deletePercentage = 10
DOWNLOAD_HOME = '/var/log/download'

