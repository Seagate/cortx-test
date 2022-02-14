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
import logging
import unittest
import requests

from libs.io.workers import make_sessions


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
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.list_of_post_ids = list(range(1, 5))
        self.log.info("ENDED: Setup operations")

    def tearDown(self):
        """
        This function will be invoked after test suit.
        It will clean up resources which are getting created during test case execution.
        This function will reset accounts, delete buckets, accounts and files.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("ENDED: Teardown operations")

    def dummy_api(self, post_id):
        """
            Just a sample function which would make dummy API calls
        """
        print("Executing dummy api with id {}".format(post_id))
        url = f"https://jsonplaceholder.typicode.com/comments?postId={post_id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return {}

    def test_make_sessions(self):
        """
        Simple function to test dummy api with multiple sessions/processes
        :return: None
        """
        print("Testing make sessions")
        data1, data2, data3, data4 = self.list_of_post_ids
        result = make_sessions(self.dummy_api)(data1, data2, data3, data4, number_of_workers=4)
        print(result)

    def test_make_sessions_with_iterable(self):
        print("Testing make sessions with either list or tuple data set")
        result = make_sessions(self.dummy_api)(list(range(1, 10000)), number_of_workers=10000)
        print(result)


if __name__ == '__main__':
    unittest.main()
