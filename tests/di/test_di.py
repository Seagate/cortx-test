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
from commons.utils import assert_utils
from commons.exceptions import TestException
from libs.di.di_test_framework import Uploader
from libs.di.di_test_framework import DIChecker
from libs.di.di_mgmt_ops import ManagementOPs
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import DATA_PATH_CFG

logger = logging.getLogger(__name__)


class TestDataIntegrity:
    """ log sys event when doing node operation
       log test hooks and actions/events
    """

    def setup_method(self, method) -> None:
        """ setup any state tied to the execution of the given method in a
        class.  setup_method is invoked for every test method of a class.
        """
        pass

    def teardown_method(self, method) -> None:
        """ teardown any state that was previously setup with a setup_method
        call.
        """
        # done = False # Flag hack to test if the tear down was executed successful
        # try:
        #     login = self.s3acc_obj.login_cortx_cli()
        #     assert_utils.assert_equals(True, login[0], login[1])
        #     accounts = self.s3acc_obj.show_s3account_cortx_cli(output_format="json")[1]
        #     accounts = self.s3acc_obj.format_str_to_dict(
        #         input_str=accounts)["s3_accounts"]
        #     accounts = [acc["account_name"]
        #                 for acc in accounts if ManagementOPs.user_prefix in acc["account_name"]]
        #     self.s3acc_obj.logout_cortx_cli()
        #     for acc in accounts:
        #         self.s3acc_obj.login_cortx_cli(
        #             username=acc, password=self.s3acc_password)
        #         self.s3acc_obj.delete_s3account_cortx_cli(account_name=acc)
        #         self.s3acc_obj.logout_cortx_cli()
        #     logger.info("ENDED : Teardown operations at test function level")
        #     done = True
        # except TestException as te:
        #     logger.error(str(te))
        #     logger.error('An error occurred while running teardown')
        # if done:
        #     logger.info('Teardown executed successfully')

    @pytest.mark.di
    @pytest.mark.tags("TEST-0")
    def test_di_sanity(self):
        import pdb
        pdb.set_trace()
        ops = ManagementOPs()
        users = ops.create_account_users(nusers=4)
        #uploader = Uploader()
        #uploader.start(users)
        #DIChecker.init_s3_conn(users)
        #DIChecker.verify_data_integrity(users)

    @pytest.mark.di
    @pytest.mark.tags("TEST-0")
    @CTFailOn(error_handler)
    def test_large_number_s3_connection(self):
        """
        300 * 3, 300 * 6, 300 * 9, 300 * 12
        :return:
        """
        logger.info("Start large number of S3 connections.")
        test_conf = DATA_PATH_CFG["test_1703"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        logger.info("ENDED: Persistence storage test.")

    def test_di_large_number_s3_connection_with_deletes(self):
        ops = ManagementOPs()
        users = ops.create_account_users(nusers=4)
        uploader = Uploader()
        uploader.start(users)
        DIChecker.init_s3_conn(users)
        DIChecker.verify_data_integrity(users)


if __name__ == '__main__':
    pass
