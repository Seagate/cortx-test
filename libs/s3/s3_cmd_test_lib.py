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
#
#
"""Python library contains methods for s3 cmd."""

import os
import shutil
import logging
from botocore.exceptions import ClientError
from commons import errorcodes as err
from commons.exceptions import CTException
from commons.utils.system_utils import create_file
from config.s3 import S3_CFG
from libs.s3.s3_awscli import S3LibCmd

LOGGER = logging.getLogger(__name__)


class S3CmdTestLib(S3LibCmd):
    """Class initialising s3 connection and including methods for s3 using CLI."""

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
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3CmdTestLib.object_upload_cli.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

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
                    folder_path, f"test_file{str(count)}")
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
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3CmdTestLib.upload_folder_cli.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

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
        except (ClientError, Exception) as error:
            LOGGER.error("Error in %s: %s",
                         S3CmdTestLib.download_bucket_cli.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

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
        tool = s3cmd_cnf["s3cmd_cfg"]["s3cmd_tool"]
        cmd_elements.append(tool)
        cmd_elements.append(operation)
        if cmd_arguments:
            for argument in cmd_arguments:
                cmd_elements.append(argument)
        cmd = " ".join(cmd_elements)
        LOGGER.debug(cmd)

        return cmd
