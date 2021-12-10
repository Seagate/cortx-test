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
"""Python library contains methods for s3 awscli."""

import os
import logging
import typing
from collections import OrderedDict
from config.s3 import S3_CFG
from commons import commands
from commons.utils.system_utils import run_local_cmd

LOGGER = logging.getLogger(__name__)


class S3CmdCommandBuilder:
    """A temporary class to build s3cmd commands.
     It should be replaced by more glorified command builder.
     """
    def __init__(self, **kwargs):
        self.parent_cmd = ['s3cmd']
        self.cmd_action = 'get'  # default get
        self.current_options = list()
        self.user_opts = kwargs

    def build_options(self):
        """ Options significant are as shown below
        --ssl
        no - ssl
        check - md5
        no - check - md5
        host
        host - bucket
        no - check - certificate
        check - certificate
        --signature - v2
        :returns options string
        """
        if self.user_opts.get('access_key'):
            self.current_options = self.current_options + ["--access_key=" + str(self.user_opts.get('access_key'))]

        if self.user_opts.get('secret_key'):
            self.current_options = self.current_options + ["--secret_key=" + str(self.user_opts.get('secret_key'))]

        if self.user_opts.get('ssl'):
            self.current_options = self.current_options + ["--ssl"]
        else:
            self.current_options = self.current_options + ["--no-ssl"]

        if self.user_opts.get('check-certificate'):
            self.current_options = self.current_options + ["--check-certificate"]
        else:
            self.current_options = self.current_options + ["--no-check-certificate"]

        if self.user_opts.get('host'):
            self.current_options = self.current_options + ["--host=" + str(self.user_opts.get('host_port'))]

        if self.user_opts.get('host-bucket'):
            self.current_options = self.current_options + ["--host-bucket=" + str(self.user_opts.get('host-bucket'))]
        return self.current_options

    def build_put_command(self, path: str, bucket: str) -> str:
        """Builds the s3cmd command line."""
        # Build option
        self.parent_cmd += self.build_options()
        # Build action
        self.parent_cmd += ['put']
        # Build Command
        bucket = bucket if bucket.startswith('s3://') else 's3://' + bucket
        part = [path] + [bucket]
        self.parent_cmd += [part]
        return self.parent_cmd

    def build_get_command(self, local_file_path: str, object_uri: str) -> str:
        """Builds the s3cmd command line.
        :param local_file_path : full local file path to be created
        :param object_uri : s3 URI like s3://bucket/object  bucket/object with proto prefix.
        """
        self.parent_cmd += self.build_options()
        self.parent_cmd += ['get']
        # Build Command
        object_uri = object_uri if object_uri.startswith('s3://') else 's3://' + object_uri
        self.parent_cmd += [object_uri, local_file_path]
        return self.parent_cmd

    def __str__(self):
        if len(self.current_options) == 0:
            return self.parent_cmd
        options_str = ' '.join(map(str, self.current_options))
        return ' '.join((self.parent_cmd, options_str))


class S3CmdFacade:
    """Wrapper Class implementing methods to expose needed s3cmd functionality."""

    def upload_object_s3cmd(self, bucket_name: str = None,
                            file_path: str = None, **kwargs) -> tuple:
        """
        Uploading Object to the Bucket using s3cmd.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :return: response.
        """
        s3cmd = S3CmdCommandBuilder(kwargs)
        cmd = s3cmd.build_put_command(file_path, bucket_name)

        response = run_local_cmd(cmd, chk_stderr=True)
        LOGGER.debug("Response: %s", str(response))

        return response

    def download_object_s3cmd(
            self,
            bucket_name: str = None,
            file_path: str = None,
            **kwargs) -> tuple:
        """
        Downloading s3 object to a local dir.

        :param file_path:
        :param bucket_name: Name of the bucket.
        :param profile_name: AWS profile name.
        :return: download bucket cli response.
        """
        s3cmd = S3CmdCommandBuilder(kwargs)
        object_uri = kwargs.get('object_uri')
        if not os.path.exists(file_path):
            os.mkdir(file_path)
        cmd = s3cmd.build_get_command(local_file_path=file_path, object_uri=object_uri)
        response = run_local_cmd(cmd, chk_stderr=True)
        LOGGER.debug("Response: %s", str(response))
        return response
