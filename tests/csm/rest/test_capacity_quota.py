# pylint: disable=too-many-lines
# !/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Tests System capacity scenarios using REST API
"""
import ast
import logging
import math
import os
import time
from http import HTTPStatus
from string import Template

import pytest
from botocore.exceptions import ClientError

from commons import configmanager
from commons import cortxlogging
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.system_utils import path_exists, make_dirs
from config import CSM_REST_CFG
from config.s3 import S3_CFG
from libs.csm.csm_interface import csm_api_factory
from libs.csm.csm_setup import CSMConfigsCheck
from libs.s3 import s3_misc
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib

# pylint: disable-msg=too-many-public-methods
# pylint: disable=too-many-instance-attributes
class TestCapacityQuota():
    """System Capacity Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.csm_obj = csm_api_factory("rest")
        cls.log.info("Initiating Rest Client ...")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_capacity.yaml")
        cls.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")
        cls.config = CSMConfigsCheck()
        setup_ready = cls.config.check_predefined_csm_user_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_users()
        assert setup_ready
        cls.created_iam_users = set()
        cls.buckets_created = []
        cls.user_id = None
        cls.display_name = None
        cls.akey = None
        cls.skey = None
        cls.bucket = None
        cls.obj_name = None
        cls.obj_name_prefix = None
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.test_file = "mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartUpload")
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)
        if not path_exists(cls.test_dir_path):
            make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)

    def setup_method(self):
        """
        Setup method for creating s3 user
        """
        self.log.info("Creating S3 account")
        self.log.info("Creating IAM user")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        self.uid = payload["uid"]
        self.user_id = resp.json()['tenant'] + "$" + self.uid
        self.created_iam_users.add(self.user_id)
        resp1 = self.csm_obj.compare_iam_payload_response(resp, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp1[0], resp1[1])
        self.akey = resp.json()["keys"][0]["access_key"]
        self.skey = resp.json()["keys"][0]["secret_key"]
        self.s3t_obj = S3TestLib(access_key=self.akey, secret_key=self.skey)
        self.bucket = "iam-user-bucket-" + str(int(time.time_ns()))
        self.display_name = "iam-display-name-" + str(int(time.time_ns()))
        self.obj_name_prefix = "created_obj"
        self.obj_name = f'{self.obj_name_prefix}{time.perf_counter_ns()}'
        self.log.info("Verify Create bucket: %s", self.bucket)
        assert s3_misc.create_bucket(self.bucket, self.akey, self.skey), "Failed to create bucket."
        self.buckets_created.append([self.bucket, self.akey, self.skey])

    def teardown_method(self):
        """
        Teardowm method for deleting s3 account created in setup.
        """
        self.log.info("Deleting buckets %s & associated objects", self.buckets_created)
        buckets_deleted = []
        iam_deleted = []
        for bucket in self.buckets_created:
            resp = s3_misc.delete_objects_bucket(bucket[0], bucket[1], bucket[2])
            if resp:
                buckets_deleted.append(bucket)
            else:
                self.log.error("Bucket deletion failed for %s ", bucket)
        self.log.info("buckets deleted %s", buckets_deleted)
        for bucket in buckets_deleted:
            self.buckets_created.remove(bucket)

        self.log.info("Deleting iam account %s created in test", self.created_iam_users)
        for iam_user in self.created_iam_users:
            resp = self.csm_obj.delete_iam_user(iam_user)
            if resp.status_code == HTTPStatus.OK:
                iam_deleted.append(iam_user)
            else:
                self.log.error("IAM deletion failed for %s ", iam_user)
        self.log.info("IAMs deleted %s", iam_deleted)
        for iam in iam_deleted:
            self.created_iam_users.remove(iam)
        assert_utils.assert_true(len(self.buckets_created) == 0, "Bucket deletion failed")
        assert_utils.assert_true(len(self.created_iam_users) == 0, "IAM deletion failed")
        self.log.info("[ENDED] ######### Teardown #########")

    def create_bucket_to_upload_parts(
            self,
            bucket_name,
            object_name,
            file_size,
            total_parts):
        """Create bucket, initiate multipart upload and upload parts."""
        self.log.info("Creating a bucket with name : %s", bucket_name)
        res = self.s3_test_obj.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", bucket_name)
        self.log.info("Initiating multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(
            bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info(
            "Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Uploading parts into bucket")
        res = self.s3_mp_test_obj.upload_parts(
            mpu_id,
            bucket_name,
            object_name,
            file_size,
            total_parts=total_parts,
            multipart_obj_path=self.mp_obj_path,
            block_size="1K",
            create_file=True)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]), total_parts, res[1])
        parts = res[1]
        self.log.info("Uploaded parts into bucket: %s", parts)
        return mpu_id, parts


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40632')
    def test_40632(self):
        """
        Test set & get API for User level quota & capacity admin user - enable
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform PUT API to set user level quota with max values")
        test_cfg = self.csm_conf["test_40632"]
        enabled = test_cfg["enabled"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        payload = self.csm_obj.iam_user_quota_payload(enabled,max_size,max_objects,
                                                    check_on_raw=True)
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 2: Perform max size verification")
        res, err_msg, obj_list = self.csm_obj.verify_max_size(max_size, self.akey, self.skey,
                                     self.bucket)
        assert res, err_msg
        for objs in obj_list:
            self.log.info("Step 3: Delete object")
            assert s3_misc.delete_object(
                    objs, self.bucket, self.akey, self.skey), "Failed to delete object."
        self.log.info("Step 4: Perform max objects verification")
        res = self.csm_obj.verify_max_objects(max_size, max_objects, self.akey, self.skey,
                                              self.bucket)
        assert res[0], res[1]
        object_list = s3_misc.get_objects_list(self.bucket,
                    self.akey, self.skey)
        self.log.info("Object list is %s ", object_list)
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40633')
    def test_40633(self):
        """
        Test set & get API for User level quota & capacity manage user - enabled
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_40633"]
        enabled = test_cfg["enabled"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        payload = self.csm_obj.iam_user_quota_payload(enabled,max_size,max_objects,
                                                  check_on_raw=True)
        self.log.info("Step 2: Perform PUT API to set user level quota with max values")
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True,
                                                               login_as="csm_user_manage")
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 3: Perform max size verification")
        res, err_msg, obj_list = self.csm_obj.verify_max_size(max_size, self.akey, self.skey,
                                     self.bucket)
        assert res, err_msg
        for objs in obj_list:
            self.log.info("Step 3: Delete object")
            assert s3_misc.delete_object(
                    objs, self.bucket, self.akey, self.skey), "Failed to delete object."
        self.log.info("Step 5: Perform max object verification")
        res = self.csm_obj.verify_max_objects(max_size, max_objects, self.akey, self.skey,
                                              self.bucket)
        assert res[0], res[1]
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40634')
    def test_40634(self):
        """
        Test set & get API for User level quota & capacity loop - random
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_40634"]
        enabled = test_cfg["enabled"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        payload = self.csm_obj.iam_user_quota_payload(enabled,max_size,max_objects,
                                  check_on_raw=True)
        for num in range(0, test_cfg["num_iterations"]):
            self.log.info("Perform get set api for iteration: %s", num)
            self.log.info("Payload is %s ", payload)
            if "max_size_kb" in payload:
                del payload["max_size_kb"]
            self.log.info("Step 2: Perform PUT API to set user level quota with max values")
            result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
            assert result, "Verification for get set user failed."
            self.log.info("Response : %s", resp)
            self.log.info("Step 3: Perform max size verification")
            res, err_msg, obj_list = self.csm_obj.verify_max_size(max_size, self.akey,
                                      self.skey, self.bucket)
            assert res, err_msg
            for objs in obj_list:
                self.log.info("Step 3: Delete object")
                assert s3_misc.delete_object(
                      objs, self.bucket, self.akey, self.skey), "Failed to delete object."
            self.log.info("Step 5: Perform max object verification")
            res, err_msg, obj_list = self.csm_obj.verify_max_objects(max_size, max_objects,
                                         self.akey, self.skey, self.bucket)
            assert res, err_msg

            for objs in obj_list:
                self.log.info("Step 6: Delete object")
                assert s3_misc.delete_object(
                       objs, self.bucket, self.akey, self.skey), "Failed to delete object."
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40635')
    def test_40635(self):
        """
        Test that if user set the disabled User level quota & capacity fields,
        other fields works as default.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_40635"]
        enabled = test_cfg["enabled"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        payload = self.csm_obj.iam_user_quota_payload(enabled,max_size,max_objects,
                              check_on_raw=True)
        self.log.info("Step 2: Perform PUT API to set user level quota with max values")
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 3: Perform max size verification")
        res, err_msg, obj_list = self.csm_obj.verify_max_size(max_size, self.akey, self.skey,
                                     self.bucket)
        assert not res, err_msg
        for objs in obj_list:
            self.log.info("Step 3: Delete object")
            assert s3_misc.delete_object(
                    objs, self.bucket, self.akey, self.skey), "Failed to delete object."
        self.log.info("Step 5: Perform max objects verification")
        res = self.csm_obj.verify_max_objects(max_size, max_objects, self.akey, self.skey,
                                              self.bucket)
        assert_utils.assert_false(res[0], res[1])
        self.log.info("##### Test ended -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40636')
    def test_40636(self):
        """
        Test set & get API for User level quota & capacity admin user - enable
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating 2 IAM user with same uid but different tenant")
        for cnt in range(2):
            tenant = "tenant_" + str(cnt)
            self.log.info("Creating new iam user with tenant %s", tenant)
            payload = self.csm_obj.iam_user_payload_rgw("random")
            self.log.info("updated payload :  %s", payload)
            resp1 = self.csm_obj.create_iam_user_rgw(payload)
            self.log.info("Verify Response : %s", resp1)
            assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            uid = resp1.json()['tenant'] + "$" + payload["uid"]
            akey = resp1.json()["keys"][0]["access_key"]
            skey = resp1.json()["keys"][0]["secret_key"]
            self.created_iam_users.add(uid)
            self.log.info("iam users set is %s ", self.created_iam_users)
            self.log.info("Step 2: Create bucket under above IAM user")
            bucket = "iam-user-bucket-" + str(int(time.time_ns()))
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, akey, skey)
            bucket_created = s3_misc.create_bucket(bucket, akey, skey)
            assert bucket_created, "Failed to create bucket"
            self.buckets_created.append([bucket, akey, skey])
            test_cfg = self.csm_conf["test_40636"]
            enabled = test_cfg["enabled"]
            max_size = test_cfg["max_size"]
            max_objects = test_cfg["max_objects"]
            payload = self.csm_obj.iam_user_quota_payload(enabled,max_size,max_objects,
                                     check_on_raw=True)
            self.log.info("Step 3: Perform PUT API to set user level quota with max values")
            result, resp = self.csm_obj.verify_get_set_user_quota(uid, payload,
                                                               verify_response=True)
            assert result, "Verification for get set user failed."
            self.log.info("Response : %s", resp)
            self.log.info("Step 4: Perform max size verification")
            res, err_msg, obj_list = self.csm_obj.verify_max_size(max_size, akey, skey,
                                     bucket)
            assert result, err_msg
            for objs in obj_list:
                self.log.info("Step 3: Delete object")
                assert s3_misc.delete_object(
                       objs, bucket, akey, skey), "Failed to delete object."
            self.log.info("Step 6: Perform max object verification")
            res = self.csm_obj.verify_max_objects(max_size, max_objects, akey, skey,
                                                 bucket)
            assert res[0], res[1]
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40637')
    def test_40637(self):
        """
        Test set & get API for User level quota & capacity for S3 user
        have already exceeded capacity
        """
        test_case_name = cortxlogging.get_frame()
        test_cfg = self.csm_conf["test_40637"]
        enabled = test_cfg["enabled"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        payload = self.csm_obj.iam_user_quota_payload(enabled,max_size,max_objects,
                                check_on_raw=True)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 3: Perform s3 operation")
        random_size = self.csm_obj.random_gen.randrange(1, max_size)
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                          self.akey, self.skey, object_size=random_size,
                                          block_size="1K")
        assert resp, "Put object Failed"
        self.log.info("Step 4: Perform get and set user level quota of less size")
        less_size = self.csm_obj.random_gen.randrange(1, max_size)
        payload = self.csm_obj.iam_user_quota_payload(enabled,less_size,max_objects,
                                         check_on_raw=True)
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40638')
    def test_40638(self):
        """
        Test set & get API for User level quota & capacity for
        S3 user have Multipart upload in-progress and then Aborted
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_40638"]
        enabled = test_cfg["enabled"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        self.log.info("Step 3: Start Multipart upload S3 operations of X Mb"
                      "X=(max_size+x)")
        bucket = "iam-user-bucket-" + str(int(time.time_ns()))
        obj_name = f'{self.obj_name_prefix}{time.perf_counter_ns()}'
        res = self.create_bucket_to_upload_parts(
            bucket,
            obj_name,
            int((max_size/1024)/2),
            test_cfg["total_parts"])
        mpu_id, parts = res
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            bucket,
            obj_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  test_cfg["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            bucket,
            obj_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(bucket)
        assert_utils.assert_in(obj_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info("Step 4: Perform get and set user level quota of less size")
        less_size = self.csm_obj.random_gen.randrange(1, max_size)
        payload = self.csm_obj.iam_user_quota_payload(enabled,less_size,max_objects,
                             check_on_raw=True)
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 5: Abort Multipart upload S3 operations")
        res = self.s3_mp_test_obj.abort_multipart_upload(
            bucket,
            obj_name,
            mpu_id)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_mp_test_obj.list_multipart_uploads(
            bucket)
        assert_utils.assert_not_in(mpu_id, res[1], res[1])
        self.log.info(
            "Aborted multipart upload with upload ID: %s", mpu_id)
        self.log.info("Step 6: Perform PUT API to set user level quota "
                      "less than used")
        resp3 = self.csm_obj.set_user_quota(self.user_id, payload)
        assert_utils.assert_true(resp3[0], resp3[1])
        self.log.info("Step 7: Perform GET API to get user level quota")
        resp4 = self.csm_obj.get_user_quota(self.user_id)
        assert_utils.assert_true(resp4[0], resp4[1])
        self.log.info("##### Test ended -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40639')
    def test_40639(self):
        """
        Test set & get API for User level quota & capacity for S3
        user have Multipart upload in-progress and then completed
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_40635"]
        enabled = test_cfg["enabled"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        self.log.info("Step 2: Start Multipart upload S3 operations of X Mb")
        bucket = "iam-user-bucket-" + str(int(time.time_ns()))
        obj_name = f'{self.obj_name_prefix}{time.perf_counter_ns()}'
        res = self.create_bucket_to_upload_parts(
            bucket,
            obj_name,
            int(max_size/1024),
            test_cfg["total_parts"])
        mpu_id, parts = res
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            bucket,
            obj_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  test_cfg["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            bucket,
            obj_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(bucket)
        assert_utils.assert_in(obj_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info("Step 3: Perform GET API to get user level quota")
        resp = self.csm_obj.get_user_quota(self.user_id)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Perform get and set user level quota of less size")
        less_size = self.csm_obj.random_gen.randrange(1, max_size)
        payload = self.csm_obj.iam_user_quota_payload(enabled,less_size,max_objects,
                                           check_on_raw=True)
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 5: Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            bucket,
            obj_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(bucket)
        assert_utils.assert_in(obj_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info("Step 6: Perform PUT API to set user level quota less than used")
        resp = self.csm_obj.set_user_quota(self.user_id, payload)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7: Perform GET API to get user level quota")
        resp = self.csm_obj.get_user_quota(self.user_id)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("##### Test ended -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-statements
    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40640')
    def test_40640(self):
        """
        Test set & get API for User level quota & capacity for S3 user
        with Multipart Abort and Simple IO in parallel.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_40640"]
        enabled = test_cfg["enabled"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        self.log.info("Step 2: Perform get and set user level quota of less size")
        less_size = self.csm_obj.random_gen.randrange(1, max_size)
        payload = self.csm_obj.iam_user_quota_payload(enabled,less_size,max_objects,
                               check_on_raw=True)
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 3: Start Multipart upload S3 operations of X Mb")
        bucket = "iam-user-bucket-" + str(int(time.time_ns()))
        obj_name = f'{self.obj_name_prefix}{time.perf_counter_ns()}'
        res = self.create_bucket_to_upload_parts(
            bucket,
            obj_name,
            max_size,
            test_cfg["total_parts"])
        mpu_id, parts = res
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            bucket,
            obj_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  test_cfg["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            bucket,
            obj_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(bucket)
        assert_utils.assert_in(obj_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info("Step 4: Perform max size verification")
        res = self.csm_obj.verify_max_size(max_size, self.akey, self.skey,
                                  bucket)
        assert res[0], res[1]
        self.log.info("Step 5: Abort Multipart upload S3 operations")
        res = self.s3_mp_test_obj.abort_multipart_upload(
            bucket,
            obj_name,
            mpu_id)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_mp_test_obj.list_multipart_uploads(
            bucket)
        assert_utils.assert_not_in(mpu_id, res[1], res[1])
        self.log.info(
            "Aborted multipart upload with upload ID: %s", mpu_id)
        self.log.info("Step 6: Perform max size verification")
        res = self.csm_obj.verify_max_size(max_size, self.akey, self.skey,
                               bucket)
        assert res[0], res[1]
        self.log.info("Step 7: Perform max objects verification")
        res = self.csm_obj.verify_max_objects(max_size, max_objects, self.akey, self.skey,
                                   bucket)
        assert res[0], res[1]
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41127')
    def test_41127(self):
        """
        Test GET capacity stats for create IAM user and Put objects using admin users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41127"]
        available_size = test_cfg["max_size"]
        random_size = self.csm_obj.random_gen.randrange(1, available_size)
        num_objects = math.floor(available_size/random_size)
        self.log.info("Random size generated is: %s", random_size)
        self.log.info("Number of objects to be created are: %s", num_objects)
        data_size = num_objects * random_size
        self.log.info("Step 1: Create N objects of Random size totals to S bytes")
        obj_name_prefix = "created_obj"
        for num in range(0, num_objects):
            obj_name = f'{obj_name_prefix}{time.perf_counter_ns()}'
            self.log.info("Creating object number %s", num)
            resp = s3_misc.create_put_objects(obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size,
                                              block_size="1K")
            assert resp, "Put object Failed"
        self.log.info("Step 3: Get capacity count from AWS")
        total_objects, total_size = s3_misc.get_objects_size_bucket(self.bucket,
                   self.akey, self.skey)
        self.log.info("total objects and size %s and %s ", total_objects, total_size)
        self.log.info("Data size is %s ", data_size)
        self.log.info("Step 4: Perform & Verify GET API to get capacity usage stats")
        resp = self.csm_obj.get_user_capacity_usage("user", self.user_id)
        assert resp.status_code == HTTPStatus.OK, \
                "Status code check failed for get capacity"
        uid = resp.json()["capacity"]["s3"]["users"][0]["id"]
        t_obj = resp.json()["capacity"]["s3"]["users"][0]["objects"]
        t_size = resp.json()["capacity"]["s3"]["users"][0]["used"]
        m_size = resp.json()["capacity"]["s3"]["users"][0]["used_rounded"]

        assert_utils.assert_equals(self.uid, uid, "id is not equal")
        assert_utils.assert_equals(total_objects, t_obj, "Number of objects not equal")
        assert_utils.assert_equals(total_objects, num_objects, "Number of objects not equal")
        assert_utils.assert_equal(total_size, t_size, "Total Size mismatch found")
        assert_utils.assert_equal(total_size, data_size*1024, "Total Size mismatch found")
        assert_utils.assert_greater_equal(m_size, total_size, "Total Used Size mismatch found ")
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41746')
    def test_41746(self):
        """
        Test GET capacity stats for create IAM user and Put objects using manage users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41746"]
        available_size = test_cfg["max_size"]
        random_size = self.csm_obj.random_gen.randrange(1, available_size)
        num_objects = math.floor(available_size / random_size)
        self.log.info("Random size generated is: %s", random_size)
        self.log.info("Number of objects to be created are: %s", num_objects)
        data_size = num_objects * random_size
        obj_list = []
        obj_name_prefix = "created_obj"
        self.log.info("Step 1: Create N objects of Random size totals to S bytes")
        for num in range(0, num_objects):
            obj_name = f'{obj_name_prefix}{time.perf_counter_ns()}'
            self.log.info("Creating object number %s", num)
            resp = s3_misc.create_put_objects(obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size,
                                              block_size="1K")
            assert resp, "Put object Failed"
            obj_list.append(obj_name)
        self.log.info("Step 3: Get capacity count from AWS")
        total_objects, total_size = s3_misc.get_objects_size_bucket(self.bucket,
                 self.akey, self.skey)
        self.log.info("total objects and size %s and %s ", total_objects, total_size)
        self.log.info("Data size is %s ", data_size)
        self.log.info("Step 4: Perform & Verify GET API to get capacity usage stats")
        resp = self.csm_obj.get_user_capacity_usage("user", self.user_id,
                         login_as="csm_user_manage")
        assert resp.status_code == HTTPStatus.OK, \
                "Status code check failed for get capacity"
        uid = resp.json()["capacity"]["s3"]["users"][0]["id"]
        t_obj = resp.json()["capacity"]["s3"]["users"][0]["objects"]
        t_size = resp.json()["capacity"]["s3"]["users"][0]["used"]
        m_size = resp.json()["capacity"]["s3"]["users"][0]["used_rounded"]
        self.log.info("Step 5: Delete object")
        for objs in obj_list:
            assert s3_misc.delete_object(
                    objs, self.bucket, self.akey, self.skey), "Failed to delete object."
        assert_utils.assert_equals(self.uid, uid, "id is not equal")
        assert_utils.assert_equals(total_objects, t_obj, "Number of objects not equal")
        assert_utils.assert_equals(total_objects, num_objects, "Number of objects not equal")
        assert_utils.assert_equal(total_size, t_size, "Total Size mismatch found")
        assert_utils.assert_equal(total_size, data_size*1024, "Total Size mismatch found")
        assert_utils.assert_greater_equal(m_size, total_size, "Total Used Size mismatch found ")
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41750')
    def test_41750(self):
        """
        Test GET capacity stats for create IAM user and Put objects using monitor users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41750"]
        available_size = test_cfg["max_size"]
        random_size = self.csm_obj.random_gen.randrange(1, available_size)
        num_objects = math.floor(available_size / random_size)
        self.log.info("Random size generated is: %s", random_size)
        self.log.info("Number of objects to be created are: %s", num_objects)
        data_size = num_objects * random_size
        obj_name_prefix = "created_obj"
        self.log.info("Step 1: Create N objects of Random size totals to S bytes")
        for num in range(0, num_objects):
            obj_name = f'{obj_name_prefix}{time.perf_counter_ns()}'
            self.log.info("Creating object number %s", num)
            resp = s3_misc.create_put_objects(obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size,
                                              block_size="1K")
            assert resp, "Put object Failed"
        self.log.info("Step 3: Get capacity count from AWS")
        total_objects, total_size = s3_misc.get_objects_size_bucket(self.bucket,
                    self.akey, self.skey)
        self.log.info("total objects and size %s and %s ", total_objects, total_size)
        self.log.info("Data size is %s ", data_size)
        self.log.info("Step 4: Perform & Verify GET API to get capacity usage stats")
        resp = self.csm_obj.get_user_capacity_usage("user", self.user_id,
                                 login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.OK, \
                "Status code check failed for get capacity"
        uid = resp.json()["capacity"]["s3"]["users"][0]["id"]
        t_obj = resp.json()["capacity"]["s3"]["users"][0]["objects"]
        t_size = resp.json()["capacity"]["s3"]["users"][0]["used"]
        m_size = resp.json()["capacity"]["s3"]["users"][0]["used_rounded"]

        assert_utils.assert_equals(self.uid, uid, "id is not equal")
        assert_utils.assert_equals(total_objects, t_obj, "Number of objects not equal")
        assert_utils.assert_equals(total_objects, num_objects, "Number of objects not equal")
        assert_utils.assert_equal(total_size, t_size, "Total Size mismatch found")
        assert_utils.assert_equal(total_size, data_size*1024, "Total Size mismatch found")
        assert_utils.assert_greater_equal(m_size, total_size, "Total Used Size mismatch found ")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41757')
    def test_41757(self):
        """
        Test GET capacity stats for delete IAM , Purge False user using admin users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41757"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        available_size = test_cfg["max_size"]
        random_size = self.csm_obj.random_gen.randrange(1, available_size)
        num_objects = math.floor(available_size / random_size)
        self.log.info("Step 1 : Creating IAM user %s")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        resp1 = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp1)
        assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                    "IAM user creation failed")
        user_id = resp1.json()['tenant'] + "$" + payload["uid"]
        resp = self.csm_obj.compare_iam_payload_response(resp1, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp[0], resp[1])
        akey = resp1.json()["keys"][0]["access_key"]
        skey = resp1.json()["keys"][0]["secret_key"]

        self.log.info("Step 2: Create bucket under above IAM user")
        bucket = "iam-user-bucket-" + str(int(time.time_ns()))
        self.log.info("Create bucket: %s with access key: %s and secret key: %s",
                          bucket, akey, skey)
        bucket_created = s3_misc.create_bucket(bucket, akey, skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Random size generated is: %s", random_size)
        self.log.info("Step 3: Created and upload Number of objects")
        for num in range(0, num_objects):
            obj_name = f'{self.obj_name_prefix}{time.perf_counter_ns()}'
            self.log.info("Creating object number %s", num)
            resp = s3_misc.create_put_objects(obj_name, bucket,
                                              akey, skey, object_size=random_size,
                                              block_size="1K")
            assert resp, "Put object Failed"
        self.log.info("Step 4: Delete iam user")
        self.log.info("Verify Delete IAM user: %s with access key: %s and secret key: %s",
                      user_id, akey, skey)
        self.log.info("Step 3: Delete objects and buckets associated with iam user")
        result = s3_misc.delete_objects_bucket(bucket, akey, skey)
        assert result, "Failed to delete buckets"
        response = self.csm_obj.delete_iam_user(user_id)
        assert response.status_code == HTTPStatus.OK, \
            "Status code check failed for user deletion"
        self.log.info("Step 4: Perform GET API to get capacity usage stats")
        resp = self.csm_obj.get_user_capacity_usage("user", user_id)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.NOT_FOUND,
                 "Status code check failed for user deletion")
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="CORTX-32043")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41758')
    def test_41758(self):
        """
        Test GET capacity stats for delete IAM , Purge True user using admin users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Create multiple objects (N) and put on 1 bucket")
        test_cfg = self.csm_conf["test_41758"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        available_size = test_cfg["max_size"]
        random_size = self.csm_obj.random_gen.randrange(1, available_size)
        num_objects = math.floor(available_size / random_size)
        self.log.info("Random size generated is: %s", random_size)
        self.log.info("Number of objects to be created are: %s", num_objects)
        for num in range(0, num_objects):
            self.log.info("Creating object number %s", num)
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size,
                                              block_size="1K")
            assert resp, "Put object Failed"
        self.log.info("Step 2: Delete iam user")
        self.log.info("Verify Delete IAM user: %s with access key: %s and secret key: %s",
                      self.user_id, self.akey, self.skey)
        self.log.info("Step 3: Delete objects and buckets associated with iam user")
        result = s3_misc.delete_all_buckets(self.akey, self.skey)
        assert result, "Failed to delete buckets"
        response = self.csm_obj.delete_iam_user(self.user_id, purge_data=True)
        assert response.status_code == HTTPStatus.OK, \
            "Status code check failed for user deletion"
        self.log.info("Step 4: Perform GET API to get capacity usage stats")
        resp = self.csm_obj.get_user_capacity_usage("user", self.user_id)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.NOT_FOUND,
                 "Status code check failed for user deletion")
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(resp.json()["message"], msg)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41128')
    def test_41128(self):
        """
        Test get capacity usage stats API for user with set quota API
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41128"]
        available_size = test_cfg["max_size"]
        random_size = self.csm_obj.random_gen.randrange(1, available_size)
        num_objects = math.floor(available_size/random_size)
        self.log.info("Random size generated is: %s", random_size)
        self.log.info("Number of objects to be created are: %s", num_objects)
        data_size = num_objects * random_size
        self.log.info("Step 2: Perform PUT API to set user level quota")
        enabled = test_cfg["enabled"]
        max_objects = test_cfg["max_objects"]
        payload = self.csm_obj.iam_user_quota_payload(enabled,available_size,max_objects,
                                 check_on_raw=True)
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                              verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 3: Perform max size verification")
        res = self.csm_obj.verify_max_size(available_size, self.akey, self.skey,self.bucket)
        assert res[0], res[1]
        self.log.info("Step 3: Get capacity count from AWS")
        total_objects, total_size = s3_misc.get_objects_size_bucket(self.bucket,
                            self.akey, self.skey)
        self.log.info("total objects and size %s and %s ", total_objects, total_size)
        self.log.info("Data size is %s ", data_size)
        self.log.info("Step 4: Perform & Verify GET API to get capacity usage stats")
        resp = self.csm_obj.get_user_capacity_usage("user", self.user_id)
        assert resp.status_code == HTTPStatus.OK, \
                "Status code check failed for get capacity"
        uid = resp.json()["capacity"]["s3"]["users"][0]["id"]
        t_obj = resp.json()["capacity"]["s3"]["users"][0]["objects"]
        t_size = resp.json()["capacity"]["s3"]["users"][0]["used"]
        m_size = resp.json()["capacity"]["s3"]["users"][0]["used_rounded"]

        assert_utils.assert_equals(self.uid, uid, "id is not equal")
        assert_utils.assert_equals(total_objects, t_obj, "Number of objects not equal")
        assert_utils.assert_equal(total_size, t_size, "Total Size mismatch found")
        assert_utils.assert_greater_equal(m_size, total_size, "Total Used Size mismatch found ")
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41151')
    def test_41151(self):
        """
        Test get capacity usage stats API for Invalid/empty fields.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41151"]
        resp_error_code_1 = test_cfg["error_code_1"]
        resp_msg_id_1 = test_cfg["message_id_1"]
        resp_data = self.rest_resp_conf[resp_error_code_1][resp_msg_id_1]
        resp_msg_index = test_cfg["message_index_1"]
        msg_1 = resp_data[resp_msg_index]
        resp_error_code_2 = test_cfg["error_code_2"]
        resp_msg_id_2 = test_cfg["message_id_2"]
        resp_data = self.rest_resp_conf[resp_error_code_2][resp_msg_id_2]
        resp_msg_index = test_cfg["message_index_2"]
        msg_2 = resp_data[resp_msg_index]
        available_size = test_cfg["max_size"]
        random_size = self.csm_obj.random_gen.randrange(1, available_size)
        num_objects = math.floor(available_size / random_size)
        self.log.info("Random size generated is: %s", random_size)
        self.log.info("Number of objects to be created are: %s", num_objects)
        self.log.info("Step 1: Create N objects of Random size totals to S bytes")
        obj_prefix = "created_obj"
        for num in range(0, num_objects):
            obj_name=f'{obj_prefix}{time.perf_counter_ns()}'
            self.log.info("Creating object number %s", num)
            resp = s3_misc.create_put_objects(obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size,
                                               block_size="1K")
            assert resp, "Put object Failed"
        self.log.info("Step 2: Perform GET API to get capacity usage "
                      "with empty key Parameters id and resource")
        uid = ""
        resource = ""
        resp = self.csm_obj.get_user_capacity_usage(resource, uid)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.NOT_FOUND,
                              "Status code check failed for get capacity")
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code_1)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id_1)
            assert_utils.assert_equals(resp.json()["message"], msg_1)
        self.log.info("Step 3: Perform GET API to get capacity usage "
                      "with invalid key Parameters id and resource")
        resource = uid = self.user_id
        resp = self.csm_obj.get_user_capacity_usage(resource, uid)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.BAD_REQUEST,
                   "Status code check failed for get capacity")
        if CSM_REST_CFG["msg_check"] == "enable":
            assert_utils.assert_equals(resp.json()["error_code"], resp_error_code_2)
            assert_utils.assert_equals(resp.json()["message_id"], resp_msg_id_2)
            assert_utils.assert_equals(resp.json()["message"],
                              Template(msg_2).substitute(A="Resource",B="user."))
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41954')
    def test_41954(self):
        """
        Test GET capacity stats for delete objects using admin users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41954"]
        available_size = test_cfg["max_size"]
        object_list = []
        random_size = self.csm_obj.random_gen.randrange(1,available_size)
        num_objects = math.floor(available_size / random_size)
        self.log.info("Random size generated is: %s", random_size)
        self.log.info("Number of objects to be created are: %s", num_objects)
        self.log.info("Step 1: Create N objects of Random size totals to S bytes")
        for num in range(0, num_objects):
            obj_name = f'{self.obj_name_prefix}{time.perf_counter_ns()}'
            self.log.info("Creating object number %s", num)
            resp = s3_misc.create_put_objects(obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size,
                                              block_size="1K")
            object_list.append(obj_name)
            assert resp, "Put object Failed"
        self.log.info("Printing object list: %s ", object_list)
        self.log.info("Step 3: Get capacity count from AWS")
        obj_before_deletion, size_before_deletion = s3_misc.get_objects_size_bucket(self.bucket,
                      self.akey, self.skey)
        for obj in object_list:
            self.log.info("Step 4: Delete object: %s", obj)
            assert s3_misc.delete_object(
                obj, self.bucket, self.akey, self.skey), "Failed to delete bucket."
            self.log.info("Step 5: Get capacity count from AWS")
            total_objects, total_size = s3_misc.get_objects_size_bucket(self.bucket,
                         self.akey, self.skey)
            if num_objects == 1:
                assert total_size == 0, "Total size remains same even after object deletion"
                assert total_objects == 0, "Object count did not reduce"
            else:
                self.log.info("AVailable size %s, total_size %s, random_size %s ",
                                               available_size, total_size, random_size)
                assert_utils.assert_greater_equal(size_before_deletion, total_size,
                       "Total size remains same even after object deletion")
                assert_utils.assert_greater_equal(obj_before_deletion, total_objects,
                                                "Object count did not reduce" )
            self.log.info("Step 6: Perform GET API to get capacity usage")
            resp = self.csm_obj.get_user_capacity_usage("user", self.user_id)
            assert resp.status_code == HTTPStatus.OK, \
                "Status code check failed for get capacity"
        self.log.info("Step 7: Get capacity count from AWS")
        total_objects, total_size = s3_misc.get_objects_size_bucket(self.bucket,
                         self.akey, self.skey)
        self.log.info("Step 8: Perform GET API to get capacity usage")
        resp = self.csm_obj.get_user_capacity_usage("user", self.user_id)
        assert resp.status_code == HTTPStatus.OK, \
                "Status code check failed for get capacity"
        uid = resp.json()["capacity"]["s3"]["users"][0]["id"]
        t_obj = resp.json()["capacity"]["s3"]["users"][0]["objects"]
        t_size = resp.json()["capacity"]["s3"]["users"][0]["used"]
        m_size = resp.json()["capacity"]["s3"]["users"][0]["used_rounded"]

        assert_utils.assert_equals(self.uid, uid, "id is not equal")
        assert_utils.assert_equals(t_obj, 0, "Number of objects not equal")
        assert_utils.assert_equal(t_size, 0, "Total Size mismatch found")
        assert_utils.assert_equal(total_size, 0, "Total Size mismatch found")
        assert_utils.assert_greater_equal(m_size, 0, "Total Used Size mismatch found ")
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41172')
    def test_41172(self):
        """
        Test get capacity usage stats API of multiple S3 users, and 1 bucket per user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41172"]
        available_size = test_cfg["available_size"]
        min_users = test_cfg["min_users"]
        max_users = test_cfg["max_users"]
        random_users = self.csm_obj.random_gen.randrange(min_users, max_users)

        for user in range(0, random_users):
            self.log.info("Step 1 : Creating IAM user %s", user)
            payload = self.csm_obj.iam_user_payload_rgw("random")
            resp1 = self.csm_obj.create_iam_user_rgw(payload)
            self.log.info("Verify Response : %s", resp1)
            assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                    "IAM user creation failed")
            user_id = resp1.json()['tenant'] + "$" + payload["uid"]
            self.created_iam_users.add(user_id)
            resp = self.csm_obj.compare_iam_payload_response(resp1, payload)
            self.log.info("Printing response %s", resp1)
            assert_utils.assert_true(resp[0], resp[1])
            akey = resp1.json()["keys"][0]["access_key"]
            skey = resp1.json()["keys"][0]["secret_key"]

            self.log.info("Step 2: Create bucket under above IAM user")
            bucket = "iam-user-bucket-" + str(int(time.time_ns()))
            self.log.info("Create bucket: %s with access key: %s and secret key: %s",
                          bucket, akey, skey)
            bucket_created = s3_misc.create_bucket(bucket, akey, skey)
            assert bucket_created, "Failed to create bucket"
            self.buckets_created.append([bucket, akey, skey])

            obj_name_prefix = "created_obj"
            random_size = self.csm_obj.random_gen.randrange(1, available_size)
            num_objects = math.floor(available_size/random_size)
            data_size = num_objects * random_size
            obj_list = []
            self.log.info("Step 3: Create %s objects of Random size totals to %s bytes",
                          num_objects, data_size)
            for obj in range(0, num_objects):
                obj_name = f'{obj_name_prefix}{time.perf_counter_ns()}'
                self.log.info("initiate put object %s", obj)
                resp = s3_misc.create_put_objects(obj_name, bucket,
                                                akey, skey, object_size=random_size,
                                                 block_size="1K")
                assert_utils.assert_true(resp, "Put object Failed")
                obj_list.append(obj_name)
            self.log.info("Step 3: Get capacity count from AWS")
            total_objects, total_size = s3_misc.get_objects_size_bucket(bucket, akey, skey)
            self.log.info("total objects and size %s and %s ", total_objects, total_size)
            self.log.info("Data size is %s ", data_size)
            self.log.info("Step 4: Perform & Verify GET API to get capacity usage stats")
            resp = self.csm_obj.get_user_capacity_usage("user", user_id)
            assert resp.status_code == HTTPStatus.OK, \
                "Status code check failed for get capacity"
            uid = resp.json()["capacity"]["s3"]["users"][0]["id"]
            t_obj = resp.json()["capacity"]["s3"]["users"][0]["objects"]
            t_size = resp.json()["capacity"]["s3"]["users"][0]["used"]
            m_size = resp.json()["capacity"]["s3"]["users"][0]["used_rounded"]
            for objs in obj_list:
                self.log.info("Step 3: Delete object")
                assert s3_misc.delete_object(
                    objs, bucket, akey, skey), "Failed to delete object."
            assert_utils.assert_equals(resp1.json()['user_id'], uid, "id is not equal")
            assert_utils.assert_equals(total_objects, t_obj, "Number of objects not equal")
            assert_utils.assert_equals(total_objects, num_objects, "Number of objects not equal")
            assert_utils.assert_equal(
                total_size, t_size, "Total Size mismatch found")
            assert_utils.assert_equal(
                total_size / 1024, data_size, "Total Size mismatch found")
            assert_utils.assert_greater_equal(
                m_size, total_size, "Total Used Size mismatch found ")

        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41173')
    def test_41173(self):
        """
        Test get capacity usage stats API of 1 S3 user and multiple buckets under it
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41173"]
        available_size = test_cfg["available_size"]
        min_bucket = test_cfg["min_bucket"]
        max_bucket = test_cfg["max_bucket"]
        random_bucket = self.csm_obj.random_gen.randrange(min_bucket, max_bucket)
        total_objects = 0
        total_size = 0
        total_data_size = 0
        total_num_objects = 0

        for bkt in range(0, random_bucket):
            self.log.info("Step 1 : Creating bucket %s", bkt)
            bucket = "iam-user-bucket-" + str(int(time.time_ns()))
            self.log.info("Create bucket: %s with access key: %s and secret key: %s",
                          bucket, self.akey, self.skey)
            bucket_created = s3_misc.create_bucket(bucket, self.akey, self.skey)
            assert bucket_created, "Failed to create bucket"
            self.buckets_created.append([bucket, self.akey, self.skey])

            obj_name_prefix = "created_obj"
            random_size = self.csm_obj.random_gen.randrange(1, available_size)
            num_objects = math.floor(available_size/random_size)
            bucket_data_size = num_objects * random_size
            obj_list = []
            self.log.info("Step 2: Create %s objects of Random size totals to %s bytes",
                          num_objects, bucket_data_size)
            for obj in range(0, num_objects):
                obj_name = f'{obj_name_prefix}{time.perf_counter_ns()}'
                self.log.info("initiate put object %s", obj)
                resp = s3_misc.create_put_objects(obj_name, bucket,
                                                self.akey, self.skey,
                                                object_size=int(random_size/1024*1024),
                                                block_size="1K")
                assert_utils.assert_true(resp, "Put object Failed")
                obj_list.append(obj_name)
            self.log.info("Step 3: Get capacity count from AWS")
            (bucket_objects, bucket_size) = \
                                    s3_misc.get_objects_size_bucket(bucket, self.akey, self.skey)
            assert_utils.assert_equals(bucket_objects, num_objects, "Number of objects not equal")
            assert_utils.assert_equal(
                bucket_size / (1024), bucket_data_size, "Total Size mismatch found")

            total_objects = total_objects + bucket_objects
            total_size = total_size + bucket_size
            total_data_size = total_data_size + bucket_data_size
            total_num_objects = total_num_objects + num_objects

        self.log.info("Step 4: Perform & Verify GET API to get capacity usage stats")
        resp = self.csm_obj.get_user_capacity_usage("user", self.user_id)
        assert resp.status_code == HTTPStatus.OK, \
            "Status code check failed for get capacity"
        uid = resp.json()["capacity"]["s3"]["users"][0]["id"]
        t_obj = resp.json()["capacity"]["s3"]["users"][0]["objects"]
        t_size = resp.json()["capacity"]["s3"]["users"][0]["used"]
        m_size = resp.json()["capacity"]["s3"]["users"][0]["used_rounded"]
        for objs in obj_list:
            self.log.info("Step 3: Delete object")
            assert s3_misc.delete_object(
                    objs, bucket, self.akey, self.skey), "Failed to delete object."
        assert_utils.assert_equals(self.uid, uid, "uid is not equal")
        assert_utils.assert_equals(total_objects, t_obj, "Number of objects not equal")
        assert_utils.assert_equals(total_objects, total_num_objects, "Number of objects not equal")
        assert_utils.assert_equal(
            total_size, t_size, "Total Size mismatch found")
        assert_utils.assert_equal(
            total_size / 1024, total_data_size, "Total Size mismatch found")
        assert_utils.assert_greater_equal(
                m_size, total_size, "Total Used Size mismatch found ")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41156')
    def test_41156(self):
        """
        Test get capacity usage stats API for multiple tenants
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41156"]
        available_size = test_cfg["available_size"]
        min_users = test_cfg["min_users"]
        max_users = test_cfg["max_users"]
        random_users = self.csm_obj.random_gen.randrange(min_users, max_users)
        for tnt in range(0, random_users):
            tenant = "tenant_" + system_utils.random_string_generator()
            self.log.info("Step 1 : Creating new iam user with tenant %s in loop %s", tenant, tnt)
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            self.log.info("updated payload :  %s", optional_payload)
            resp1 = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp1)
            assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            user_id = resp1.json()['tenant'] + "$" + optional_payload['uid']
            self.created_iam_users.add(user_id)
            resp = self.csm_obj.compare_iam_payload_response(resp1, optional_payload)
            self.log.info("Printing response %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            akey = resp1.json()["keys"][0]["access_key"]
            skey = resp1.json()["keys"][0]["secret_key"]

            self.log.info("Step 2: Create bucket under above IAM user")
            bucket = "iam-user-bucket-" + str(int(time.time_ns()))
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, akey, skey)
            bucket_created = s3_misc.create_bucket(bucket, akey, skey)
            assert bucket_created, "Failed to create bucket"
            self.buckets_created.append([bucket, akey, skey])

            obj_name_prefix = "created_obj"
            random_size = self.csm_obj.random_gen.randrange(1, available_size)
            num_objects = math.floor(available_size/random_size)
            data_size = num_objects * random_size
            obj_list = []
            self.log.info("Step 3: Create %s objects of Random size totals to %s bytes",
                          num_objects, data_size)
            for obj in range(0, num_objects):
                obj_name = f'{obj_name_prefix}{time.perf_counter_ns()}'
                self.log.info("initiate put object %s", obj)
                resp = s3_misc.create_put_objects(obj_name, bucket,
                                                akey, skey, object_size=random_size,
                                                block_size="1K")
                assert_utils.assert_true(resp, "Put object Failed")
                obj_list.append(obj_name)
            self.log.info("Step 3: Get capacity count from AWS")
            total_objects, total_size = s3_misc.get_objects_size_bucket(bucket, akey, skey)

            self.log.info("Step 4: Perform & Verify GET API to get capacity usage stats")
            resp = self.csm_obj.get_user_capacity_usage("user", user_id)
            assert resp.status_code == HTTPStatus.OK, \
                "Status code check failed for get capacity"
            uid = resp.json()["capacity"]["s3"]["users"][0]["id"]
            t_obj = resp.json()["capacity"]["s3"]["users"][0]["objects"]
            t_size = resp.json()["capacity"]["s3"]["users"][0]["used"]
            m_size = resp.json()["capacity"]["s3"]["users"][0]["used_rounded"]
            for objs in obj_list:
                self.log.info("Step 3: Delete object")
                assert s3_misc.delete_object(
                    objs, bucket, akey, skey), "Failed to delete object."
            assert_utils.assert_equals(resp1.json()['user_id'], uid, "uid is not equal")
            assert_utils.assert_equals(total_objects, t_obj, "Number of objects not equal")
            assert_utils.assert_equals(total_objects, num_objects, "Number of objects not equal")
            assert_utils.assert_equal(
                total_size, t_size, "Total Size mismatch found")
            assert_utils.assert_equal(
                total_size / 1024, data_size, "Total Size mismatch found")
            assert_utils.assert_greater_equal(
                m_size, total_size, "Total Used Size mismatch found ")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41964')
    def test_41964(self):
        """
        Test set API for User level quota/capacity greater then available and
        full 100%
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41964"]
        quota_type = test_cfg["quota_type"]
        enabled = test_cfg["enabled"]
        max_objects = test_cfg["max_objects"]
        list_factors = []
        self.log.info("Step 1: Check the total available capacity")
        resp = self.csm_obj.get_capacity_usage()
        assert resp.status_code == HTTPStatus.OK, \
            "Status code check failed for get capacity"
        total_available = resp.json()["capacity"]["system"]["cluster"][0]["available"]
        max_size = total_available + test_cfg["extra_bytes"]
        self.log.info("Step 2: Set max size to greater than available capacity")
        payload = self.csm_obj.iam_user_quota_payload(quota_type, enabled, max_size, max_objects)
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                              verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 3: Completely full the storage capacity full")
        for i in range(1, test_cfg["extra_bytes"]):
            if test_cfg["extra_bytes"] % i == 0:
                list_factors.append(i)
        random_size = list_factors[-1]
        random_objects = math.floor(total_available/random_size)
        for num in range(0, random_objects):
            self.log.info("Creating object number %s", num)
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey,
                                              object_size=random_size)
            assert resp, "Put object Failed"
        self.log.info("Step 4: Perform & Verify GET API to get capacity usage stats")
        resp = self.csm_obj.get_user_capacity_usage("user", self.user_id)
        assert resp.status_code == HTTPStatus.OK, \
            "Status code check failed for get capacity"
        avail_size = resp.json()["capacity"]["s3"]["user"][0]["used_total"]
        assert_utils.assert_equal(avail_size, "0", "Total Used Size mismatch found")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41965')
    def test_41965(self):
        """
        Test SET and GET quota with negative max objects
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform PUT API to set valid max size and negative "
                      "max object value")
        test_cfg = self.csm_conf["test_41965"]
        max_size = test_cfg["max_size"]
        small_size = test_cfg["small_size"]
        enabled = test_cfg["enabled"]
        max_objects = -(self.csm_obj.random_gen.randrange(1, small_size))
        payload = self.csm_obj.iam_user_quota_payload(enabled, max_size, max_objects,
                                  check_on_raw=True)
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                              verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 2: Perform max size number of 1MB objects")
        for num in range(0, int(max_size/1024)):
            self.log.info("Creating object number %s", num)
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey,
                                              object_size=int(small_size/1024),
                                              block_size="1K")
            assert resp, "Put object Failed"
        self.log.info("Maximum amount of objects should be created since max_objects"
                      "parameter is not effective")
        self.log.info("Step 3: Perform put 1 object of random size")
        random_size = self.csm_obj.random_gen.randrange(1, max_size)
        try:
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                          self.akey, self.skey, object_size=random_size,
                                          block_size="1K")
        except ClientError as error:
            self.log.info("Expected exception received %s", error)
            assert error.response['Error']['Code'] == "QuotaExceeded", \
                                      "Put operation passed after max size"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41966')
    def test_41966(self):
        """
        Test SET and GET quota with negative max size
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform PUT API to set negative max size and valid"
                      "max object value")
        test_cfg = self.csm_conf["test_41966"]
        available_size = test_cfg["available_size"]
        max_size = -(self.csm_obj.random_gen.randrange(1, available_size))
        enabled = test_cfg["enabled"]
        max_objects = test_cfg["max_objects"]
        self.log.info("Step 2: Perform get set user quota")
        payload = self.csm_obj.iam_user_quota_payload(enabled, max_size, max_objects,
                                      check_on_raw=True)
        resp = self.csm_obj.set_user_quota(self.user_id, payload)
        self.log.info("Set quota API response: %s", resp.json())
        assert resp.status_code == HTTPStatus.OK, "Status code check failed"
        res = self.csm_obj.get_user_quota(self.user_id)
        assert res.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Step 3: Perform max_objects upload of random size")
        res = self.csm_obj.verify_max_objects(available_size, max_objects, self.akey, self.skey,
                                              self.bucket)
        assert res[0], res[1]
        self.log.info("Only maximum number of objects specified of any size should"
                      "be uploaded since max_size parameter is ineffective")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable=broad-except
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41967')
    def test_41967(self):
        """
        Test SET and GET quota with negative max objects and size
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform PUT API to set valid max size and negative "
                      "max object value")
        test_cfg = self.csm_conf["test_41967"]
        enabled = test_cfg["enabled"]
        size_for_io = test_cfg["size_for_io"]
        objects_for_io = test_cfg["objects_for_io"]
        max_size = -(self.csm_obj.random_gen.randrange(1, size_for_io))
        max_objects = -(self.csm_obj.random_gen.randrange(1, objects_for_io))
        self.log.info("Step 2: Perform get set user quota")
        payload = self.csm_obj.iam_user_quota_payload(enabled, max_size,
                                                      max_objects,check_on_raw=True)
        resp = self.csm_obj.set_user_quota(self.user_id, payload)
        self.log.info("Set quota API response: %s", resp.json())
        assert resp.status_code == HTTPStatus.OK, "Status code check failed"
        res = self.csm_obj.get_user_quota(self.user_id)
        assert res.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Step 2: Performing IOs of any size and any number of objects"
                      "should pass")
        for num in range(0, objects_for_io):
            self.log.info("Creating an uploading object %s:", num)
            random_size = math.floor(size_for_io/objects_for_io)
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size,
                                              block_size="1K")
            assert resp, "Put object Failed"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41968')
    def test_41968(self):
        """
        Test IO operations on suspended IAM user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Creating IAM user with suspended False")
        uid = "iam_user_1_" + str(int(time.time()))
        bucket_name = "iam-user-bucket-" + str(int(time.time()))
        self.log.info("Creating new iam user  %s", uid)
        payload = self.csm_obj.iam_user_payload_rgw("random")
        payload.update({"suspended": False})
        resp1 = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp1)
        assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                 "IAM user creation failed")
        user_id = resp1.json()['tenant'] + "$" + payload["uid"]
        self.created_iam_users.add(user_id)
        resp = self.csm_obj.compare_iam_payload_response(resp1, payload)
        assert_utils.assert_true(resp[0], resp[1])
        akey = resp1.json()["keys"][0]["access_key"]
        skey = resp1.json()["keys"][0]["secret_key"]
        self.log.info("Step 2: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      bucket_name, akey, skey)
        bucket_created = s3_misc.create_bucket(bucket_name, akey, skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 3: Perform IOs")
        obj_name = f'{self.obj_name_prefix}{time.perf_counter_ns()}'
        resp = s3_misc.create_put_objects(obj_name, bucket_name,
                                          akey, skey)
        assert resp, "Put object Failed"
        buckets_deleted = []
        resp = s3_misc.delete_objects_bucket(bucket_name, akey,
                           skey)
        if resp:
            buckets_deleted.append(bucket_name)
            self.log.info("buckets deleted %s ", buckets_deleted)
        else:
            self.log.error("Bucket deletion failed for %s ", bucket_name)
        self.log.info("Step 4: Update Suspended True for same IAM User")
        payload = {}
        payload.update({"suspended": True})
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, \
                  "Status code check failed for updating iam user."
        self.log.info("Step 5: Perform IOs on previously created bucket")
        try:
            resp = s3_misc.create_put_objects(self.obj_name, bucket_name,
                                          akey, skey)
            assert_utils.assert_false(resp, "Put object Failed")
        except Exception as error:
            self.log.info("Expected exception received %s", error)

        self.log.info("Step 5: Update Suspended False for same IAM User")
        payload = {}
        payload.update({"suspended": False})
        response = self.csm_obj.modify_iam_user_rgw(user_id, payload)
        assert response.status_code == HTTPStatus.OK, \
                  "Status code check failed for updating iam user."
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      bucket_name, akey, skey)
        bucket_name = "iam-user-bucket-" + str(int(time.time()))
        bucket_created = s3_misc.create_bucket(bucket_name, akey, skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 6: Perform IOs")
        obj_name = f'{self.obj_name_prefix}{time.perf_counter_ns()}'
        resp = s3_misc.create_put_objects(obj_name, bucket_name,
                                          akey, skey)
        assert resp, "Put object Failed"
        resp = s3_misc.delete_objects_bucket(bucket_name, akey,
                           skey)
        if resp:
            buckets_deleted.append(bucket_name)
            self.log.info("buckets deleted %s ", buckets_deleted)
        else:
            self.log.error("Bucket deletion failed for %s ", bucket_name)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41970')
    def test_41970(self):
        """
        Test with Login and logout in loop
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41970"]
        duration = test_cfg["duration"]
        t_end = time.time() + duration
        while time.time() < t_end:
            self.log.info("Step 1: Login using admin user")
            response = self.csm_obj.custom_rest_login(
                username=self.csm_obj.config["csm_admin_user"]["username"],
                password=self.csm_obj.config["csm_admin_user"]["password"])
            assert_utils.assert_equals(response.status_code, HTTPStatus.OK)
            self.log.info("Step 2: Login using manage user")
            response = self.csm_obj.custom_rest_login(
                username=self.csm_obj.config["csm_user_manage"]["username"],
                password=self.csm_obj.config["csm_user_manage"]["password"])
            assert_utils.assert_equals(response.status_code, HTTPStatus.OK)
            self.log.info("Step 3: Login using monitor user")
            response = self.csm_obj.custom_rest_login(
                username=self.csm_obj.config["csm_user_monitor"]["username"],
                password=self.csm_obj.config["csm_user_monitor"]["password"])
            assert_utils.assert_equals(response.status_code, HTTPStatus.OK)

            self.log.info("Step 4: Logout admin user")
            self.log.info("Get header")
            header = self.csm_obj.get_headers(
                self.csm_obj.config["csm_admin_user"]["username"],
                self.csm_obj.config["csm_admin_user"]["password"])
            self.log.info("Logout user session")
            response = self.csm_obj.csm_user_logout(header)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
            self.log.info("Step 5: Logout manage user")
            self.log.info("Get header")
            header = self.csm_obj.get_headers(
                self.csm_obj.config["csm_user_manage"]["username"],
                self.csm_obj.config["csm_user_manage"]["password"])
            self.log.info("Logout user session")
            response = self.csm_obj.csm_user_logout(header)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
            self.log.info("Step 6: Logout monitor user")
            self.log.info("Get header")
            header = self.csm_obj.get_headers(
                self.csm_obj.config["csm_user_monitor"]["username"],
                self.csm_obj.config["csm_user_monitor"]["password"])
            self.log.info("Logout user session")
            response = self.csm_obj.csm_user_logout(header)
            self.csm_obj.check_expected_response(response, HTTPStatus.OK)
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40600')
    def test_40600(self):
        """
        Test that user can set and get the User level quota/capacity.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Step 2: Perform PUT API to set user level quota fields.")
        test_cfg = self.csm_conf["test_40600"]
        enabled = test_cfg["enabled"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        quota_payload = {"enabled": enabled, "max_size": max_size,
                         "max_objects": max_objects}
        resp = self.csm_obj.set_user_quota(user_id, quota_payload)
        self.log.info("Set quota API response: %s", resp.json())
        assert resp.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Step 3: Perform GET API to get user level quota fields.")
        res = self.csm_obj.get_user_quota(user_id)
        assert res.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Step 4: Verify the user level quota fields as per request.")
        user_quota = res.json()
        self.log.info("response: %s", user_quota)
        assert user_quota['enabled'] == ast.literal_eval('True'), "Status check failed"
        assert user_quota['max_size'] == max_size, "Max size field not matched"
        assert user_quota['max_objects'] == max_objects, "Objects field not matched"
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40601')
    def test_40601(self):
        """
        Test that user can set and get the disabled User level quota/capacity fields for S3 user.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Step 2: Perform PUT API to set user level quota fields.")
        max_size, max_objects = self.csm_obj.get_rand_int(10, 10)
        test_cfg = self.csm_conf["test_40601"]
        enabled = test_cfg["enabled"]
        quota_payload = {"enabled": enabled, "max_size": max_size,
                         "max_objects": max_objects}
        resp = self.csm_obj.set_user_quota(user_id, quota_payload)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Step 3: Perform GET API to get user level quota as enabled")
        res = self.csm_obj.get_user_quota(user_id)
        assert res.status_code == HTTPStatus.OK, "Status code check failed"
        user_quota = res.json()
        self.log.info("Step 4: Verify the user level quota fields as per request.")
        assert user_quota['enabled'] == ast.literal_eval('True'), "Status check failed"
        assert user_quota['max_size'] == int(max_size), "Max size field not matched"
        assert user_quota['max_objects'] == int(max_objects), "Objects field not matched"
        self.log.info("Step 5: Perform PUT API to set user level quota as disabled")
        quota_payload = {"enabled": False, "max_size": max_size,
                         "max_objects": max_objects}
        resp = self.csm_obj.set_user_quota(user_id, quota_payload)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Step 6: Perform GET API to get user level quota fields.")
        res = self.csm_obj.get_user_quota(user_id)
        assert res.status_code == HTTPStatus.OK, "Status code check failed"
        user_quota = res.json()
        self.log.info("Step 7: Verify the user level quota fields as per above request.")
        assert user_quota['enabled'] == ast.literal_eval('False'), "Status check failed"
        assert user_quota['max_size'] == int(max_size), "Max size field not matched"
        assert user_quota['max_objects'] == int(max_objects), "Objects field not matched"
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40602')
    def test_40602(self):
        """
        Test that user can set and get the User level quota/capacity by get user info API.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Step 2: Perform PUT API to set user level quota fields.")
        test_cfg = self.csm_conf["test_40602"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        enabled = test_cfg["enabled"]
        quota_payload = {"enabled": enabled, "max_size": max_size,
                         "max_objects": max_objects}
        resp = self.csm_obj.set_user_quota(user_id, quota_payload)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Step 3: Perform GET I AM user info API to get user level quota")
        res = self.csm_obj.get_iam_user(user_id)
        assert res.status_code == HTTPStatus.OK, "Status code check failed"
        user_quota = res.json()
        self.log.info("Step 4: Verify the user info level quota fields as per request.")
        assert user_quota['user_quota']['enabled'] == ast.literal_eval('True'), "Status check fail"
        assert user_quota['user_quota']['max_size'] == max_size, "Maxsize field not matched"
        assert user_quota['user_quota']['max_objects'] == max_objects, "Objects field not matched"
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40603')
    def test_40603(self):
        """
        Test that monitor user can not set the User level quota/capacity.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Step 2: Perform PUT API to set user level quota fields.")
        test_cfg = self.csm_conf["test_40603"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        enabled = test_cfg["enabled"]
        quota_payload = {"enabled": enabled, "max_size": max_size,
                         "max_objects": max_objects}
        resp = self.csm_obj.set_user_quota(user_id, quota_payload,
                                           login_as="csm_user_monitor")
        assert resp.status_code == HTTPStatus.FORBIDDEN, "Status code check failed"
        self.log.info("Step 3: Perform GET API to get user level quota fields.")
        res = self.csm_obj.get_user_quota(user_id)
        assert res.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40604')
    def test_40604(self):
        """
        Test that user can set and get the User level quota/capacity under the tenant.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user under the tenant.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "tenant": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Step 2: Perform PUT API(tenant$uid) to set user level quota fields")
        resp_dict = response.json()
        test_cfg = self.csm_conf["test_40604"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        tenant_user = resp_dict['tenant'] + "$" + payload['uid']
        enabled = test_cfg["enabled"]
        quota_payload = {"enabled": enabled, "max_size": max_size,
                         "max_objects": max_objects}
        resp = self.csm_obj.set_user_quota(tenant_user, quota_payload)
        assert resp.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Step 3: Perform GET API(tenant$uid) to get user level quota fields.")
        res = self.csm_obj.get_user_quota(tenant_user)
        assert res.status_code == HTTPStatus.OK, "Status code check failed"
        self.log.info("Step 4: Verify the user level quota fields as per request.")
        user_quota = res.json()
        assert user_quota['enabled'] == ast.literal_eval('True'), "Status check failed"
        assert user_quota['max_size'] == max_size, "Max size field not matched"
        assert user_quota['max_objects'] == max_objects, "Objects field not matched"
        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-40605')
    def test_40605(self):
        """
        Test set/get API for User level quota/capacity with Invalid/empty fields.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Perform POST API to create user.")
        self.log.info("Creating IAM user payload.")
        user_id, display_name = self.csm_obj.get_iam_user_payload()
        payload = {"uid": user_id, "display_name": display_name}
        self.log.info("payload :  %s", payload)
        self.log.info("Creating IAM user.")
        response = self.csm_obj.create_iam_user_rgw(payload)
        assert response.status_code == HTTPStatus.CREATED, "Status code check failed"
        self.log.info("Step 2: PUT API to set user level quota with empty fields")
        quota_payload = {"enabled": "", "max_size": "",
                         "max_objects": ""}
        resp = self.csm_obj.set_user_quota(user_id, quota_payload)
        self.log.info("response :  %s", resp)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed"
        self.log.info("Step 3: Perform PUT API to set user quota with empty fields")
        quota_payload = {"enabled": None, "max_size": None,
                         "max_objects": None}
        resp = self.csm_obj.set_user_quota(user_id, quota_payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed"
        self.log.info("Step 4: PUT API to set user quota with invalid/empty user quota endpoint.")
        resp = self.csm_obj.set_user_quota("", quota_payload)
        assert resp.status_code == HTTPStatus.NOT_FOUND, "Status code check failed"
        self.log.info("Step 5: GET API to get user quota fields with invalid/empty endpoint.")
        res = self.csm_obj.get_user_quota("")
        self.log.info("response :  %s", res)
        assert res.status_code == HTTPStatus.NOT_FOUND, "Status code check failed"
