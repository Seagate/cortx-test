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

"""Python library contains methods for s3 awscli."""
import ast
import os
import logging

from config.s3 import S3_CFG
from commons import commands
from commons.utils.system_utils import run_local_cmd

LOGGER = logging.getLogger(__name__)


class S3LibCmd:
    """Class containing methods to implement aws cmd functionality."""

    def __init__(self):
        """AWS cli constructor."""
        self.cmd_endpoint_options = f" --endpoint-url {S3_CFG['s3_url']}" \
            f"{'' if S3_CFG['validate_certs'] else ' --no-verify-ssl'}"

    def upload_object_cli(
            self,
            bucket_name: str = None,
            object_name: str = None,
            file_path: str = None) -> tuple:
        """
        Uploading Object to the Bucket using aws cli.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :return: response.
        """
        cmd = commands.S3_UPLOAD_FILE_CMD.format(file_path, bucket_name, object_name)
        cmd += self.cmd_endpoint_options
        response = run_local_cmd(cmd, chk_stderr=True)
        LOGGER.debug("Response: %s", str(response))

        return response

    def upload_folder_cli(
            self,
            bucket_name: str = None,
            folder_path: str = None,
            profile_name: str = None) -> tuple:
        """
        Uploading folder to the Bucket using aws cli.

        :param bucket_name: Name of the bucket.
        :param folder_path: Path of the folder.
        :param profile_name: AWS profile name.
        :return: response.
        """
        cmd = commands.S3_UPLOAD_FOLDER_CMD.format(folder_path, bucket_name, profile_name)
        cmd += self.cmd_endpoint_options
        response = run_local_cmd(cmd, chk_stderr=True)
        LOGGER.debug("Response: %s", str(response))

        return response

    def download_bucket_cli(
            self,
            bucket_name: str = None,
            folder_path: str = None,
            profile_name: str = None) -> tuple:
        """
        Downloading s3 objects to a local directory recursively using awscli.

        :param bucket_name: Name of the bucket.
        :param folder_path: Folder path.
        :param profile_name: AWS profile name.
        :return: download bucket cli response.
        """
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
        cmd = commands.S3_DOWNLOAD_BUCKET_CMD.format(bucket_name, folder_path, profile_name)
        cmd += self.cmd_endpoint_options
        response = run_local_cmd(cmd, chk_stderr=True)
        LOGGER.debug("Response: %s", str(response))

        return response


class AWScliS3api:
    """Class including methods related to aws cli s3api operations."""

    def __init__(self):
        """AWS cli s3api constructor."""
        self.cmd_endpoint_options = f" --endpoint-url {S3_CFG['s3_url']}" \
            f"{'' if S3_CFG['validate_certs'] else ' --no-verify-ssl'}"

    def create_bucket(self, bucket_name: str) -> tuple:
        """
        Create s3 bucket using s3api.

        :param bucket_name: Name of the bucket.
        :return: True/False, response.
        """
        LOGGER.info("Create bucket: %s", bucket_name)
        cmd_create_bkt = commands.CMD_AWSCLI_CREATE_BUCKET.format(bucket_name)
        cmd_create_bkt += self.cmd_endpoint_options
        _, output = run_local_cmd(cmd_create_bkt, chk_stderr=True)
        if bucket_name in output:
            return True, output

        return False, output

    def delete_bucket(self, bucket_name, force=False) -> tuple:
        """
        Method to delete a bucket using awscli.

        :param bucket_name: Name of the bucket
        :param force: True for forcefully deleting bucket containing objects
        :return: True/False and output of command execution
        """
        LOGGER.info("Delete bucket: %s", bucket_name)
        LOGGER.info("List objects: %s", self.list_objects_v2(bucket_name))
        cmd_del_bkt = commands.CMD_AWSCLI_DELETE_BUCKET.format(bucket_name)
        cmd_del_bkt = " ".join([cmd_del_bkt, "--force"]) if force else cmd_del_bkt
        cmd_del_bkt += self.cmd_endpoint_options
        _, output = run_local_cmd(cmd_del_bkt, chk_stderr=True)
        if bucket_name in output:
            return True, output

        return False, output

    def list_bucket(self) -> list:
        """
        Method to list buckets using awscli.

        :return: list of buckets.
        """
        LOGGER.info("List buckets")
        bktlist = list()
        cmd_list_bkt = commands.CMD_AWSCLI_LIST_BUCKETS + self.cmd_endpoint_options
        status, output = run_local_cmd(cmd_list_bkt, chk_stderr=True)
        if status:
            bktlist = [bkt.split(-1) for bkt in output.split("\n") if bkt]

        return bktlist

    def download_object(self, bucket_name, object_name, file_path):
        """
        Download s3 object to file path.

        :param bucket_name: Name of the bucket.
        :param object_name: name of the object.
        :param file_path: download file path.
        :return: true/false, response.
        """
        LOGGER.info("Download s3 object.")
        dwn_object = commands.CMD_AWSCLI_DOWNLOAD_OBJECT.format(
            bucket_name, object_name, file_path) + self.cmd_endpoint_options
        _, output = run_local_cmd(dwn_object, chk_stderr=True)

        return os.path.exists(file_path), output

    def upload_directory(self, bucket_name, directory_path) -> tuple:
        """
        Upload directory to s3 bucket.

        :param bucket_name: Name of the bucket.
        :param directory_path: Absolute directory path.
        :return: true/false, response.
        """
        LOGGER.info("Upload  directory to S3 bucket.")
        upload_dir = commands.CMD_AWSCLI_UPLOAD_DIR_TO_BUCKET.format(
            directory_path, bucket_name) + self.cmd_endpoint_options
        status, output = run_local_cmd(upload_dir, chk_stderr=True)
        upload_list = [out.split("\\r")[-1] for out in output.split("\\n") if out][:-1]
        LOGGER.info("Upload list: %s", upload_list)

        return status, upload_list

    def list_objects_v2(self, bucket_name, **kwargs):
        """
        Method to list objects using aws s3api.

        :param bucket_name: Name of the bucket.
        :param kwargs: All supported options by list-object-v2.
        :return: true/false, response.
        """
        LOGGER.info("List objects using aws s3api.")
        if kwargs:
            options = ""
            for key, value in kwargs.items():
                key = key.replace("_", "-")
                if value:
                    options += " --{} {}".format(key, value)
                else:
                    options += " --{}".format(key)
            cmd_list_v2_objects = commands.CMD_AWSCLI_LIST_OBJECTS_V2_OPTIONS_BUCKETS.format(
                bucket_name, options) + self.cmd_endpoint_options
            status, output = run_local_cmd(cmd_list_v2_objects, chk_stderr=True)
        else:
            cmd_list_v2_objects = commands.CMD_AWSCLI_LIST_OBJECTS_V2_BUCKETS.format(
                bucket_name) + self.cmd_endpoint_options
            status, output = run_local_cmd(cmd_list_v2_objects, chk_stderr=True)
        output = ast.literal_eval(ast.literal_eval(output.strip('b'))) if output else output
        LOGGER.info("list-objects-v2: %s", output)
        if status:
            return status, output

        return False, output
