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
"""Python library contains methods for s3 cmd."""

import os
import shutil
import logging

from libs.s3.s3_core_lib import S3LibCmd
from commons import errorcodes as err
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.helpers.s3_helper import S3Helper
from commons.utils.system_utils import create_file

try:
    s3hobj = S3Helper()
except ImportError as err:
    s3hobj = S3Helper.get_instance()

s3_conf = read_yaml("config/s3/s3_config.yaml")[1]
CM_CFG = read_yaml("config/common_config.yaml")[1]

logger = logging.getLogger(__name__)


class S3CmdTestLib(S3LibCmd):
    """
    This Class initialising s3 connection and including methods for s3 using CLI.
    """

    def __init__(self,
                 access_key: str = s3hobj.get_local_keys()[0],
                 secret_key: str = s3hobj.get_local_keys()[1],
                 endpoint_url: str = s3_conf["s3_url"],
                 s3_cert_path: str = s3_conf["s3_cert_path"],
                 region: str = s3_conf["region"],
                 aws_session_token: str = None,
                 debug: bool = s3_conf["debug"]
                 ) -> None:
        """
        This method initializes members of S3CmdTestLib and its parent class.
        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param s3_cert_path: s3 certificate path.
        :param region: region.
        :param aws_session_token: aws_session_token.
        :param debug: debug mode.
        """
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            region,
            aws_session_token,
            debug)

    def object_upload_cli(
            self,
            bucket_name: str,
            object_name: str,
            file_path: str,
            obj_size: int) -> tuple:
        """
        Uploading Object to the Bucket using aws cli.
        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :param obj_size: Size of the object.
        :return: (Boolean, response)
        """
        if not os.path.exists(file_path):
            logger.debug(
                "%s do not exists creating as per the size given.",
                file_path)
            create_file(file_path, obj_size)
        try:
            logger.info("uploading object using cli")
            response = self.upload_object_cli(
                bucket_name, object_name, file_path)
            upload_res = response.split("b'")[1].split("\\r")
            logger.debug(upload_res)
            logger.info("output = %s", upload_res)
            os.remove(file_path)
            if b"upload:" in upload_res[-1] or "upload:" in upload_res[-1]:
                return True, upload_res

            return False, response
        except BaseException as error:
            logger.error("Error in %s: %s",
                         S3CmdTestLib.object_upload_cli.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

    def upload_folder_cli(
            self,
            bucket_name: str,
            folder_path: str,
            file_count: int) -> tuple:
        """
        Uploading folder to the Bucket using aws cli.
        :param bucket_name: Name of the bucket.
        :param folder_path: Path of the folder.
        :param file_count: Number of files.
        :return: (Boolean, response)
        """
        try:
            logger.info("Uploading folder objects to bucket using cli.")
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
            os.mkdir(folder_path)
            for count in range(file_count):
                file_path = os.path.join(
                    folder_path, "test_file{}".format(
                        str(count)))
                create_file(file_path, 10)
            response = super().upload_folder_cli(
                bucket_name, folder_path, CM_CFG["aws_cred_section"])
            shutil.rmtree(folder_path)
            logger.debug(response)
            upload_cnt = response.count(b"upload:") if isinstance(
                response, bytes) else str(response).count("upload:")
            logger.debug(upload_cnt)
            if upload_cnt == file_count:
                return True, response

            return False, response
        except BaseException as error:
            logger.error("Error in %s: %s",
                         S3CmdTestLib.upload_folder_cli.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

    def download_bucket_cli(self, bucket_name: str, folder_path: str) -> tuple:
        """
        Downloading s3 objects to a local directory recursively using awscli.
        :param bucket_name: Name of the bucket.
        :param folder_path: Folder path.
        :return: (Boolean, response)
        """
        try:
            logger.info("Downloading folder from bucket using cli.")
            response = super().download_bucket_cli(
                bucket_name, folder_path, CM_CFG["aws_cred_section"])
            logger.info(response)
            if os.path.exists(folder_path):
                return True, response

            return False, response
        except BaseException as error:
            logger.error("Error in %s: %s",
                         S3CmdTestLib.download_bucket_cli.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

    def command_formatter(
            self,
            s3cmd_cnf: str,
            operation: str,
            cmd_arguments: str = None) -> str:
        """
        Creating command fronm dictonary cmd_options.
        :param dict s3cmd_cnf: yml config file pointer.
        :param str operation: type of operation to be performed on s3.
        :param list cmd_arguments: parameters for the command.
        :return: actual command that is going to execute for utility.
        """
        cmd_elements = []
        tool = s3cmd_cnf["common_cfg"]["s3cmd_tool"]
        cmd_elements.append(tool)
        cmd_elements.append(operation)
        if cmd_arguments:
            for argument in cmd_arguments:
                cmd_elements.append(argument)
        cmd = " ".join(cmd_elements)
        logger.debug(cmd)

        return cmd
