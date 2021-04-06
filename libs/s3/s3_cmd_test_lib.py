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

from commons import errorcodes as err
from commons.exceptions import CTException
from commons.utils.system_utils import create_file
from libs.s3 import S3_CFG, ACCESS_KEY, SECRET_KEY
from libs.s3.s3_core_lib import S3LibCmd

LOGGER = logging.getLogger(__name__)


class S3CmdTestLib(S3LibCmd):
    """Class initialising s3 connection and including methods for s3 using CLI."""

    def __init__(self,
                 access_key: str = ACCESS_KEY,
                 secret_key: str = SECRET_KEY,
                 endpoint_url: str = S3_CFG["s3_url"],
                 s3_cert_path: str = S3_CFG["s3_cert_path"],
                 **kwargs) -> None:
        """
        Method to initializes members of S3CmdTestLib and its parent class.

        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param s3_cert_path: s3 certificate path.
        :param region: region.
        :param aws_session_token: aws_session_token.
        :param debug: debug mode.
        """
        kwargs["region"] = kwargs.get("region", S3_CFG["region"])
        kwargs["aws_session_token"] = kwargs.get("aws_session_token", None)
        kwargs["debug"] = kwargs.get("debug", S3_CFG["debug"])
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            **kwargs)

    def object_upload_cli(
            self,
            bucket_name: str = None,
            object_name: str = None,
            file_path: str = None,
            obj_size: int = None) -> tuple:
        """
        Uploading Object to the Bucket using aws cli.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :param obj_size: Size of the object.
        :return: (Boolean, response)
        """
        if not os.path.exists(file_path):
            LOGGER.debug(
                "%s do not exists creating as per the size given.",
                file_path)
            create_file(file_path, obj_size)
        try:
            LOGGER.info("uploading object using cli")
            status, response = self.upload_object_cli(
                bucket_name, object_name, file_path)
            upload_res = response.split("b'")[1].split("\\r")
            LOGGER.debug(upload_res)
            LOGGER.info("output = %s", upload_res)
            os.remove(file_path)
            if "upload:" in str(upload_res[-1]):
                return status, upload_res

            return False, response
        except BaseException as error:
            LOGGER.error("Error in %s: %s",
                         S3CmdTestLib.object_upload_cli.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

    def upload_folder_cli(
            self,
            bucket_name: str = None,
            folder_path: str = None,
            file_count: int = None) -> tuple:
        """
        Uploading folder to the Bucket using aws cli.

        :param bucket_name: Name of the bucket.
        :param folder_path: Path of the folder.
        :param file_count: Number of files.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Uploading folder objects to bucket using cli.")
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
            os.mkdir(folder_path)
            for count in range(file_count):
                file_path = os.path.join(
                    folder_path, "test_file{}".format(
                        str(count)))
                create_file(file_path, 10)
            status, response = super().upload_folder_cli(
                bucket_name, folder_path, S3_CFG["aws_cred_section"])
            shutil.rmtree(folder_path)
            LOGGER.debug(response)
            upload_cnt = response.count(b"upload:") if isinstance(
                response, bytes) else str(response).count("upload:")
            LOGGER.debug(upload_cnt)
            if upload_cnt == file_count:
                return status, response

            return False, response
        except BaseException as error:
            LOGGER.error("Error in %s: %s",
                         S3CmdTestLib.upload_folder_cli.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

    def download_bucket_cli(
            self,
            bucket_name: str = None,
            folder_path: str = None,
            profile_name: str = S3_CFG["aws_cred_section"]) -> tuple:
        """
        Downloading s3 objects to a local directory recursively using awscli.

        :param profile_name: AWS profile name.
        :param bucket_name: Name of the bucket.
        :param folder_path: Folder path.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Downloading folder from bucket using cli.")
            status, response = super().download_bucket_cli(
                bucket_name, folder_path, profile_name)
            LOGGER.info(response)

            return status, response
        except BaseException as error:
            LOGGER.error("Error in %s: %s",
                         S3CmdTestLib.download_bucket_cli.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

    @staticmethod
    def command_formatter(
            s3cmd_cnf: dict = None,
            operation: str = None,
            cmd_arguments: list = None) -> str:
        """
        Creating command from dictionary cmd_options.

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
        LOGGER.debug(cmd)

        return cmd
