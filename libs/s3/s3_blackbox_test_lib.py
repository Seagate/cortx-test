#!/usr/bin/python
# -*- coding: utf-8 -*-
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
#

"""blackbox test library which contains CRUD and related helper operations."""
import os
import logging
import time

from commons import commands
from commons.utils import config_utils, system_utils, assert_utils
from commons.utils.system_utils import run_local_cmd, execute_cmd
from config.s3 import S3_CFG, S3_BLKBOX_CFG
from config.s3 import S3_BLKBOX_CFG as S3FS_CNF
from commons.utils.assert_utils import assert_true, assert_in
from libs.s3 import ACCESS_KEY, SECRET_KEY

LOGGER = logging.getLogger(__name__)


class JCloudClient:
    """Class related to jcloud jclient operations."""

    @staticmethod
    def configure_jclient_cloud(
            source: str,
            destination: str,
            nfs_path: str,
            ca_crt_path: str) -> bool:
        """
        Function to configure jclient and cloud jar files.

        :param ca_crt_path: s3 ca.crt path.
        :param nfs_path: nfs server path where jcloudclient.jar, jclient.jar present.
        :param source: path to the source dir where .jar are present.
        :param destination: destination path where .jar need to be copied
        """
        if not os.path.exists(source):
            os.mkdir(source)

        dir_list = os.listdir(source)
        if "jcloudclient.jar" not in dir_list or "jclient.jar" not in dir_list:
            temp_dir = "/mnt/jjarfiles"
            os.mkdir(temp_dir)
            mount_cmd = f"mount.nfs -v {nfs_path} {temp_dir}"
            umount_cmd = f"umount -v {temp_dir}"
            run_local_cmd(mount_cmd)
            run_local_cmd(f"yes | cp -rf {temp_dir}*.jar {source}")
            run_local_cmd(umount_cmd)
            os.remove(temp_dir)

        run_local_cmd(f"yes | cp -rf {source}*.jar {destination}")
        res_ls = run_local_cmd(f"ls {destination}")[1]
        # Run commands to set cert files in client Location.
        run_local_cmd(commands.CMD_KEYTOOL1)
        run_local_cmd(commands.CMD_KEYTOOL2.format(ca_crt_path))

        return bool(".jar" in res_ls)

    def update_jclient_jcloud_properties(self):
        """
        Update jclient, jcloud properties with correct s3, iam endpoint.
        :return: True
        """
        resp = False
        for prop_path in [S3_BLKBOX_CFG["jcloud_cfg"]["jclient_properties_path"],
                          S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_properties_path"]]:
            LOGGER.info("Updating: %s", prop_path)
            prop_dict = config_utils.read_properties_file(prop_path)
            if prop_dict:
                if prop_dict['iam_endpoint'] != S3_CFG["iam_url"]:
                    prop_dict['iam_endpoint'] = S3_CFG["iam_url"]
                if prop_dict['s3_endpoint'] != S3_CFG["s3_url"]:
                    prop_dict['s3_endpoint'] = S3_CFG["s3_url"]
                resp = config_utils.write_properties_file(prop_path, prop_dict)

        return resp

    def create_cmd_format(self, bucket, operation, jtool=None, chunk=None):
        """
        Function forms a command to perform specified operation.

        using given bucket name and returns a single line command.
        :param str bucket: Name of the s3 bucket
        :param str operation: type of operation to be performed on s3
        :param str jtool: Name of the java jar tool
        :param bool chunk: Its accepts chunk upload, if True
        :return: str command: cli command to be executed
        """
        if jtool == S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"]:
            java_cmd = S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_cmd"]
            aws_keys_str = "--access-key {} --secret-key {}".format(
                ACCESS_KEY, SECRET_KEY)
            bucket_url = "s3://{}".format(bucket)
            cmd = "{} {} {} {} {}".format(java_cmd, operation, bucket_url,
                                          aws_keys_str, "-p")
        else:
            java_cmd = S3_BLKBOX_CFG["jcloud_cfg"]["jclient_cmd"]
            aws_keys_str = "--access_key {} --secret_key {}".format(
                ACCESS_KEY, SECRET_KEY)
            bucket_url = "s3://{}".format(bucket)
            if chunk:
                cmd = "{} {} {} {} {} {}".format(java_cmd, operation, bucket_url,
                                                 aws_keys_str, "-p", "-C")
            else:
                cmd = "{} {} {} {} {}".format(java_cmd, operation, bucket_url,
                                              aws_keys_str, "-p")

        LOGGER.info("jcloud command: %s", cmd)

        return cmd


class MinIOClient:
    """Class for minIO related operations."""

    def __init__(self,
                 **kwargs) -> None:
        """
        method initializes members for minio client.

        """
        val_cert = kwargs.get("validate_certs", S3_CFG["validate_certs"])
        self.validate_cert = f"{'' if val_cert else ' --insecure'}"
        self.minio_cnf = S3_BLKBOX_CFG["minio_cfg"]

    @staticmethod
    def configure_minio(access: str = None, secret: str = None, path: str = None) -> bool:
        """
        Function to configure minio creds in config.json file.

        :param access: aws access key.
        :param secret: aws secret key.
        :param path: path to minio cfg file.
        :return: True/False.
        """
        path = path if path else S3_CFG["minio_path"]
        res = False
        if os.path.exists(path):
            data = config_utils.read_content_json(path, mode='rb')
            data["hosts"]["s3"]["accessKey"] = access
            data["hosts"]["s3"]["secretKey"] = secret
            res = config_utils.create_content_json(
                path=path, data=data, ensure_ascii=False)
        else:
            LOGGER.warning(
                "Minio is not installed please install and then run the configuration.")

        return os.path.isfile(path) and res

    @staticmethod
    def configre_minio_cloud(minio_repo=None,
                             endpoint_url=None,
                             s3_cert_path=None,
                             minio_cert_path_list=None,
                             **kwargs):
        """
        Installing minio client in current machine.

        :param minio_repo: minio repo path.
        :param endpoint_url: s3 endpoint url.
        :param s3_cert_path: s3 certificate path.
        :param minio_cert_path_list: minio path list to be updated.
        :param kwargs: access, secret keys.
        :return: True if setup completed or false.
        """
        try:
            LOGGER.info("Installing minio client in current machine.")
            ACCESS = kwargs.get("access", None)
            SECRET = kwargs.get("secret", None)
            run_local_cmd("wget {}".format(minio_repo))
            run_local_cmd("chmod +x {}".format(os.path.basename(minio_repo)))
            run_local_cmd("./{} config host add s3 {} {} {} --api S3v4".format(os.path.basename(
                minio_repo), endpoint_url, ACCESS, SECRET))
            for crt_path in minio_cert_path_list:
                if not os.path.exists(crt_path):
                    run_local_cmd("yes | cp -r {} {}".format(s3_cert_path, crt_path))
            LOGGER.info("Installed minio client in current machine.")

            return True
        except Exception as error:
            LOGGER.error(str(error))
            return False

    def create_bucket(self, bucket_name):
        """
        Creating a new bucket.

        :param str bucket_name: Name of bucket to be created
        :return: None
        """
        LOGGER.info(
            "Step 1: Creating a bucket with name %s", bucket_name)
        cmd = self.minio_cnf["create_bkt_cmd"].format(bucket_name) + self.validate_cert
        resp = system_utils.run_local_cmd(cmd)
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_in("Bucket created successfully", resp[1], resp[1])
        LOGGER.info(
            "Step 1: Bucket is created with name %s", bucket_name)


class S3FS:
    """Class for s4fs Tools operations."""

    @staticmethod
    def configure_s3fs(
            access: str = None,
            secret: str = None,
            path: str = None) -> bool:
        """
        Function to configure access and secret keys for s3fs.

        :param access: aws access key.
        :param secret: aws secret key.
        :param path: s3fs config file.
        :return: True if s3fs configured else False.
        """
        path = path if path else S3_CFG["s3fs_path"]
        status, resp = run_local_cmd("s3fs --version")
        LOGGER.info(resp)
        if status:
            with open(path, "w+") as f_write:
                f_write.write(f"{access}:{secret}")
        else:
            LOGGER.warning("S3fs is not present, please install it and then run the configuration.")

        return status

    @staticmethod
    def create_cmd(operation, cmd_arguments=None):
        """
        Creating command from operation and cmd_options.

        :param str operation: type of operation to be performed on s3
        :param list cmd_arguments: parameters for the command
        :return str: actual command that is going to execute for utility
        """
        cmd_elements = []
        tool = S3FS_CNF["s3fs_cfg"]["s3fs_tool"]
        cmd_elements.append(tool)
        cmd_elements.append(operation)
        if S3_CFG["use_ssl"]:
            if S3FS_CNF["s3fs_cfg"]["no_check_certificate"]:
                cmd_arguments.append("-o no_check_certificate")
            if not S3FS_CNF["s3fs_cfg"]["ssl_verify_hostname"]:
                cmd_arguments.append("-o ssl_verify_hostname=0")
            else:
                cmd_arguments.append("-o ssl_verify_hostname=2")
            if S3FS_CNF["s3fs_cfg"]["nosscache"]:
                cmd_arguments.append("-o nosscache")
        if cmd_arguments:
            for argument in cmd_arguments:
                cmd_elements.append(argument)
        cmd = " ".join(cmd_elements)
        return cmd

    def create_and_mount_bucket(self, bucket_name=None):
        """
        Method helps to create bucket and mount bucket using s3fs client.

        :return tuple: bucket_name & dir_name
        """
        if not bucket_name:
            bucket_name = self.s3fs_cfg["bucket_name"].format(time.perf_counter_ns())
        LOGGER.info("Creating bucket %s", bucket_name)
        resp = self.s3_test_obj.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        LOGGER.info("Bucket created %s", bucket_name)
        LOGGER.info("Create a directory and list mount directory")
        dir_name = self.s3fs_cfg["dir_name"].format(int(time.perf_counter_ns()))
        command = " ".join([self.s3fs_cfg["make_dir_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        LOGGER.info("Created a directory and list mount directory")
        LOGGER.info("Mount bucket")
        operation = " ".join([bucket_name, dir_name])
        cmd_arguments = [
            self.s3fs_cfg["passwd_file"],
            self.s3fs_cfg["url"],
            self.s3fs_cfg["path_style"],
            self.s3fs_cfg["dbglevel"]]
        command = self.create_cmd(
            operation, cmd_arguments)
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        LOGGER.info("Mount bucket successfully")
        LOGGER.info("Check the mounted directory present")
        resp = execute_cmd(self.s3fs_cfg["cmd_check_mount"].format(dir_name))
        assert_in(
            dir_name,
            str(resp[1]),
            resp[1])
        LOGGER.info("Checked the mounted directory present")
        return bucket_name, dir_name
