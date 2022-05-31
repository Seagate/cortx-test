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
"""Python library contains facade for s3cmd."""

import os
import logging
import tempfile
from typing import AnyStr
from commons.utils import assert_utils
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
            self.current_options = self.current_options + [
                "--access_key=" + str(self.user_opts.get('access_key'))]

        if self.user_opts.get('secret_key'):
            self.current_options = self.current_options + [
                "--secret_key=" + str(self.user_opts.get('secret_key'))]

        if self.user_opts.get('ssl'):
            self.current_options = self.current_options + ["--ssl"]
        else:
            self.current_options = self.current_options + ["--no_ssl"]

        if self.user_opts.get('check_certificate'):
            self.current_options = self.current_options + ["--check-certificate"]
        else:
            self.current_options = self.current_options + ["--no-check-certificate"]

        if self.user_opts.get('host_port'):
            self.current_options = self.current_options + [
                "--host=" + str(self.user_opts.get('host_port'))]

        if self.user_opts.get('host_bucket'):
            self.current_options = self.current_options + [
                "--host-bucket=" + str(self.user_opts.get('host_bucket'))]

        if self.user_opts.get('disable_multipart'):
            self.current_options = self.current_options + ["--disable-multipart"]

        if self.user_opts.get('multipart_chunk_size_mb'):
            self.current_options = self.current_options + [
                "--multipart-chunk-size-mb=" + str(self.user_opts.get('multipart_chunk_size_mb'))]
        return self.current_options

    def build_put_command(self, path: str, bucket: str) -> AnyStr:
        """Builds the s3cmd command line.
        :param path : s3 prefix plus object name e.g. tmp/tmpobject.db'
        :param bucket: can be of form s3://bucket or just bucket name
        """
        assert_utils.assert_true(path.startswith('/'))
        # Build option
        self.parent_cmd += self.build_options()
        # Build action
        self.parent_cmd += ['put']
        # Build Command
        bucket = bucket if bucket.startswith('s3://') else 's3://' + bucket
        part = '/'.join([bucket, os.path.split(path)[-1]])
        self.parent_cmd += [path]
        self.parent_cmd += [part]
        return self.parent_cmd

    def build_get_command(self, local_file_path: str, object_uri: str) -> AnyStr:
        """Builds the s3cmd command line.
        :param local_file_path : full local file path to be created
        :param object_uri : s3 URI like s3://bucket/object or bucket/object with proto prefix.
        """
        assert_utils.assert_true(object_uri.startswith('s3://'),
                                 'Object URI should start with s3://')
        self.parent_cmd += self.build_options()
        self.parent_cmd += ['get']
        # Build Command
        self.parent_cmd += [object_uri, local_file_path]
        return self.parent_cmd

    def __str__(self):
        if len(self.current_options) == 0:
            return self.parent_cmd
        options_str = ' '.join(map(str, self.current_options))
        return ' '.join((self.parent_cmd, options_str))


class S3CmdFacade:
    """Wrapper Class implementing methods to expose needed s3cmd functionality."""

    @classmethod
    def upload_object_s3cmd(cls, bucket_name: str = None,
                            file_path: str = None, **kwargs) -> tuple:
        """
        Uploading Object to the Bucket using s3cmd.

        :param bucket_name: Name of the bucket.
        :param object_name: Name of the object.
        :param file_path: Path of the file.
        :return: response.
        """
        s3cmd = S3CmdCommandBuilder(**kwargs)
        cmd = s3cmd.build_put_command(file_path, bucket_name)
        cmd = ' '.join(cmd)
        response = run_local_cmd(cmd, chk_stderr=True)
        LOGGER.debug("Response: %s", str(response))
        return response

    @classmethod
    def download_object_s3cmd(cls, file_path: str = None, **kwargs) -> tuple:
        """
        Downloading s3 object to a local dir.

        :param file_path:
        :param bucket_name: Name of the bucket.
        :param profile_name: AWS profile name.
        :return: download bucket cli response.
        """
        s3cmd = S3CmdCommandBuilder(**kwargs)
        object_uri = kwargs.get('object_uri')
        if not os.path.exists(file_path):
            if not os.path.exists(os.path.split(file_path)[0]):
                os.mkdir(os.path.split(file_path)[0])
        cmd = s3cmd.build_get_command(local_file_path=file_path, object_uri=object_uri)
        cmd = ' '.join(cmd)
        response = run_local_cmd(cmd, chk_stderr=True)
        LOGGER.debug("Response: %s", str(response))
        return response


if __name__ == '__main__':
    odict = dict(access_key='access_key', secret_key='secret_key',  # nosec
                 ssl=True, no_check_certificate=False,
                 host_port='host_port', host_bucket='host-bucket',
                 multipart_chunk_size_mb='15MB')
    upload_file = os.path.join(tempfile.gettempdir(), 'tmpobject.db')
    S3CmdFacade.upload_object_s3cmd(bucket_name='dummy', file_path=upload_file, **odict)
    dodict = dict(access_key='access_key', secret_key='secret_key',  # nosec
                  ssl=True, no_check_certificate=False,
                  host_port='host_port', object_uri='s3://host-bucket/tmpobject.db')
    tempf = os.path.join(tempfile.gettempdir(), 'tmpobject2.db')
    S3CmdFacade.download_object_s3cmd(file_path=tempf, **dodict)
