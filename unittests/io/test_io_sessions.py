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

""" io sessions Unit Tests."""
import unittest
import requests

from libs.io.workers import make_sessions
from unittests.io import logger


class TestIOSessions(unittest.TestCase):
    """
    S3 API IO Sessions lib unittest suite.
    """

    def setUp(self):
        """
        This function will be invoked before test suit execution
        It will perform prerequisite test steps if any
        Defined var for log, config, creating common account or bucket
        """
        logger.info("STARTED: Setup operations")
        self.list_of_post_ids = list(range(1, 5))
        logger.info("ENDED: Setup operations")

    def tearDown(self):
        """
        This function will be invoked after test suit.
        It will clean up resources which are getting created during test case execution.
        This function will reset accounts, delete buckets, accounts and files.
        """
        logger.info("STARTED: Teardown operations")
        logger.info("ENDED: Teardown operations")

    def dummy_api(self, post_id):
        """
            Just a sample function which would make dummy API calls
        """
        logger.info("Executing dummy api with id {}".format(post_id))
        url = f"https://jsonplaceholder.typicode.com/comments?postId={post_id}"
        response = requests.get(url)
        if response.status_code == 200:
            logger.info(response.json())
            return response.json()
        return {}

    def dummy_method(self, post_id):
        """
            Just a sample function which would make dummy API calls
        """
        logger.info("Executing dummy api with id {}".format(post_id))
        logger.info(post_id)
        return {"post_id": post_id}

    def test_make_sessions(self):
        """
        Simple function to test dummy api with multiple sessions/processes
        :return: None
        """
        logger.info("Testing make sessions")
        data1, data2, data3, data4 = self.list_of_post_ids
        result = make_sessions(self.dummy_api)(data1, data2, data3, data4, number_of_workers=4)
        logger.info(result)

    def test_make_sessions_with_iterable(self):
        """
        Simple function to test dummy api with multiple sessions/processes with ten thousand workers
        :return: None
        """
        logger.info("Testing make sessions with either list or tuple data set")
        result = make_sessions(self.dummy_method)(list(range(1, 10000)), number_of_workers=10)
        logger.info(result)

    def test_make_sessions_with_iterable_default_workers(self):
        """
        Simple function to test dummy api with multiple sessions/processes with default workers
        :return: None
        """
        logger.info("Testing make sessions with either list or tuple data set")
        result = make_sessions(self.dummy_method)(list(range(1, 1000)))
        logger.info(result)

    def test_make_sessions_with_iterable_lessthen_default_workers(self):
        """
        Simple function to test dummy api with multiple sessions/processes with default workers
        :return: None
        """
        logger.info("Testing make sessions with either list or tuple data set")
        result = make_sessions(self.dummy_method)(list(range(1, 15)))
        logger.info(result)


if __name__ == '__main__':
    unittest.main()
