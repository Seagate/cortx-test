#!/bin/bash/
  dir_path=/mnt/nfs_share
  log_path=$1/$2/
  LOG_PATH=$dir_path/$log_path
  cmd="mkdir -p $dir_path"
  cmd2="mount -l|grep nfs4"
  mount_cmd="mount cftic2.pun.seagate.com:/cftshare_temp $dir_path"

  if [ -d $dir_path ]
  then
      echo "Directory exists."
  else
      echo "INFO: Directory does not exists.Will create the dir"
      eval $cmd
  fi

  if [[ $(mount -l|grep "$dir_path") ]]; then
      echo "Mounted"
  else
      echo "Not mounted"
          echo "Mount the dir"
          $mount_cmd
          echo "Verify the nfs share is mounted"
          eval $cmd2

  fi
  if [ -d $LOG_PATH ]
  then
      echo "Directory exists"
      echo "Copying logs to nfs share"
      mv $3/log/latest/TEST-N* $LOG_PATH
      echo "Copied the logs: $LOG_PATH"
  else
      echo "Directory not exists"
      echo "Creating dir"
      mkdir -p $LOG_PATH
      mv $3/log/latest/TEST-N* $LOG_PATH
	  echo "Copied the logs: $LOG_PATH"
  fi
