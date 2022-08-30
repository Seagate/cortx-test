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

"""S3 copy object quota test module."""

import logging
import os
from http import HTTPStatus
from time import perf_counter_ns

import pytest
from commons import configmanager
from commons import error_messages as errmsg
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import path_exists, make_dirs
from config.s3 import S3_CFG
from libs.csm.csm_interface import csm_api_factory
from libs.csm.csm_setup import CSMConfigsCheck
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3 import s3_misc

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class TestCopyObjectsQuota:
    """S3 copy object class."""
    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-statements
    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-locals
    # pylint: disable=attribute-defined-outside-init
    @classmethod
    def setup_class(cls):
        """
        Setup_class will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Class setup.")
        cls.csm_obj = csm_api_factory("rest")
        cls.ha_obj = HAK8s()
        cls.config = CSMConfigsCheck()
        cls.log.info("Initiating Rest Client ...")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_capacity.yaml")
        cls.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")
        cls.created_iam_users = set()
        cls.buckets_created = []
        setup_ready = cls.config.check_predefined_csm_user_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_users()
        assert_utils.assert_true(setup_ready, setup_ready)
        resp = cls.ha_obj.get_config_value(cls.csm_obj.master)
        if resp[0]:
            cls.nvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['data'])
        cls.aligned_size = 4 * cls.nvalue
        cls.test_file = f"mp_obj-{}".format(perf_counter_ns())
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "test_copy_object")
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)
        if not path_exists(cls.test_dir_path):
            make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.log.info("ENDED: Class setup.")

    def setup_method(self):
        """
        Setup_method will be invoked before running each test case.

        It will perform all prerequisite steps required for test execution.
        It will create a bucket and upload an object to that bucket.
        """
        self.log.info("STARTED: Test setup.")
        self.log.info("Step 1: Create a user (user1)")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.CREATED,
                                   "IAM user creation failed")
        self.user_id = resp.json()["keys"][0]['user']
        self.created_iam_users.add(self.user_id)
        resp1 = self.csm_obj.compare_iam_payload_response(resp, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp1[0], resp1[1])
        self.akey = resp.json()["keys"][0]["access_key"]
        self.skey = resp.json()["keys"][0]["secret_key"]
        self.src_bkt = "src1"
        self.obj = "obj"
        self.dest_bkt1 = "dest1"
        self.log.info("Step 2: Create bucket under above IAM user")
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      self.src_bkt, self.akey, self.skey)
        bucket_created = s3_misc.create_bucket(self.src_bkt, self.akey, self.skey)
        assert_utils.assert_true(bucket_created, "Failed to create bucket")
        self.buckets_created.append([self.src_bkt, self.akey, self.skey])
        self.log.info("ENDED: Test setup.")

    def teardown_method(self):
        """
        Teardown will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Test teardown.")
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
        self.log.info("ENDED: Test teardown.")

    def create_iam_user(self):
        """
        It will create IAM user.
        :return: access key, secrete key and user_id.
        """
        self.log.info("Creating S3 account and IAM user")
        payload = self.csm_obj.iam_user_payload_rgw("random")
        resp = self.csm_obj.create_iam_user_rgw(payload)
        self.log.info("Verify Response : %s", resp)
        assert_utils.assert_equals(resp.status_code, HTTPStatus.CREATED,
                                   "IAM user creation failed")
        user_id = resp.json()["keys"][0]['user']
        self.created_iam_users.add(user_id)
        resp1 = self.csm_obj.compare_iam_payload_response(resp, payload)
        self.log.info("Printing response %s", resp1)
        assert_utils.assert_true(resp1[0], resp1[1])
        akey = resp.json()["keys"][0]["access_key"]
        skey = resp.json()["keys"][0]["secret_key"]
        return akey, skey, user_id




    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags('TEST-46133')
    def test_46133(self):
        """
        Test copy-object operation within same bucket and across different buckets for simple
        object when max-object limit is set in user level quota
        """
        self.log.info("STARTED:Test copy-object operation within same bucket and across different"
                      "buckets for simple object when max-object limit is set in user level quota")
        test_cfg = self.csm_conf["test_40632"]
        config_dict = {"enabled": True, "max_size": test_cfg["max_size"],
                       "max_objects": test_cfg["max_objects"]}
        self.log.info("Step 3: Perform PUT API to set user level quota fields i.e."
                      "enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N ")
        self.csm_obj.set_get_user_quota(config_dict, self.user_id)
        self.log.info("Step 4:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 5: Upload a simple object obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = s3_misc.create_put_objects("obj1", self.src_bkt, self.akey, self.skey,
                                          object_size=random_size, block_size="1K")
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 6: Perform Copy object operation within same bucket 'N-1' times using"
                      "same source bucket and object and just changing the key name of the "
                      "destination object .")
        for cnt in range(2, (test_cfg["max_objects"]+1)):
            dest_obj = "obj" + str(cnt)
            resp = s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1",
                                       self.src_bkt, dest_obj)
            assert_utils.assert_true(resp, f"Copy object Failed for {self.src_bkt}/{dest_obj}")
        self.log.info("Step 7: Perform Copy object operation again (N)th time within same bucket"
                      " using same source bucket and object and just changing the key name of the"
                      " destination object .")
        try:
            dest_obj = "obj" + str(test_cfg["max_objects"]+1)
            s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1", self.src_bkt, dest_obj)
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 8:Perform Get API to get user and bucket stats and validate the object"
                      "count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 9: Create one more user (user2)")
        akey, skey, uid = self.create_iam_user()
        self.log.info("Step 10: Create 2 buckets named 'src1' and 'dest1' under the user created"
                      " in step 9.")
        bucket_created = s3_misc.create_bucket(self.src_bkt, akey, skey)
        assert_utils.assert_true(bucket_created, "Failed to create bucket")
        self.buckets_created.append([self.src_bkt, akey, skey])
        bucket_created = s3_misc.create_bucket(self.dest_bkt1, akey, skey)
        assert_utils.assert_true(bucket_created, "Failed to create bucket")
        self.buckets_created.append([self.dest_bkt1, akey, skey])
        self.log.info("Step 11: Perform PUT API to set user level quota fields"
                      " i.e. enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N .")
        self.csm_obj.set_get_user_quota(config_dict, uid)
        self.log.info("Step 12:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(akey, skey, uid)
        self.log.info("Step 13: Upload a simple object obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = s3_misc.create_put_objects("obj1", self.src_bkt, akey, skey,
                                          object_size=random_size, block_size="1K")
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 14: Perform Copy object operation within same bucket 'N-1' times using"
                      "same source bucket and object and just changing the key name of the "
                      "destination object .")
        for obj_cnt in range(1, (test_cfg["max_objects"])):
            dest_obj = "obj" + str(obj_cnt)
            resp = s3_misc.copy_object(akey, skey, self.src_bkt, "obj1", self.dest_bkt1, dest_obj)
            assert_utils.assert_true(resp, f"Copy object Failed for {self.dest_bkt1}/{dest_obj}")
        self.log.info("Step 15: Perform Copy object operation again (N)th time within same bucket"
                      " using same source bucket and object and just changing the key name of the"
                      " destination object .")
        try:
            dest_obj = "obj" + str(test_cfg["max_objects"])
            s3_misc.copy_object(akey, skey, self.src_bkt, "obj1", self.dest_bkt1, dest_obj)
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 16:Perform Get API to get user and bucket stats and validate the"
                      "object count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(akey, skey, uid)
        self.log.info("ENDED:Test copy-object operation within same bucket and across different"
                      " buckets for simple object when max-object limit is set in user level quota")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags('TEST-46134')
    def test_46134(self):
        """
        Test copy-object operation across different buckets(multi-hop) for simple object when
        max-object limit is set in user level quota
        """
        self.log.info("STARTED:Test copy-object operation across different buckets(multi-hop) for"
                      " simple object when max-object limit is set in user level quota")
        test_cfg = self.csm_conf["test_40632"]
        config_dict = {"enabled": True, "max_size": test_cfg["max_size"],
                       "max_objects": test_cfg["max_objects"]}
        self.log.info("Step 2: Perform PUT API to set user level quota fields i.e."
                      "enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N ")
        self.csm_obj.set_get_user_quota(config_dict, self.user_id)
        self.log.info("Step 3:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 4: Create 'N+1' buckets named 'src1' , 'dest1' .. 'destN' under the"
                      "user created in step 1")
        for cnt in range(1, test_cfg["max_objects"]+2):
            bkt_name = "dest" + str(cnt)
            bucket_created = s3_misc.create_bucket(bkt_name, self.akey, self.skey)
            assert_utils.assert_true(bucket_created, "Failed to create bucket")
            self.buckets_created.append([bkt_name, self.akey, self.skey])
        self.log.info("Step 5: Upload a simple object obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = s3_misc.create_put_objects("obj1", self.src_bkt, self.akey, self.skey,
                                          object_size=random_size, block_size="1K")
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 6:  Perform Copy object operation from bucket 'src1' --> 'dest1'"
                      " --> 'dest2' --> ... --> 'destN-1' bucket and keeping the key name of"
                      " the destination object same during every copy operation.")
        for cnt in range(1, (test_cfg["max_objects"])):
            dest_bkt = "dest" + str(cnt)
            resp = s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1",
                                       dest_bkt, "obj1")
            assert_utils.assert_true(resp, f"Copy object Failed for {dest_bkt}/obj1")
            self.src_bkt = dest_bkt
        self.log.info("Step 7: Perform Copy object operation again (N)th time from 'destN-1'"
                      " to 'destN' bucket and keeping the key name of the destination object"
                      "same during every copy operation.")
        try:
            dest_bkt = "dest" + str(test_cfg["max_objects"])
            s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1", dest_bkt, "obj1")
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 8:Perform Get API to get user and bucket stats and validate the object"
                      "count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 9: Create one more user (user2)")
        akey, skey, uid = self.create_iam_user()
        self.log.info("Step 10: Perform PUT API to set user level quota fields"
                      " i.e. enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N .")
        self.csm_obj.set_get_user_quota(config_dict, uid)
        self.log.info("Step 11:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(akey, skey, uid)
        self.log.info("Step 12:  Create 'N+1' buckets named 'src1' , 'dest1' .. 'destN' under"
                      "the user created in step 9.")
        bucket_created = s3_misc.create_bucket(self.src_bkt, akey, skey)
        assert_utils.assert_true(bucket_created, "Failed to create bucket")
        self.buckets_created.append([self.src_bkt, akey, skey])
        for cnt in range(1, test_cfg["max_objects"]+1):
            bkt_name = "dest" + str(cnt)
            bucket_created = s3_misc.create_bucket(bkt_name, akey, skey)
            assert_utils.assert_true(bucket_created, "Failed to create bucket")
            self.buckets_created.append([bkt_name, self.akey, self.skey])
        self.log.info("Step 13: Upload a simple object obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = s3_misc.create_put_objects("obj1", self.src_bkt, akey, skey,
                                          object_size=random_size, block_size="1K")
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 14:  Perform Copy object operation from bucket 'src1' --> 'dest1'"
                      " --> 'dest2' --> ... --> 'destN-1' bucket and using different key name for"
                      " the destination object during every copy operation.")
        src_bkt = self.src_bkt
        src_obj = "obj1"
        for cnt in range(1, (test_cfg["max_objects"])):
            dest_bkt = "dest" + str(cnt)
            dest_obj = "obj" + str(cnt+1)
            resp = s3_misc.copy_object(akey, skey, src_bkt, src_obj,
                                       dest_bkt, dest_obj)
            assert_utils.assert_true(resp, f"Copy object Failed for {dest_bkt}/{dest_obj}")
            src_bkt = dest_bkt
            src_obj = dest_obj
        self.log.info("Step 15: Perform Copy object operation again (N)th time from 'destN-1'"
                      "Perform Copy object operation again (N)th time from 'destN-1' bucket"
                      " to 'destN' bucket and using different key name of the destination object"
                      "same during every copy operation.")
        try:
            dest_bkt = "dest" + str(test_cfg["max_objects"])
            dest_obj = "obj" + str(test_cfg["max_objects"]+1)
            s3_misc.copy_object(akey, skey, src_bkt, src_obj, dest_bkt, dest_obj)
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 16:Perform Get API to get user and bucket stats and validate the object"
                      "count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(akey, skey, uid)
        self.log.info("ENDED:Test copy-object operation across different buckets(multi-hop) for"
                      " simple object when max-object limit is set in user level quota")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags('TEST-46135')
    def test_46135(self):
        """
        Test copy-object overwrite operation for simple object when max-object limit is set in user
        level quota
        """
        self.log.info("STARTED:Test copy-object overwrite operation for simple object when"
                      " max-object limit is set in user level quota")
        test_cfg = self.csm_conf["test_40632"]
        config_dict = {"enabled": True, "max_size": test_cfg["max_size"],
                       "max_objects": test_cfg["max_objects"]}
        self.log.info("Create 2 buckets named 'src1' and 'dest1' under the user created"
                      " in step 9.")
        bucket_created = s3_misc.create_bucket(self.dest_bkt1, self.akey, self.skey)
        assert_utils.assert_true(bucket_created, "Failed to create bucket")
        self.buckets_created.append([self.dest_bkt1, self.akey, self.skey])
        self.log.info("Step 3: Perform PUT API to set user level quota fields i.e."
                      "enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N ")
        self.csm_obj.set_get_user_quota(config_dict, self.user_id)
        self.log.info("Step 4:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 5: Upload a simple object obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = s3_misc.create_put_objects("obj1", self.src_bkt, self.akey, self.skey,
                                          object_size=random_size, block_size="1K")
        assert_utils.assert_true(resp, "Put object Failed")
        self.log.info("Step 6: Perform Copy object operation within same bucket 'N-1' times using"
                      "same source bucket and object and just changing the key name of the "
                      "destination object .")
        for cnt in range(1, (test_cfg["max_objects"])):
            dest_obj = "obj" + str(cnt)
            resp = s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1",
                                       self.dest_bkt1, dest_obj)
            assert_utils.assert_true(resp, f"Copy object Failed for {self.dest_bkt1}/{dest_obj}")
        self.log.info("Step 7: Perform Copy object operation again (N)th time from 'src1' bucket"
                      " to 'dest1' bucket using same source bucket and object and same/existing"
                      " key name of the destination object(overwrite scenario)")
        try:
            dest_obj = "obj" + str(test_cfg["max_objects"]-1)
            s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1",
                                self.dest_bkt1, dest_obj)
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 8:Perform Get API to get user and bucket stats and validate the object"
                      "count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("ENDED:Test copy-object overwrite operation for simple object when"
                      " max-object limit is set in user level quota")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags('TEST-46136')
    def test_46136(self):
        """
        Test copy-object operation within same bucket and across different buckets for multipart
        object when max-object limit is set in user level quota
        """
        self.log.info("STARTED:Test copy-object operation within same bucket and across different"
                      " buckets for multipart object when max-object limit is set in user level"
                      " quota")
        test_cfg = self.csm_conf["test_40632"]
        config_dict = {"enabled": True, "max_size": test_cfg["max_size"],
                       "max_objects": test_cfg["max_objects"]}
        self.log.info("Step 3: Perform PUT API to set user level quota fields i.e."
                      "enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N ")
        self.csm_obj.set_get_user_quota(config_dict, self.user_id)
        self.log.info("Step 4:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 5: Upload multipart upload obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = self.multipart_upload(self.src_bkt, "obj1", self.akey, self.skey, random_size)
        assert_utils.assert_true(resp, "multipart upload Failed")
        self.log.info("Step 6: Perform Copy object operation within same bucket 'N-1' times using"
                      "same source bucket and object and just changing the key name of the "
                      "destination object .")
        for cnt in range(2, (test_cfg["max_objects"]+1)):
            dest_obj = "obj" + str(cnt)
            resp = s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1",
                                       self.src_bkt, dest_obj)
            assert_utils.assert_true(resp, f"Copy object Failed for {self.src_bkt}/{dest_obj}")
        self.log.info("Step 7: Perform Copy object operation again (N)th time within same bucket"
                      " using same source bucket and object and just changing the key name of the"
                      " destination object .")
        try:
            dest_obj = "obj" + str(test_cfg["max_objects"]+1)
            s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1", self.src_bkt, dest_obj)
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 8:Perform Get API to get user and bucket stats and validate the object"
                      "count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 9: Create one more user (user2)")
        akey, skey, uid = self.create_iam_user()
        self.log.info("Step 10: Create 2 buckets named 'src1' and 'dest1' under the user created"
                      " in step 9.")
        bucket_created = s3_misc.create_bucket(self.src_bkt, akey, skey)
        assert_utils.assert_true(bucket_created, "Failed to create bucket")
        self.buckets_created.append([self.src_bkt, akey, skey])
        bucket_created = s3_misc.create_bucket(self.dest_bkt1, akey, skey)
        assert_utils.assert_true(bucket_created, "Failed to create bucket")
        self.buckets_created.append([self.dest_bkt1, akey, skey])
        self.log.info("Step 11: Perform PUT API to set user level quota fields"
                      " i.e. enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N .")
        self.csm_obj.set_get_user_quota(config_dict, uid)
        self.log.info("Step 12:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(akey, skey, uid)
        self.log.info("Step 13: Upload multipart object obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = self.multipart_upload(self.src_bkt, "obj1", self.akey, self.skey, random_size)
        assert_utils.assert_true(resp, "Multipart upload Failed")
        self.log.info("Step 14: Perform Copy object operation within same bucket 'N-1' times using"
                      "same source bucket and object and just changing the key name of the "
                      "destination object .")
        for obj_cnt in range(1, (test_cfg["max_objects"])):
            dest_obj = "obj" + str(obj_cnt)
            resp = s3_misc.copy_object(akey, skey, self.src_bkt, "obj1", self.dest_bkt1, dest_obj)
            assert_utils.assert_true(resp, f"Copy object Failed for {self.dest_bkt1}/{dest_obj}")
        self.log.info("Step 15:Perform Copy object operation again (N)th time from 'src1' bucket"
                      " to 'dest1' bucket using same source bucket and object and by just changing"
                      " the key name of the destination object ")
        try:
            dest_obj = "obj" + str(test_cfg["max_objects"])
            s3_misc.copy_object(akey, skey, self.src_bkt, "obj1", self.dest_bkt1, dest_obj)
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 16:Perform Get API to get user and bucket stats and validate the object"
                      "count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(akey, skey, uid)
        self.log.info("ENDED:Test copy-object operation within same bucket and across different"
                      " buckets for multipart object when max-object limit is set in user level"
                      " quota")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags('TEST-46137')
    def test_46137(self):
        """
        Test copy-object operation across different buckets(multi-hop) for multipart object when
        max-object limit is set in user level quota
        """
        self.log.info("STARTED:Test copy-object operation across different buckets(multi-hop) for"
                      " multipart object when max-object limit is set in user level quota")
        test_cfg = self.csm_conf["test_40632"]
        config_dict = {"enabled": True, "max_size": test_cfg["max_size"],
                       "max_objects": test_cfg["max_objects"]}
        self.log.info("Step 2: Perform PUT API to set user level quota fields i.e."
                      "enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N ")
        self.csm_obj.set_get_user_quota(config_dict, self.user_id)
        self.log.info("Step 3:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 4: Create 'N+1' buckets named 'src1' , 'dest1' .. 'destN' under the"
                      "user created in step 1")
        for cnt in range(1, test_cfg["max_objects"]+2):
            bkt_name = "dest" + str(cnt)
            bucket_created = s3_misc.create_bucket(bkt_name, self.akey, self.skey)
            assert_utils.assert_true(bucket_created, "Failed to create bucket")
            self.buckets_created.append([bkt_name, self.akey, self.skey])
        self.log.info("Step 5: Upload a multipart object obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = self.multipart_upload(self.src_bkt, "obj1", self.akey, self.skey, random_size)
        assert_utils.assert_true(resp, "Multipart upload Failed")
        self.log.info("Step 6:Perform Copy object operation from bucket 'src1' --> 'dest1'"
                      " --> 'dest2' --> ... --> 'destN-1' bucket and keeping the key name"
                      " of the destination object same during every copy operation.")
        for cnt in range(1, (test_cfg["max_objects"])):
            dest_bkt = "dest" + str(cnt)
            resp = s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1",
                                       dest_bkt, "obj1")
            assert_utils.assert_true(resp, f"Copy object Failed for {dest_bkt}/obj1")
            self.src_bkt = dest_bkt
        self.log.info("Step 7: Perform Copy object operation again (N)th time from 'destN-1'"
                      "to 'destN' bucket and keeping the key name of the destination object"
                      "same during every copy operation.")
        try:
            dest_bkt = "dest" + str(test_cfg["max_objects"])
            s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1", dest_bkt, "obj1")
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 8:Perform Get API to get user and bucket stats and validate the object"
                      "count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 9: Create one more user (user2)")
        akey, skey, uid = self.create_iam_user()
        self.log.info("Step 10: Perform PUT API to set user level quota fields"
                      " i.e. enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N .")
        self.csm_obj.set_get_user_quota(config_dict, uid)
        self.log.info("Step 11:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(akey, skey, uid)
        self.log.info("Step 12:  Create 'N+1' buckets named 'src1' , 'dest1' .. 'destN' under"
                      "the user created in step 9.")
        bucket_created = s3_misc.create_bucket(self.src_bkt, akey, skey)
        assert_utils.assert_true(bucket_created, "Failed to create bucket")
        self.buckets_created.append([self.src_bkt, akey, skey])
        for cnt in range(1, test_cfg["max_objects"]+1):
            bkt_name = "dest" + str(cnt)
            bucket_created = s3_misc.create_bucket(bkt_name, akey, skey)
            assert_utils.assert_true(bucket_created, "Failed to create bucket")
            self.buckets_created.append([bkt_name, self.akey, self.skey])
        self.log.info("Step 13: Upload a multipart object obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = self.multipart_upload(self.src_bkt, "obj1", akey, skey, random_size)
        assert_utils.assert_true(resp, "Multipart upload Failed")
        self.log.info("Step 14:  Perform Copy object operation from bucket 'src1' --> 'dest1'"
                      " --> 'dest2' --> ... --> 'destN-1' bucket and using different key name for"
                      " the destination object during every copy operation.")
        src_bkt = self.src_bkt
        src_obj = "obj1"
        for cnt in range(1, (test_cfg["max_objects"])):
            dest_bkt = "dest" + str(cnt)
            dest_obj = "obj" + str(cnt+1)
            resp = s3_misc.copy_object(akey, skey, src_bkt, src_obj,
                                       dest_bkt, dest_obj)
            assert_utils.assert_true(resp, f"Copy object Failed for {dest_bkt}/{dest_obj}")
            src_bkt = dest_bkt
            src_obj = dest_obj
        self.log.info("Step 15:  Perform Copy object operation again (N)th time from 'destN-1'"
                      " bucket to 'destN' bucket and using different key name for the destination"
                      " object during every copy operation.")
        try:
            dest_bkt = "dest" + str(test_cfg["max_objects"])
            dest_obj = "obj" + str(test_cfg["max_objects"]+1)
            s3_misc.copy_object(akey, skey, src_bkt, src_obj, dest_bkt, dest_obj)
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 16:Perform Get API to get user and bucket stats and validate the object"
                      "count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(akey, skey, uid)
        self.log.info("ENDED:Test copy-object operation across different buckets(multi-hop) for"
                      " multipart object when max-object limit is set in user level quota")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags('TEST-46138')
    def test_46138(self):
        """
        Test copy-object overwrite operation for multipart object when max-object limit is set
        in user level quota
        """
        self.log.info("STARTED:Test copy-object overwrite operation for multipart object when"
                      " max-object limit is set in user level quota")
        test_cfg = self.csm_conf["test_40632"]
        config_dict = {"enabled": True, "max_size": test_cfg["max_size"],
                       "max_objects": test_cfg["max_objects"]}
        self.log.info("Create 2 buckets named 'src1' and 'dest1' under the user created"
                      " in step 9.")
        bucket_created = s3_misc.create_bucket(self.dest_bkt1, self.akey, self.skey)
        assert_utils.assert_true(bucket_created, "Failed to create bucket")
        self.buckets_created.append([self.dest_bkt1, self.akey, self.skey])
        self.log.info("Step 3: Perform PUT API to set user level quota fields i.e."
                      "enabled(bool)=true, max_size(integer value)= -1 ,"
                      " max_objects(integer value) = N ")
        self.csm_obj.set_get_user_quota(config_dict, self.user_id)
        self.log.info("Step 4:Perform GET API to get user level quota fields and verify the"
                      " user level quota fields as per above PUT request.")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("Step 5: Upload a multipart object obj1 of some random size S in src1")
        random_size = self.csm_obj.random_gen.randrange(1, test_cfg["max_size"])
        resp = self.multipart_upload(self.src_bkt, "obj1", self.akey, self.skey, random_size)
        assert_utils.assert_true(resp, "Multipart upload Failed")
        self.log.info("Step 6: Perform Copy object operation within same bucket 'N-1' times using"
                      "same source bucket and object and just changing the key name of the "
                      "destination object .")
        for cnt in range(1, (test_cfg["max_objects"])):
            dest_obj = "obj" + str(cnt)
            resp = s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1",
                                       self.dest_bkt1, dest_obj)
            assert_utils.assert_true(resp, f"Copy object Failed for {self.dest_bkt1}/{dest_obj}")
        self.log.info("Step 7: Perform Copy object operation again (N)th time from 'src1' bucket"
                      " to 'dest1' bucket using same source bucket and object and same/existing"
                      " key name of the destination object(overwrite scenario) .")
        try:
            dest_obj = "obj" + str(test_cfg["max_objects"]-1)
            s3_misc.copy_object(self.akey, self.skey, self.src_bkt, "obj1",
                                self.dest_bkt1, dest_obj)
        except CTException as error:
            self.log.info("Expected exception received %s", error)
            assert_utils.assert_in(errmsg.S3_COPY_OBJECT_QUOTA_ERR, error.message, error)
        self.log.info("Step 8:Perform Get API to get user and bucket stats and validate the object"
                      "count and space utilization for user/bucket .")
        self.log.debug("Perform & Verify GET API to get capacity usage stats")
        self.csm_obj.verify_user_quota(self.akey, self.skey, self.user_id)
        self.log.info("ENDED:Test copy-object overwrite operation for multipart object when"
                      " max-object limit is set in user level quota")
