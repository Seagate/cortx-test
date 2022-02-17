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

"""Python Library using boto3 module."""

import logging
from botocore.config import Config

import boto3
from config.s3 import S3_CFG


LOGGER = logging.getLogger(__name__)


class S3RestApi(object):
    """Basic Class for Creating Boto3 REST API Objects."""

    def __init__(self,
                 access_key: str,
                 secret_key: str,
                 **kwargs):
        """
        method initializes members of S3Lib.

        Different instances need to be created as per different parameter values like access_key,
        secret_key etc.
        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param s3_cert_path: s3 certificate path.
        :param region: region.
        :param aws_session_token: aws_session_token.
        :param debug: debug mode.
        """
        region = kwargs.get("region", S3_CFG["region"])
        aws_session_token = kwargs.get("aws_session_token", None)
        debug = kwargs.get("debug", S3_CFG["debug"])
        use_ssl = kwargs.get("use_ssl", S3_CFG["use_ssl"])
        endpoint_url = kwargs.get("endpoint_url", S3_CFG["endpoint"])
        config = Config(retries={'max_attempts': S3_CFG["s3api_retry"]})
        if debug:
            # Uncomment to enable debug
            boto3.set_stream_logger(name="botocore")
        self.s3_resource = boto3.resource("s3",
                                          use_ssl=use_ssl,
                                          verify=False,
                                          aws_access_key_id=access_key,
                                          aws_secret_access_key=secret_key,
                                          endpoint_url=endpoint_url,
                                          region_name=region,
                                          aws_session_token=aws_session_token,
                                          config=config)
        self.s3_client = boto3.client("s3",
                                      use_ssl=use_ssl,
                                      verify=False,
                                      aws_access_key_id=access_key,
                                      aws_secret_access_key=secret_key,
                                      endpoint_url=endpoint_url,
                                      region_name=region,
                                      aws_session_token=aws_session_token,
                                      config=config)

    def __del__(self):
        """Destroy all core objects."""
        try:
            del self.s3_client
            del self.s3_resource
        except NameError as error:
            LOGGER.warning(error)
