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

    @staticmethod
    def dummy_api(post_id):
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

    @staticmethod
    def dummy_method(post_id):
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
