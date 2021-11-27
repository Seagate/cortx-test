#!/bin/bash
  dir_path=/mnt/nfs_share
  log_path=$1/$2/
  LOG_PATH=$dir_path/$log_path
  cmd="mkdir -p $dir_path"
  cmd2="mount -l|grep nfs4"
  cmd3="mkdir -p $LOG_PATH"
  mount_cmd="mount cftic2.pun.seagate.com:/cftshare_temp $dir_path"
  mv_cmd="mv $3/log/latest/TEST-N* $LOG_PATH"

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
      echo "INFO: Copied the logs: $LOG_PATH"
  else
      echo "INFO: Directory not exists"
      echo "INFO: Creating dir"
      eval "$cmd3"
      eval "$mv_cmd"
	  echo "INFO: Copied the logs: $LOG_PATH"
  fi
