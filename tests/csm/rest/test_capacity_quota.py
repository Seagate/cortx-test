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
import logging
import math
import os
import time
from http import HTTPStatus
from random import SystemRandom
from time import perf_counter_ns

import pytest

from commons import commands
from commons import configmanager
from commons import cortxlogging
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import run_local_cmd
from config.s3 import S3_CFG
from libs.csm.csm_interface import csm_api_factory
from libs.s3 import s3_misc
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib

# pylint: disable=too-many-instance-attributes
class TestCapacityQuota():
    """System Capacity Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.csm_obj = csm_api_factory("rest")
        cls.cryptogen = SystemRandom()
        cls.log.info("Initiating Rest Client ...")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_capacity.yaml")
        cls.created_iam_users = set()
        cls.buckets_created = []
        cls.user_id = None
        cls.display_name = None
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.test_file = "mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartUpload")
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)

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
        self.user_id = resp.json()['tenant'] + "$" + payload["uid"]
        self.created_iam_users.add(self.user_id)
        resp1 = self.csm_obj.compare_iam_payload_response(resp, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp1[0], resp1[1])
        self.akey = resp.json()["access_key"]
        self.skey = resp.json()["secret_key"]
        self.bucket = "iam-user-bucket-" + str(int(time.time_ns()))
        self.obj_name_prefix = "created_obj"
        self.obj_name = "{0}{1}".format(self.obj_name_prefix, perf_counter_ns())
        self.display_name = "iam-display-name-" + str(int(time.time_ns()))
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        self.cryptogen = SystemRandom()
        assert s3_misc.create_bucket(self.bucket, self.akey, self.skey), "Failed to create bucket."

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
            resp = s3_misc.delete_iam_user(iam_user[0], iam_user[1], iam_user[2])
            if resp:
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
            multipart_obj_path=self.mp_obj_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]), total_parts, res[1])
        parts = res[1]
        self.log.info("Uploaded parts into bucket: %s", parts)
        return mpu_id, parts

    @pytest.mark.skip("Feature not ready")
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
        self.log.info("Step 1: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
        self.bucket, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 2: Perform PUT API to set user level quota with max values")
        test_cfg = self.csm_conf["test_40632"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        payload = self.csm_obj.iam_user_quota_payload()
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 3: Perform put object of max size")
        self.csm_obj.verify_max_size(max_size)
        self.log.info("Step 4: Delete object")
        assert s3_misc.delete_object(
            self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
        self.log.info("Step 5: Perform put objects of small size")
        self.csm_obj.verify_max_objects(max_size, max_objects)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
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
        self.log.info("Step 1: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        test_cfg = self.csm_conf["test_40633"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        self.log.info("Step 2: Perform PUT API to set user level quota with max values")
        payload = self.csm_obj.iam_user_quota_payload()
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 3: Perform put object of max size")
        self.csm_obj.verify_max_size(max_size)
        self.log.info("Step 4: Delete object")
        assert s3_misc.delete_object(
            self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
        self.log.info("Step 5: Perform put objects of small size")
        self.csm_obj.verify_max_objects(max_size, max_objects)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
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
        self.log.info("Step 1: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        test_cfg = self.csm_conf["test_40634"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        for num in range(0, test_cfg["num_iterations"]):
            self.log.info("Perform get set api for iteration: %s", num)
            self.log.info("Step 2: Perform PUT API to set user level quota")
            payload = self.csm_obj.iam_user_quota_payload()
            result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
            assert result, "Verification for get set user failed."
            self.log.info("Response : %s", resp)
            self.log.info("Step 3: Perform put object of max size")
            self.csm_obj.verify_max_size(max_size)
            self.log.info("Step 4: Delete object")
            assert s3_misc.delete_object(
                self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
            self.log.info("Step 5: Perform put objects of small size")
            self.csm_obj.verify_max_objects(max_size, max_objects)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
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
        self.log.info("Step 2: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        test_cfg = self.csm_conf["test_40635"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        self.log.info("Step 2: Perform PUT API to set user level quota with max values")
        payload = self.csm_obj.iam_user_quota_payload()
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                               verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 3: Perform put object of max size")
        self.csm_obj.verify_max_size(max_size)
        self.log.info("Step 4: Delete object")
        assert s3_misc.delete_object(
            self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
        self.log.info("Step 5: Perform put objects of small size")
        self.csm_obj.verify_max_objects(max_size, max_objects)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.skip("Feature not ready")
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
            optional_payload = self.csm_obj.iam_user_payload_rgw("loaded")
            optional_payload.update({"tenant": tenant})
            optional_payload.update({"uid": self.user_id})
            optional_payload.update({"display_name": self.display_name})
            self.log.info("updated payload :  %s", optional_payload)
            resp1 = self.csm_obj.create_iam_user_rgw(optional_payload)
            self.log.info("Verify Response : %s", resp1)
            assert_utils.assert_true(resp1.status_code == HTTPStatus.CREATED,
                                     "IAM user creation failed")
            uid = resp1.json()['tenant'] + "$" + payload["uid"]
            self.created_iam_users.add(uid)
            self.log.info("Step 2: Create bucket under above IAM user")
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          self.bucket, self.akey, self.skey)
            bucket_created = s3_misc.create_bucket(self.bucket, self.akey, self.skey)
            assert bucket_created, "Failed to create bucket"
            test_cfg = self.csm_conf["test_40636"]
            max_size = test_cfg["max_size"]
            max_objects = test_cfg["max_objects"]
            self.log.info("Step 3: Perform PUT API to set user level quota with max values")
            payload = self.csm_obj.iam_user_quota_payload()
            result, resp = self.csm_obj.verify_get_set_user_quota(uid, payload,
                                                               verify_response=True)
            assert result, "Verification for get set user failed."
            self.log.info("Response : %s", resp)
            self.log.info("Step 4: Perform put object of max size")
            self.csm_obj.verify_max_size(max_size)
            self.log.info("Step 5: Delete object")
            assert s3_misc.delete_object(
                self.bucket, self.obj_name, self.akey, self.skey), "Failed to delete bucket."
            self.log.info("Step 6: Perform put objects of small size")
            self.csm_obj.verify_max_objects(max_size, max_objects)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
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
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 2: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 3: Perform s3 operation")
        random_size = self.cryptogen.randrange(1, max_size)
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                          self.akey, self.skey, object_size=random_size)
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 3: Perform PUT API to set user level quota less than used")
        less_size = self.cryptogen.randrange(1, max_size)
        resp3 = self.csm_obj.set_user_quota(self.user_id, "user", "true", less_size, max_objects)
        assert_utils.assert_true(resp3[0], resp3[1])
        self.log.info("Step 4: Perform GET API to get user level quota")
        resp4 = self.csm_obj.get_user_quota(self.user_id, "user")  #Expected Result not known yet
        assert_utils.assert_true(resp4[0], resp4[1])
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
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        self.log.info("Step 2: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 3: Start Multipart upload S3 operations of X Mb"
                      "X=(max_size+x)")
        res = self.create_bucket_to_upload_parts(
            self.bucket,
            self.obj_name,
            (max_size+test_cfg["extra_bytes"]),
            test_cfg["total_parts"])
        mpu_id, parts = res
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            self.bucket,
            self.obj_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  test_cfg["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            self.bucket,
            self.obj_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(self.bucket)
        assert_utils.assert_in(self.obj_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info("Step 3: Perform PUT API to set user level quota less then used")
        resp3 = self.csm_obj.set_user_quota(self.user_id, "user", "true", max_size, max_objects)
        assert_utils.assert_false(resp3[0], resp3[1])
        self.log.info("Step 4: Perform GET API to get user level quota")
        resp4 = self.csm_obj.get_user_quota(self.user_id, "user")
        assert_utils.assert_true(resp4[0], resp4[1])
        self.log.info("Step 5: Abort Multipart upload S3 operations")
        res = self.s3_mp_test_obj.abort_multipart_upload(
            self.bucket,
            self.obj_name,
            mpu_id)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_mp_test_obj.list_multipart_uploads(
            self.bucket)
        assert_utils.assert_not_in(mpu_id, res[1], res[1])
        self.log.info(
            "Aborted multipart upload with upload ID: %s", mpu_id)
        self.log.info("Step 6: Perform PUT API to set user level quota "
                      "less than used")
        resp3 = self.csm_obj.set_user_quota(self.user_id, "user", "true", max_size, max_objects)
        assert_utils.assert_true(resp3[0], resp3[1])
        self.log.info("Step 7: Perform GET API to get user level quota")
        resp4 = self.csm_obj.get_user_quota(self.user_id, "user")
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
        test_cfg = self.csm_conf["test_40639"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        self.log.info("Step 2: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 2: Start Multipart upload S3 operations of X Mb")
        res = self.create_bucket_to_upload_parts(
            self.bucket,
            self.obj_name,
            max_size,
            test_cfg["total_parts"])
        mpu_id, parts = res
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            self.bucket,
            self.obj_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  test_cfg["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            self.bucket,
            self.obj_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(self.bucket)
        assert_utils.assert_in(self.obj_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info("Step 3: Perform GET API to get user level quota")
        resp = self.csm_obj.get_user_quota(self.user_id, "user")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Perform PUT API to set user level quota less than used")
        less_size = self.cryptogen.randrange(1, max_size)
        resp = self.csm_obj.set_user_quota(self.user_id, "user", "true", less_size, max_objects)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Perform GET API to get user level quota")
        resp = self.csm_obj.get_user_quota(self.user_id, "user")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            self.bucket,
            self.obj_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(self.bucket)
        assert_utils.assert_in(self.obj_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info("Step 7: Perform PUT API to set user level quota less than used")
        resp = self.csm_obj.set_user_quota(self.user_id, "user", "true",
                                             less_size, max_objects)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8: Perform GET API to get user level quota")
        resp = self.csm_obj.get_user_quota(self.user_id, "user")
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
        test_cfg = self.csm_conf["test_40639"]
        max_size = test_cfg["max_size"]
        max_objects = test_cfg["max_objects"]
        self.log.info("Step 2: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.bucket, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.bucket, self.akey, self.skey)
        assert bucket_created, "Failed to create bucket"
        self.log.info("Step 2: Perform PUT API to set user level quota of less size")
        less_size = self.cryptogen.randrange(1, max_size)
        resp = self.csm_obj.set_user_quota(self.user_id, "user", "true", less_size, max_objects)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Perform GET API to get user level quota")
        resp = self.csm_obj.get_user_quota(self.user_id, "user")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Start Multipart upload S3 operations of X Mb")
        res = self.create_bucket_to_upload_parts(
            self.bucket,
            self.obj_name,
            max_size,
            test_cfg["total_parts"])
        mpu_id, parts = res
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            self.bucket,
            self.obj_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  test_cfg["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            self.bucket,
            self.obj_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(self.bucket)
        assert_utils.assert_in(self.obj_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info("Step 5: Perform put object of max size")
        self.csm_obj.verify_max_size(max_size)
        self.log.info("Step 6: Abort Multipart upload S3 operations")
        res = self.s3_mp_test_obj.abort_multipart_upload(
            self.bucket,
            self.obj_name,
            mpu_id)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_mp_test_obj.list_multipart_uploads(
            self.bucket)
        assert_utils.assert_not_in(mpu_id, res[1], res[1])
        self.log.info(
            "Aborted multipart upload with upload ID: %s", mpu_id)
        self.log.info("Step 7: Perform put object of max size")
        self.csm_obj.verify_max_size(max_size)
        self.log.info("Step 8: Perform put objects of small size")
        self.csm_obj.verify_max_objects(max_size, max_objects)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
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
        max_size = test_cfg["max_size"]
        random_size = self.cryptogen.randrange(1, max_size)
        num_objects = math.floor(max_size/random_size)
        self.log.info("Step 1: Create N objects of Random size totals to S bytes")
        for _ in range(0, num_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size)
            assert resp, "Put object Failed"
        self.log.info("Step 2: Perform GET API to get capacity usage stats using - Admin")
        resp = self.csm_obj.get_capacity_usage(self.user_id)
        assert resp.status_code == HTTPStatus.OK, \
            "Status code check failed for get capacity"
        self.log.info("Step 3: Verify above count matches aws response")
        status, output = run_local_cmd(commands.CMD_AWSCLI_READABLE.format(self.bucket), 
                                    chk_stderr=True)
        assert status, "list objects operation failed"
        # Verify the above count matches AWS response
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
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
        max_size = test_cfg["max_size"]
        random_size = self.cryptogen.randrange(1, max_size)
        num_objects = math.floor(max_size / random_size)
        self.log.info("Step 1: Create N objects of Random size totals to S bytes")
        for _ in range(0, num_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size)
            assert resp, "Put object Failed"
        self.log.info("Step 2: Perform GET API to get capacity usage stats using - manage")
        resp = self.csm_obj.get_capacity_usage(self.user_id)
        assert resp.status_code == HTTPStatus.OK, \
            "Status code check failed for get capacity"
        self.log.info("Step 3: Verify above count matches aws response")
        status, output = run_local_cmd(commands.CMD_AWSCLI_READABLE.format(self.bucket), 
                          chk_stderr=True)
        assert status, "list objects operation failed"
        # Verify the above count matches AWS response
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
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
        max_size = test_cfg["max_size"]
        random_size = self.cryptogen.randrange(1, max_size)
        num_objects = math.floor(max_size / random_size)
        self.log.info("Step 1: Create N objects of Random size totals to S bytes")
        for _ in range(0, num_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size)
            assert resp, "Put object Failed"
        self.log.info("Step 2: Perform GET API to get capacity usage stats using - monitor")
        resp = self.csm_obj.get_capacity_usage(self.user_id)
        assert resp.status_code == HTTPStatus.OK, \
            "Status code check failed for get capacity"
        self.log.info("Step 3: Verify above count matches aws response")
        status, output = run_local_cmd(commands.CMD_AWSCLI_READABLE.format(self.bucket), 
                         chk_stderr=True)
        assert status, "list objects operation failed"
        # Verify the above count matches AWS response
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
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
        self.log.info("Pre-condition: Create multiple objects (N) on 1 bucket")
        test_cfg = self.csm_conf["test_41757"]
        max_size = test_cfg["max_size"]
        random_size = self.cryptogen.randrange(1, max_size)
        num_objects = math.floor(max_size / random_size)
        for _ in range(0, num_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size)
            assert resp, "Put object Failed"
        self.log.info("Step 1: Delete iam user")
        self.log.info("Verify Delete IAM user: %s with access key: %s and secret key: %s",
                      self.user_id, self.akey, self.skey)
        purge_data = False
        response = self.csm_obj.delete_iam_user_rgw(self.user_id, purge_data)
        assert response.status_code == HTTPStatus.OK, \
                           "Status code check failed for user deletion"
        self.log.info("Step 2: Perform GET API to get capacity usage stats")
        resp = self.csm_obj.get_capacity_usage(self.user_id)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
                           "Status code check failed for user deletion"
        #TODO: Error code and message check part
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
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
        self.log.info("Pre-condition: Create multiple objects (N) on 1 bucket")
        test_cfg = self.csm_conf["test_41127_3"]
        max_size = test_cfg["max_size"]
        random_size = self.cryptogen.randrange(1, max_size)
        num_objects = math.floor(max_size / random_size)
        for _ in range(0, num_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size)
            assert resp, "Put object Failed"
        self.log.info("Step 1: Delete iam user")
        self.log.info("Verify Delete IAM user: %s with access key: %s and secret key: %s",
                      self.user_id, self.akey, self.skey)
        purge_data = True
        response = self.csm_obj.delete_iam_user_rgw(self.user_id, purge_data)
        assert response.status_code == HTTPStatus.OK, \
            "Status code check failed for user deletion"
        self.log.info("Step 2: Perform GET API to get capacity usage stats")
        resp = self.csm_obj.get_capacity_usage(self.user_id)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status code check failed for user deletion"
        # TODO: Error code and message check part
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41128')
    def test_41128(self):
        """
        Test GET capacity stats for delete IAM , Purge True user using admin users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_40634"]
        max_size = test_cfg["max_size"]
        self.log.info("Step 2: Perform PUT API to set user level quota")
        payload = self.csm_obj.iam_user_quota_payload()
        result, resp = self.csm_obj.verify_get_set_user_quota(self.user_id, payload,
                                                              verify_response=True)
        assert result, "Verification for get set user failed."
        self.log.info("Response : %s", resp)
        self.log.info("Step 3: Perform max size verification")
        res = self.csm_obj.verify_max_size(max_size, self.akey, self.skey)
        assert res[0], res[1]
        self.log.info("Step 4: Perform GET API to get capacity usage stats using - monitor")
        resp = self.csm_obj.get_capacity_usage(self.user_id)
        assert resp.status_code == HTTPStatus.OK, \
            "Status code check failed for get capacity"
        self.log.info("Step 5: Verify above count matches aws response")
        status, output = run_local_cmd(commands.CMD_AWSCLI_READABLE.format(self.bucket), 
                         chk_stderr=True)
        assert status, "list objects operation failed"
        # Verify the above count matches AWS response
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip("Feature not ready")
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-41151')
    def test_41151(self):
        """
        Test GET capacity stats for create IAM user and Put objects using manage users
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_41151"]
        max_size = test_cfg["max_size"]
        random_size = self.cryptogen.randrange(1, max_size)
        num_objects = math.floor(max_size / random_size)
        self.log.info("Step 1: Create N objects of Random size totals to S bytes")
        for _ in range(0, num_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              self.akey, self.skey, object_size=random_size)
            assert resp, "Put object Failed"
        self.log.info("Step 2: Perform GET API to get capacity usage "
                      "with empty key Parameters id and resource")
        uid = ""
        resource = ""
        resp = self.csm_obj.get_capacity_usage(resource, uid)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status code check failed for get capacity"
        # TODO: Error code and message check part
        self.log.info("Step 3: Perform GET API to get capacity usage "
                      "with invalid key Parameters id and resource")
        resource = uid = self.user_id
        resp = self.csm_obj.get_capacity_usage(resource, uid)
        assert resp.status_code == HTTPStatus.BAD_REQUEST, \
            "Status code check failed for get capacity"
        # TODO: Error code and message check part
        self.log.info("##### Test ended -  %s #####", test_case_name)
