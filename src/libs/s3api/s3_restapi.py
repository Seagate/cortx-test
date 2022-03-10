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

"""Python Library using boto3 module."""

import logging

from aiobotocore.config import AioConfig
from aiobotocore.session import get_session

from config import S3_CFG

LOGGER = logging.getLogger(__name__)


class S3RestApi(object):
    """Basic Class for Creating Boto3 REST API Objects."""

    def __init__(self, access_key: str, secret_key: str, **kwargs):
        """
        Method initializes members of S3Lib.
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
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = kwargs.get("region", S3_CFG["region"])
        self.aws_session_token = kwargs.get("aws_session_token", None)
        self.use_ssl = kwargs.get("use_ssl", S3_CFG["use_ssl"])
        self.endpoint_url = kwargs.get("endpoint_url", S3_CFG["endpoint"])
        self.config = AioConfig(retries={'max_attempts': S3_CFG["s3api_retry"]})
        self.debug = kwargs.get("debug", S3_CFG["debug"])
        # if self.debug:
        # Uncomment to enable debug
        # self.session.set_debug_logger(name="botocore")

    def get_client(self):
        """Create s3 client session for asyncio operations."""
        session = get_session()
        return session.create_client(service_name="s3",
                                     use_ssl=self.use_ssl,
                                     verify=False,
                                     aws_access_key_id=self.access_key,
                                     aws_secret_access_key=self.secret_key,
                                     endpoint_url=self.endpoint_url,
                                     region_name=self.region,
                                     aws_session_token=self.aws_session_token,
                                     config=self.config)
