#!/bin/bash
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
  dir_path=/mnt/nfs_share
  log_path=deployment_logs/$1/$2/
  LOG_PATH=$dir_path/$log_path
  cmd="mkdir -p $dir_path"
  cmd2="mount -l|grep nfs4"
  cmd3="mkdir -p $LOG_PATH"
  mount_cmd="mount cftic2.pun.seagate.com:/cftshare_temp $dir_path"
  mv_cmd="mv $3/log/latest/TEST-N* $LOG_PATH"
  mv_cmd2="mv $3/support_bundle/*.tar $LOG_PATH"
  mv_cmd3="mv $3/crash_files/*.gz $LOG_PATH"
  mv_csv="cp $3/log/latest/*.csv $LOG_PATH"
  export_cmd="export LOG_PATH=$LOG_PATH"
  if [ -d $dir_path ]
  then
      echo "INFO: Directory exists."
  else
      echo "DEBUG: Directory does not exists.Will create the dir"
      eval "$cmd"
  fi
  # shellcheck disable=SC2143
  if [[ $(mount -l|grep "$dir_path") ]]; then
      echo "INFO: Mounted"
  else
      echo "DEBUG: Not mounted"
          echo "INFO: Mount the dir"
          eval "$mount_cmd"
          echo "INFO: Verify the nfs share is mounted"
          eval "$cmd2"
  fi
  if [ -d "$LOG_PATH" ]
  then
      echo "INFO: Directory exists"
      echo "INFO: Copying logs to nfs share"
      eval "$mv_cmd"
      eval "$mv_cmd2"
      eval "$mv_cmd3"
      echo "INFO: Copied the logs: $LOG_PATH"
      eval "$export_cmd"
  else
      echo "INFO: Directory not exists"
      echo "INFO: Creating dir"
      eval "$cmd3"
      eval "$mv_cmd"
      eval "$mv_cmd2"
      eval "$mv_cmd3"
      eval "$mv_csv"
     echo "INFO: Copied the logs: $LOG_PATH"
     eval "$export_cmd"
  fi
