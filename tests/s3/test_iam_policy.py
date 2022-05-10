# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""IAM Policy Test Module."""

import copy
import json
import logging
import os
import time

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from commons.utils.assert_utils import assert_in, assert_false
from config.s3 import IAM_POLICY_CFG
from libs.s3 import s3_test_lib, iam_test_lib, iam_policy_test_lib
from libs.s3.s3_acl_test_lib import S3AclTestLib
from libs.s3.s3_bucket_policy_test_lib import S3BucketPolicyTestLib
from libs.s3.s3_common_test_lib import create_bucket_put_object
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib


# pylint: disable-msg=too-many-public-methods
class TestIAMPolicy:
    """IAM Policy Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to test suit once.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup test suite")
        cls.s3_test_lib = s3_test_lib.S3TestLib()
        cls.iam_test_lib = iam_test_lib.IamTestLib()
        cls.iam_policy_test_lib = iam_policy_test_lib.IamPolicyTestLib()
        cls.bucket_policy_test_lib = S3BucketPolicyTestLib()
        cls.s3_mp_test_obj = S3MultipartTestLib()
        cls.test_file = f"file_object_{time.perf_counter_ns()}.txt"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestIAMPolicy")
        cls.test_file_path = os.path.join(cls.test_dir_path, cls.test_file)
        cls.buckets = []
        if not os.path.exists(cls.test_dir_path):
            os.makedirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.log.info("ENDED: Setup test suite")

    def teardown_class(self):
        """
        Function will be invoked after test suit once.
        """
        self.log.info("STARTED: Teardown test suite")
        if not os.path.exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        self.log.info("ENDED: Teardown test suite")

    def setup_method(self):
        """
        Function will be invoked before each test case execution.

        It will perform prerequisite test steps if any.
        Define few variable, will be used while executing test and for cleanup.
        """
        self.buckets = []

    def teardown_method(self):
        """
        Function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        Also removing local file created during execution.
        """
        for bucket in self.buckets:
            self.s3_test_lib.delete_bucket(bucket_name=bucket, force=True)

    def create_iam_policy(self, actions, bucket, policy_name, permission="Allow"):
        """
        Create IAM Policy wrapper
        """
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": permission,
                    "Action": actions,
                    "Resource": [f"arn:aws:s3:::{bucket}/*", f"arn:aws:s3:::{bucket}"]
                }
            ]
        }
        self.log.info("Creating IAM Policy %s = %s", policy_name, policy_document)
        _, policy = self.iam_policy_test_lib.create_policy(
            policy_name=policy_name,
            policy_document=json.dumps(policy_document))
        return policy.arn

    def attach_list_iam_policy(self, policy_arn, iam_user):
        """
        Attach IAM Policy, LIst IAM Policy and make sure it is attached
        """
        self.log.info("Attach Policy1 %s to %s user", policy_arn, iam_user)
        self.iam_policy_test_lib.attach_user_policy(iam_user, policy_arn)

        self.log.info("List Attached User Policies on %s", iam_user)
        resp = self.iam_policy_test_lib.check_policy_in_attached_policies(iam_user, policy_arn)
        assert resp

    def put_bucket_acl(self, access: str, secret: str, bucket: str, exception: str = None):
        """
        Put bucket ACL with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        operation = "Put Bucket ACL:"
        acl_obj = S3AclTestLib(access_key=access, secret_key=secret)
        try:
            acl_obj.put_bucket_acl(bucket, acl="public-read-write")
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    def get_bucket_acl(self, access, secret, bucket, exception):
        """
        Get bucket ACL with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        operation = "Get Bucket ACL:"
        acl_obj = S3AclTestLib(access_key=access, secret_key=secret)
        try:
            acl_obj.get_bucket_acl(bucket)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    # pylint: disable-msg=too-many-arguments
    def put_object_acl(self, access, secret, bucket, object_name, exception):
        """
        Put object ACL with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :object_name: Object Name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        operation = "Put Object ACL:"
        acl_obj = S3AclTestLib(access_key=access, secret_key=secret)
        try:
            acl_obj.put_object_canned_acl(bucket, object_name, acl="public-read-write")
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    # pylint: disable-msg=too-many-arguments
    def get_object_acl(self, access, secret, bucket, object_name, exception):
        """
        Get object ACL with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :object_name: Object Name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        operation = "Get Object ACL:"
        acl_obj = S3AclTestLib(access_key=access, secret_key=secret)
        try:
            acl_obj.get_object_acl(bucket, object_name)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    def list_bucket(self, access, secret, bucket, exception):
        """
        List bucket with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        s3_tl = s3_test_lib.S3TestLib(access_key=access, secret_key=secret)
        operation = "List Bucket:"
        try:
            s3_tl.object_list(bucket)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    def delete_bucket(self, access, secret, bucket, exception):
        """
        Delete bucket with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        s3_tl = s3_test_lib.S3TestLib(access_key=access, secret_key=secret)
        operation = "Delete Bucket:"
        try:
            s3_tl.delete_bucket(bucket)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    # pylint: disable-msg=too-many-arguments
    def create_multipart(self, access, secret, bucket, object_name, exception):
        """
        Create Multipart with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :object_name: Object name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        s3_mp_test_obj = S3MultipartTestLib(access_key=access, secret_key=secret)
        operation = "Create Multipart: "
        try:
            res = s3_mp_test_obj.create_multipart_upload(bucket, object_name)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert exception in str(error.message), error.message
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
            return "None"
        else:
            assert not exception, f"{operation}Expected {exception}. Did not receive any exception."
            return res[1]["UploadId"]

    def list_multipart(self, access, secret, bucket, exception):
        """
        List multipart with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        s3_mp_test_obj = S3MultipartTestLib(access_key=access, secret_key=secret)
        operation = "List Multipart:"
        try:
            s3_mp_test_obj.list_multipart_uploads(bucket)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    # pylint: disable-msg=too-many-arguments
    def abort_multipart(self, access, secret, bucket, object_name, upload_id, exception):
        """
        Abort multipart with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :object_name: Object name
        :upload_id: Upload ID
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        s3_mp_test_obj = S3MultipartTestLib(access_key=access, secret_key=secret)
        operation = "Abort Multipart:"
        try:
            s3_mp_test_obj.abort_multipart_upload(bucket, object_name, upload_id)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    # pylint: disable-msg=too-many-arguments
    def put_object(self, access, secret, bucket, object_name, exception):
        """
        Put object with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :object_name: Object name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        s3_test_lib_obj = s3_test_lib.S3TestLib(access_key=access, secret_key=secret)
        operation = "Put Object:"
        system_utils.create_file(self.test_file, 0)
        try:
            s3_test_lib_obj.put_object(bucket, object_name, self.test_file)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    # pylint: disable-msg=too-many-arguments
    def get_object(self, access, secret, bucket, object_name, exception):
        """
        Get object with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :object_name: Object name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        s3_test_lib_obj = s3_test_lib.S3TestLib(access_key=access, secret_key=secret)
        operation = "Get Object:"
        try:
            s3_test_lib_obj.get_object(bucket, object_name)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    # pylint: disable-msg=too-many-arguments
    def delete_object(self, access, secret, bucket, object_name, exception):
        """
        Delete object with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :object_name: Object name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        s3_test_lib_obj = s3_test_lib.S3TestLib(access_key=access, secret_key=secret)
        operation = "Delete Object:"
        try:
            s3_test_lib_obj.delete_object(bucket, object_name)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    # pylint: disable-msg=too-many-arguments
    def put_bucket_policy(self, access, secret, bucket, policy, exception):
        """
        Put bucket policy with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :policy: Bucket policy
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        bucket_policy_test_lib = S3BucketPolicyTestLib(access_key=access, secret_key=secret)
        operation = "Put Bucket Policy:"
        try:
            bucket_policy_test_lib.put_bucket_policy(bucket, policy)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    def get_bucket_policy(self, access, secret, bucket, exception):
        """
        Get bucket policy with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        bucket_policy_test_lib = S3BucketPolicyTestLib(access_key=access, secret_key=secret)
        operation = "Get Bucket Policy:"
        try:
            bucket_policy_test_lib.get_bucket_policy(bucket)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    def delete_bucket_policy(self, access, secret, bucket, exception):
        """
        Delete bucket policy with exception wrapper

        :access: Access Key
        :secret: Secret Key
        :bucket: Bucket name
        :object_name: Object name
        :exception: Exception string e.g. AccessDenied, None meaning no exception expected
        """
        bucket_policy_test_lib = S3BucketPolicyTestLib(access_key=access, secret_key=secret)
        operation = "Delete Bucket Policy:"
        try:
            bucket_policy_test_lib.delete_bucket_policy(bucket)
        except CTException as error:
            self.log.info("%s Expected %s, got %s, %s", operation, exception, error.message,
                          error.message)
            if exception:
                assert_in(exception, str(error.message), error.message)
            else:
                self.log.error("%s Expected no Exception. Instead caught %s.", operation,
                               error.message)
                raise error
        else:
            assert_false(exception, f"{operation} Expected {exception}. "
                                    f"Did not receive any exception.")

    # pylint: disable-msg=too-many-locals
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags("TEST-33900")
    @CTFailOn(error_handler)
    def test_33900(self):
        """Verify S3:ACL Actions in IAM Policy"""
        bucket = f"bucket-{time.time()}-test-33900"
        object_name = f"obj-{time.time()}-test-33900"
        object_size = 0
        actions = ["s3:GetBucketAcl", "s3:PutBucketAcl", "s3:PutObjectAcl", "s3:GetObjectAcl"]

        self.log.info("Create %s & Create %s in %s", bucket, object_name, bucket)
        create_bucket_put_object(self.s3_test_lib, bucket, object_name, self.test_file_path,
                                 object_size)
        self.buckets.append(bucket)
        for permission in ["Deny", "Allow"]:
            iam_user = f"iam-{permission}-{time.time()}"
            self.log.info("Create IAM account %s", iam_user)
            _, resp = self.iam_test_lib.create_user(iam_user)
            user_arn = resp["User"]["Arn"]
            _, resp = self.iam_test_lib.create_access_key(iam_user)
            access = resp["AccessKey"]["AccessKeyId"]
            secret = resp["AccessKey"]["SecretAccessKey"]

            self.log.info("Create IAM Policy")
            policy_arn = self.create_iam_policy(actions, bucket,
                                                f"policy-{permission.lower()}-{int(time.time())}",
                                                permission)

            self.log.info("Attach IAM Policies & Verify it is attached")
            self.attach_list_iam_policy(policy_arn, iam_user)

            if permission == "Allow":
                # Put Bucket Policy using S3 account which gives access to iam user
                bucket_policy = copy.deepcopy(IAM_POLICY_CFG["test_33900"]["bucket_policy"])
                for statement in bucket_policy["Statement"]:
                    statement["Principal"]["AWS"] = user_arn
                    statement["Resource"] = statement["Resource"].format(bucket)
                self.log.info("Bucket Policy %s", bucket_policy)
                self.bucket_policy_test_lib.put_bucket_policy(bucket_name=bucket,
                                                              bucket_policy=json.dumps(
                                                                  bucket_policy))
                exception = None
            else:
                exception = "AccessDenied"

            self.put_bucket_acl(access, secret, bucket, exception)
            self.get_bucket_acl(access, secret, bucket, exception)
            self.put_object_acl(access, secret, bucket, object_name, exception)
            self.get_object_acl(access, secret, bucket, object_name, exception)

            # Cleanup
            if permission == "Allow":
                self.bucket_policy_test_lib.delete_bucket_policy(bucket)
            self.log.info("Detach policy from IAM user")
            self.iam_policy_test_lib.detach_user_policy(iam_user, policy_arn)
            self.log.info("Delete policy")
            self.iam_policy_test_lib.delete_policy(policy_arn)
            self.log.info("Delete Access Key")
            self.iam_test_lib.delete_access_key(iam_user, access)
            self.log.info("Delete IAM account")
            self.iam_test_lib.delete_user(iam_user)

    @pytest.mark.s3_iam_policy
    @pytest.mark.tags("TEST-33901")
    @CTFailOn(error_handler)
    def test_33901(self):
        """Verify S3:Bucket Actions in IAM Policy"""
        bucket = f"bucket-{time.time()}-test-33901"
        actions = ["s3:ListBucket", "s3:DeleteBucket"]

        self.log.info("Create bucket %s", bucket)
        self.s3_test_lib.create_bucket(bucket)
        self.buckets.append(bucket)
        for permission in ["Deny", "Allow"]:
            iam_user = f"iam-{permission}-{time.time()}"
            self.log.info("Create IAM account %s", iam_user)
            _, resp = self.iam_test_lib.create_user(iam_user)
            user_arn = resp["User"]["Arn"]
            _, resp = self.iam_test_lib.create_access_key(iam_user)
            access = resp["AccessKey"]["AccessKeyId"]
            secret = resp["AccessKey"]["SecretAccessKey"]

            self.log.info("Create IAM Policy")
            policy_arn = self.create_iam_policy(actions, bucket,
                                                f"policy-{permission.lower()}-{int(time.time())}",
                                                permission)

            self.log.info("Attach IAM Policies")
            self.attach_list_iam_policy(policy_arn, iam_user)

            if permission == "Allow":
                # Put Bucket Policy using S3 account which gives access to iam user
                bucket_policy = copy.deepcopy(IAM_POLICY_CFG["test_3390_"]["bucket_policy"])
                for statement in bucket_policy["Statement"]:
                    statement["Principal"]["AWS"] = user_arn
                    statement["Resource"] = statement["Resource"].format(bucket)
                    statement["Action"] = actions
                self.log.info(bucket_policy)
                self.bucket_policy_test_lib.put_bucket_policy(bucket_name=bucket,
                                                              bucket_policy=json.dumps(
                                                                  bucket_policy))
                exception = None
            else:
                exception = "AccessDenied"

            self.list_bucket(access, secret, bucket, exception)
            self.delete_bucket(access, secret, bucket, exception)

            # Cleanup
            if permission == "Allow":
                self.bucket_policy_test_lib.delete_bucket_policy(bucket)
            self.log.info("Detach policy from IAM user")
            self.iam_policy_test_lib.detach_user_policy(iam_user, policy_arn)
            self.log.info("Delete policy")
            self.iam_policy_test_lib.delete_policy(policy_arn)
            self.log.info("Delete Access Key")
            self.iam_test_lib.delete_access_key(iam_user, access)
            self.log.info("Delete IAM account")
            self.iam_test_lib.delete_user(iam_user)

    # pylint: disable=too-many-locals,too-many-statements
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags("TEST-33902")
    @CTFailOn(error_handler)
    def test_33902(self):
        """Verify S3:Multipart Actions in IAM Policy"""
        bucket = f"bucket-{time.time()}-test-33902"
        object_name1 = f"obj-{time.time()}-test-33902-1"
        object_name2 = f"obj-{time.time()}-test-33902-2"
        actions = ["s3:PutObject", "s3:ListBucketMultipartUploads", "s3:AbortMultipartUpload"]

        self.log.info("Create bucket %s", bucket)
        self.s3_test_lib.create_bucket(bucket)
        self.buckets.append(bucket)
        for permission in ["Deny", "Allow"]:
            mpu_id1 = []
            if permission == "Deny":
                # Create Multipart using s3 account
                res = self.s3_mp_test_obj.create_multipart_upload(bucket, object_name1)
                mpu_id1 = res[1]["UploadId"]

            iam_user = f"iam-{permission}-{time.time()}"
            self.log.info("Create IAM account %s", iam_user)
            _, resp = self.iam_test_lib.create_user(iam_user)
            user_arn = resp["User"]["Arn"]
            _, resp = self.iam_test_lib.create_access_key(iam_user)
            access = resp["AccessKey"]["AccessKeyId"]
            secret = resp["AccessKey"]["SecretAccessKey"]

            self.log.info("Create IAM Policy")
            policy_arn = self.create_iam_policy(actions, bucket,
                                                f"policy-{permission.lower()}-{int(time.time())}",
                                                permission)

            self.log.info("Attach IAM Policies")
            self.attach_list_iam_policy(policy_arn, iam_user)

            if permission == "Allow":
                # Put Bucket Policy using S3 account which gives access to iam user
                bucket_policy = copy.deepcopy(IAM_POLICY_CFG["test_33902"]["bucket_policy"])
                for statement in bucket_policy["Statement"]:
                    statement["Principal"]["AWS"] = user_arn
                    statement["Resource"] = statement["Resource"].format(bucket)
                self.log.info(bucket_policy)
                self.bucket_policy_test_lib.put_bucket_policy(bucket_name=bucket,
                                                              bucket_policy=json.dumps(
                                                                  bucket_policy))
                exception = None
            else:
                exception = "AccessDenied"

            self.log.info("Execute actions")
            mpu_id2 = self.create_multipart(access, secret, bucket, object_name2, exception)
            self.list_multipart(access, secret, bucket, exception)
            if permission == "Allow":
                self.abort_multipart(access, secret, bucket, object_name2, mpu_id2, exception)
            else:
                self.abort_multipart(access, secret, bucket, object_name1, mpu_id1, exception)

            # Cleanup
            if permission == "Allow":
                self.bucket_policy_test_lib.delete_bucket_policy(bucket)
            if permission == "Deny":
                # Delete the multipart for object1
                self.s3_mp_test_obj.abort_multipart_upload(bucket, object_name1, mpu_id1)

            self.log.info("Detach policy from IAM user")
            self.iam_policy_test_lib.detach_user_policy(iam_user, policy_arn)
            self.log.info("Delete policy")
            self.iam_policy_test_lib.delete_policy(policy_arn)
            self.log.info("Delete Access Key")
            self.iam_test_lib.delete_access_key(iam_user, access)
            self.log.info("Delete IAM account")
            self.iam_test_lib.delete_user(iam_user)

    @pytest.mark.s3_iam_policy
    @pytest.mark.tags("TEST-33903")
    @CTFailOn(error_handler)
    def test_33903(self):
        """Verify S3:Object Actions in IAM Policy"""
        bucket = f"bucket-{time.time()}-test-33903"
        object_name = f"obj-{time.time()}-test-33903"
        actions = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]

        self.log.info("Create bucket %s", bucket)
        self.s3_test_lib.create_bucket(bucket)
        self.buckets.append(bucket)
        for permission in ["Deny", "Allow"]:
            iam_user = f"iam-{permission}-{time.time()}"
            self.log.info("Create IAM account %s", iam_user)
            _, resp = self.iam_test_lib.create_user(iam_user)
            user_arn = resp["User"]["Arn"]
            _, resp = self.iam_test_lib.create_access_key(iam_user)
            access = resp["AccessKey"]["AccessKeyId"]
            secret = resp["AccessKey"]["SecretAccessKey"]

            self.log.info("Create IAM Policy")
            policy_arn = self.create_iam_policy(actions, bucket,
                                                f"policy-{permission.lower()}-{int(time.time())}",
                                                permission)

            self.log.info("Attach IAM Policies")
            self.attach_list_iam_policy(policy_arn, iam_user)

            if permission == "Allow":
                # Put Bucket Policy using S3 account which gives access to iam user
                bucket_policy = copy.deepcopy(IAM_POLICY_CFG["test_33903"]["bucket_policy"])
                for statement in bucket_policy["Statement"]:
                    statement["Principal"]["AWS"] = user_arn
                    statement["Resource"] = statement["Resource"].format(bucket)
                    statement["Action"] = actions
                self.log.info(bucket_policy)
                self.bucket_policy_test_lib.put_bucket_policy(bucket_name=bucket,
                                                              bucket_policy=json.dumps(
                                                                  bucket_policy))
                exception = None
            else:
                exception = "AccessDenied"

            self.log.info("Execute actions")

            self.put_object(access, secret, bucket, object_name, exception)
            self.get_object(access, secret, bucket, object_name, exception)
            self.delete_object(access, secret, bucket, object_name, exception)

            # Cleanup
            self.log.info("Detach policy from IAM user")
            self.iam_policy_test_lib.detach_user_policy(iam_user, policy_arn)
            self.log.info("Delete policy")
            self.iam_policy_test_lib.delete_policy(policy_arn)
            self.log.info("Delete Access Key")
            self.iam_test_lib.delete_access_key(iam_user, access)
            self.log.info("Delete IAM account")
            self.iam_test_lib.delete_user(iam_user)

    @pytest.mark.s3_iam_policy
    @pytest.mark.tags("TEST-33904")
    @CTFailOn(error_handler)
    def test_33904(self):
        """Verify S3:BucketPolicy Actions in IAM Policy"""
        bucket = f"bucket-{time.time()}-test-33904"
        actions = ["s3:PutBucketPolicy", "s3:GetBucketPolicy", "s3:DeleteBucketPolicy"]

        self.log.info("Create bucket %s", bucket)
        self.s3_test_lib.create_bucket(bucket)
        self.buckets.append(bucket)
        for permission in ["Deny", "Allow"]:
            iam_user = f"iam-{permission}-{time.time()}"
            self.log.info("Create IAM account %s", iam_user)
            _, resp = self.iam_test_lib.create_user(iam_user)
            user_arn = resp["User"]["Arn"]
            _, resp = self.iam_test_lib.create_access_key(iam_user)
            access = resp["AccessKey"]["AccessKeyId"]
            secret = resp["AccessKey"]["SecretAccessKey"]

            self.log.info("Create IAM Policy")
            policy_arn = self.create_iam_policy(actions, bucket,
                                                f"policy-{permission.lower()}-{int(time.time())}",
                                                permission)

            self.log.info("Attach IAM Policies")
            self.attach_list_iam_policy(policy_arn, iam_user)

            self.log.info("Create bucket policy")
            bucket_policy = copy.deepcopy(IAM_POLICY_CFG["test_3390_"]["bucket_policy"])
            for statement in bucket_policy["Statement"]:
                statement["Principal"]["AWS"] = user_arn
                statement["Resource"] = statement["Resource"].format(bucket)
                statement["Action"] = actions
            self.log.info(bucket_policy)
            if permission == "Allow":
                # Put Bucket Policy using S3 account which gives access to iam user
                self.bucket_policy_test_lib.put_bucket_policy(bucket_name=bucket,
                                                              bucket_policy=json.dumps(
                                                                  bucket_policy))
                exception = None
            else:
                exception = "AccessDenied"

            self.log.info("Execute actions")

            self.put_bucket_policy(access, secret, bucket, json.dumps(bucket_policy), exception)
            self.get_bucket_policy(access, secret, bucket, exception)
            self.delete_bucket_policy(access, secret, bucket, exception)

            # Cleanup
            self.log.info("Detach policy from IAM user")
            self.iam_policy_test_lib.detach_user_policy(iam_user, policy_arn)
            self.log.info("Delete policy")
            self.iam_policy_test_lib.delete_policy(policy_arn)
            self.log.info("Delete Access Key")
            self.iam_test_lib.delete_access_key(iam_user, access)
            self.log.info("Delete IAM account")
            self.iam_test_lib.delete_user(iam_user)
