#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""blackbox test library which contains CRUD and related helper operations."""
import os
import logging
import time

from commons import commands
from commons.utils import config_utils
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.utils.system_utils import run_local_cmd
from commons.utils.system_utils import execute_cmd
from commons.utils.assert_utils import assert_true
from commons.utils.assert_utils import assert_in
from commons.constants import S3_ENGINE_RGW
from config import CMN_CFG
from config.s3 import S3_CFG, S3_BLKBOX_CFG
from config.s3 import S3_BLKBOX_CFG as S3FS_CNF
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_test_lib import S3TestLib



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
            if not os.path.exists(temp_dir):
                os.mkdir(temp_dir)
            mount_cmd = commands.CMD_MOUNT.format(nfs_path, temp_dir)
            umount_cmd = commands.CMD_UMOUNT.format(temp_dir)
            run_local_cmd(mount_cmd)
            run_local_cmd(f"yes | cp -rf {temp_dir}/*.jar {source}")
            run_local_cmd(umount_cmd)
            os.rmdir(temp_dir)

        run_local_cmd(f"yes | cp -rf {source}*.jar {destination}")
        res_ls = run_local_cmd(f"ls {destination}")[1]
        # Run commands to set cert files in client Location.
        if S3_CFG['validate_certs']:
            run_local_cmd(commands.CMD_KEYTOOL1)
            run_local_cmd(commands.CMD_KEYTOOL2.format(ca_crt_path))

        return bool(".jar" in res_ls)

    @staticmethod
    def update_jclient_jcloud_properties():
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
                    iam_endpoint = (S3_CFG["iam_url"].split('//')[1]).split(':')[0]
                    prop_dict['iam_endpoint'] = iam_endpoint
                if prop_dict['s3_endpoint'] != S3_CFG["s3_url"]:
                    s3_endpoint = S3_CFG["s3_url"].split('//')[1]
                    prop_dict['s3_endpoint'] = s3_endpoint
                prop_dict['use_https'] = 'true' if S3_CFG['use_ssl'] else 'false'
                # Skip certificate validation with https/ssl is unsupported option in jcloud/jclient

                if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
                    prop_dict['s3_endpoint'] = s3_endpoint.split(':')[0]
                    if S3_CFG['use_ssl']:
                        prop_dict['s3_https_port'] = s3_endpoint.split(':')[1]
                    else:
                        prop_dict['s3_http_port'] = s3_endpoint.split(':')[1]
                resp = config_utils.write_properties_file(prop_path, prop_dict)

        return resp

    # pylint: disable=too-many-arguments
    @staticmethod
    def create_cmd_format(bucket, operation, jtool=None, chunk=None,
                          access_key=ACCESS_KEY, secret_key=SECRET_KEY):
        """
        Function forms a command to perform specified operation.

        using given bucket name and returns a single line command.
        :param str bucket: Name of the s3 bucket
        :param str operation: type of operation to be performed on s3
        :param str jtool: Name of the java jar tool
        :param bool chunk: Its accepts chunk upload, if True
        :param access_key: Access Key for S3 operation
        :param secret_key: Secret Key for S3 operation
        :return: str command: cli command to be executed
        """
        if jtool == S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"]:
            java_cmd = S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_cmd"]
            aws_keys_str = "--access-key {} --secret-key {}".format(
                access_key, secret_key)
            bucket_url = "s3://{}".format(bucket)
            cmd = "{} {} {} {} {}".format(java_cmd, operation, bucket_url,
                                          aws_keys_str, "-p")
        else:
            java_cmd = S3_BLKBOX_CFG["jcloud_cfg"]["jclient_cmd"]
            aws_keys_str = "--access_key {} --secret_key {}".format(
                access_key, secret_key)
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

    def __init__(self, access: str = None, secret: str = None,) -> None:
        """
        method initializes members for s3fs client.
        """
        self.access = access
        self.secret = secret
        self.s3_test_obj = S3TestLib(access_key=self.access, secret_key=self.secret,
                                     endpoint_url=S3_CFG["s3_url"])

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
        if not S3_CFG["validate_certs"]:
            cmd_arguments.append("-o no_check_certificate")
        if S3FS_CNF["s3fs_cfg"]["nosscache"]:
            cmd_arguments.append("-o nosscache")
        if cmd_arguments:
            for argument in cmd_arguments:
                cmd_elements.append(argument)
        cmd = " ".join(cmd_elements)
        LOGGER.info("s3fs command: %s", cmd)

        return cmd

    @staticmethod
    def check_bucket_mounted(mount_path=None) -> tuple:
        """
        Check the bucket mounted on client.
        :param: mount_path: Mount path of the bucket.
        :return: True if bucket mounted successfully else False.
        """
        if not system_utils.path_exists(mount_path):
            return False, f"Mount path '{mount_path}' does not exit"
        command = S3FS_CNF["s3fs_cfg"]["cmd_check_mount"].format(mount_path)
        resp = execute_cmd(command)
        if not resp[0]:
            return False, f"Failed to execute command: {command}"
        if f"s3fs on {mount_path} type fuse.s3fs" not in resp[1]:
            return False, resp[1]

        return True, resp[1]

    def create_and_mount_bucket(self, bucket_name=None):
        """
        Method helps to create bucket and mount bucket using s3fs client.

        :return tuple: bucket_name & dir_name
        """
        if not bucket_name:
            bucket_name = S3FS_CNF["s3fs_cfg"]["bucket_name"].format(time.perf_counter_ns())
        LOGGER.info("Creating bucket %s", bucket_name)
        resp = self.s3_test_obj.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        LOGGER.info("Bucket created %s", bucket_name)
        LOGGER.info("Create a directory and list mount directory")
        dir_name = S3FS_CNF["s3fs_cfg"]["dir_name"].format(int(time.perf_counter_ns()))
        command = " ".join([S3FS_CNF["s3fs_cfg"]["make_dir_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        LOGGER.info("Created a directory and list mount directory")
        LOGGER.info("Mount bucket")
        operation = " ".join([bucket_name, dir_name])
        cmd_arguments = [
            S3FS_CNF["s3fs_cfg"]["passwd_file"],
            S3FS_CNF["s3fs_cfg"]["url"].format(S3_CFG['s3_url']),
            S3FS_CNF["s3fs_cfg"]["path_style"],
            S3FS_CNF["s3fs_cfg"]["dbglevel"]]
        command = self.create_cmd(operation, cmd_arguments)
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        resp = self.check_bucket_mounted(dir_name)
        assert_true(resp[0], resp[1])
        LOGGER.info("Mount bucket successfully")
        LOGGER.info("Check the mounted directory present")
        resp = execute_cmd(S3FS_CNF["s3fs_cfg"]["cmd_check_mount"].format(dir_name))
        assert_in(
            dir_name,
            str(resp[1]),
            resp[1])
        LOGGER.info("Checked the mounted directory present")
        return bucket_name, dir_name


# pylint: disable=too-few-public-methods
class S3CMD:
    """Class for s3cmd Tools operations."""

    def __init__(self, access: str = None, secret: str = None) -> None:
        """method initializes members for s3cms client."""
        self.access = access
        self.secret = secret
        self.s3cf_path = S3_CFG["s3cfg_path"]
        self.use_ssl = S3_CFG['use_ssl']
        self.validate_certs = S3_CFG['validate_certs']
        self.endpoint = S3_CFG["s3_url"].split('//')[1]

    def configure_s3cfg(self, access: str = None, secret: str = None) -> bool:
        """
        Function to configure access and secret keys in s3cfg file.

        :param access: aws access key.
        :param secret: aws secret key.
        :return: True if s3cmd configured else False.
        """
        access = access if access else self.access
        secret = secret if secret else self.secret
        status, resp = run_local_cmd("s3cmd --version")
        LOGGER.info(resp)
        if not (status and system_utils.path_exists(self.s3cf_path)):
            LOGGER.critical(
                "S3cmd is not present, please install & configuration it through Makefile.")
            return False

        LOGGER.info("Updating config: %s", self.s3cf_path)
        s3cmd_params = {
            "access_key": access, "secret_key": secret, "host_base": self.endpoint,
            "host_bucket": self.endpoint, "check_ssl_certificate": str(self.validate_certs),
            "use_https": str(self.use_ssl)
        }
        for key, value in s3cmd_params.items():
            status = config_utils.update_config_ini(self.s3cf_path, "default", key, value)
            if not status:
                LOGGER.error("Failed to update key: %s with %s", key, value)
                return status

            LOGGER.info("Updated key: %s with %s", key, value)

        return status
