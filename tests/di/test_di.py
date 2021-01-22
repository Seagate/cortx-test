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
# !/usr/bin/env python3
import os
import logging
import pytest
import pytest_ordering
import pytest_metadata
import config as cfg
#from libs.di.di_test_framework import Uploader
#from libs.di.di_test_framework import DIChecker
#from libs.di.di_mgmt_ops import ManagementOPs
#from libs.di.di_lib import create_iter_content_json
from libs.di.di_lib import init_loghandler

logger = logging.getLogger(__name__)
#init_loghandler(logger)


def setup_module(module):
    """ setup any state specific to the execution of the given module."""


def teardown_module(module):
    """ teardown any state that was previously setup with a setup_module
    method.
    """

class TestDataIntegrity:
    """ log sys event when doing node operation
       log test hooks and actions/events
    """
    HOME = os.getcwd()

    @classmethod
    def setup_class(cls):
        """ setup any state specific to the execution of the given class (which
        usually contains tests).
        """

    @classmethod
    def teardown_class(cls):
        """ teardown any state that was previously setup with a call to
        setup_class.
        """

    def setUp(self) -> None:
        #users = ManagementOPs.create_account_users()
        #create_iter_content_json(DataIntegrityTest.HOME, users)
        pass

    def setup_method(self, method) -> None:
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """

    def teardown_method(self, method) -> None:
        """ teardown any state that was previously setup with a setup_method
        call.
        """
    @pytest.mark.skip
    @pytest.mark.run(order=2)
    @pytest.mark.test(test_id=12345, tag='di')
    @pytest.mark.dataprovider('', conn=300)
    def test_di_large_number_s3_connection(self):
        """
        300 * 3, 300 * 6, 300 * 9, 300 * 12
        :return:
        """
        cmn_cfg = cfg.CMN_CFG
        users = cfg.constants.USER_JSON

    @pytest.mark.skip
    @pytest.mark.test(test_id=12345, tag='di')
    @pytest.mark.run(order=2)
    def test_very_large_number_s3_connection(self):
        assert True

    """
    @pytest.mark.test(test_id=1234, tag='di')
    def test_di_large_number_s3_connection(self):
        uploader = Uploader()
        uploader.start()
        dichecker = DIChecker()
        dichecker.verify_data_integrity()
    
    
    def test_di_large_number_s3_connection_with_deletes(self):
        uploader = Uploader()
        uploader.start()
        destructive_step()
        dichecker = DIChecker()
        dichecker.verify_data_integrity()

    def test_di_for_mixed_ops_with_sas_hba_fault(self):
        uploader = Uploader()
        uploader.start()
        destructive_step()
        dichecker = DIChecker()
        dichecker.verify_data_integrity()
    """

    def tearDown(self) -> None:
        pass


if __name__ == '__main__':
    pass
