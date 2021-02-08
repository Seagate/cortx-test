# -*- coding: utf-8 -*-
#!/usr/bin/python
"""Bukcet Workflow Operations Test Module."""
import random
import os
import time
import logging
import pytest
from libs.s3 import s3_test_lib, iam_test_lib, s3_acl_test_lib
from commons.utils.system_utils import create_file, remove_file
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons import const
from commons.utils.config_utils import read_yaml

LOGGER = logging.getLogger(__name__)

s3test_obj = s3_test_lib.S3TestLib()
iam_obj = iam_test_lib.IamTestLib()
acl_obj = s3_acl_test_lib.S3AclTestLib()

bkt_ops_conf = read_yaml(
    "config/s3/test_bucket_workflow_operations.yaml")
cmn_conf = read_yaml("config/common_config.yaml")


class BucketWorkflowOperations():
    """Bucket Workflow Operations Test suite."""

    def setup_method(self):
        """
        Function will be invoked before each test case execution.

        It will perform prerequisite test steps if any
        """
        LOGGER.info("STARTED: Setup operations")
        self.random_id = str(time.time())
        self.ldap_user = const.S3_BUILD_VER[cmn_conf["BUILD_VER_TYPE"]
                                            ]["ldap_creds"]["ldap_username"]
        self.ldap_pwd = const.S3_BUILD_VER[cmn_conf["BUILD_VER_TYPE"]
                                           ]["ldap_creds"]["ldap_passwd"]
        LOGGER.info("ENDED: Setup operations")

    def tearDown_method(self):
        """
        Function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        LOGGER.info("STARTED: Teardown operations")
        bucket_list = s3test_obj.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                bkt_ops_conf["bucket_workflow"]["bkt_name_prefix"])]
        for bktname in pref_list:
            acl_obj.put_bucket_acl(
                bktname, acl=bkt_ops_conf["bucket_workflow"]["bkt_permission"])
        s3test_obj.delete_multiple_buckets(pref_list)
        if os.path.exists(bkt_ops_conf["bucket_workflow"]["file_path"]):
            remove_file(
                bkt_ops_conf["bucket_workflow"]["file_path"])
        LOGGER.info("Deleting IAM accounts")
        self.account_name = bkt_ops_conf["bucket_workflow"]["acc_name_prefix"]
        acc_list = iam_obj.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        LOGGER.info(acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        LOGGER.info(all_acc)
        for acc_name in all_acc:
            iam_obj.reset_access_key_and_delete_account_s3iamcli(acc_name)
        LOGGER.info("Deleted IAM accounts successfully")
        LOGGER.info("ENDED: Teardown operations")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5463", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_1975(self):
        """Bucket names must start with a lowercase letter or number."""
        LOGGER.info(
            "STARTED: Bucket names must start with a lowercase letter or number")
        LOGGER.info(
            "Creating a bucket with lowercase letter is %s",
            bkt_ops_conf["test_8535"]["bucket_name_1"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8535"]["bucket_name_1"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8535"]["bucket_name_1"], resp[1]
        LOGGER.info(
            "Bucket is created with lowercase letter : %s",
            bkt_ops_conf["test_8535"]["bucket_name_1"])
        LOGGER.info(
            "Creating a bucket name which starts with number %s",
            bkt_ops_conf["test_8535"]["bucket_name_2"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8535"]["bucket_name_2"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8535"]["bucket_name_2"], resp[1]
        LOGGER.info(
            "Bucket is created with number : %s",
            bkt_ops_conf["test_8535"]["bucket_name_2"])
        LOGGER.info("Cleanup activity")
        resp = s3test_obj.delete_bucket(
            bkt_ops_conf["test_8535"]["bucket_name_2"], force=True)
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED: Bucket names must start with a lowercase letter or number")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5469", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_1976(self):
        """Bucket name can contain only lower-case characters, numbers, periods and dashes."""
        LOGGER.info(
            "STARTED: Bucket name can contain only lower-case chars, numbers, periods and dashes")
        LOGGER.info(
            "Creating a bucket with lower case, number, periods, dashes")
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8536"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8536"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            bkt_ops_conf["test_8536"]["bucket_name"])
        LOGGER.info(
            "ENDED: Bucket name can contain only lower-case characters, "
            "numbers, periods and dashes")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5467", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_1977(self):
        """Bucket names must be at least 3 and no more than 63 characters long."""
        LOGGER.info(
            "STARTED: Bucket names must be at least 3 and no more than 63 characters long")
        LOGGER.info(
            "Creating a bucket with at least 3 characters is : %s",
            bkt_ops_conf["test_8537"]["bucket_name_1"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8537"]["bucket_name_1"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8537"]["bucket_name_1"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            bkt_ops_conf["test_8537"]["bucket_name_1"])
        LOGGER.info(
            "Creating a bucket with name  63 chars long is : %s",
            bkt_ops_conf["test_8537"]["bucket_name_2"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8537"]["bucket_name_2"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8537"]["bucket_name_2"], resp[1]
        LOGGER.info(
            "Created a bucket with name 63 characters long is : %s",
            bkt_ops_conf["test_8537"]["bucket_name_2"])
        LOGGER.info("Cleanup activity")
        resp = s3test_obj.delete_bucket(
            bkt_ops_conf["test_8537"]["bucket_name_1"], force=True)
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED: Bucket names must be at least 3 and no more than 63 characters long")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5468", "bucket_workflow_operations")
    def test_1978(self):
        """Bucket name with less than 3 characters and more than 63 characters."""
        LOGGER.info(
            "STARTED: Bucket name with less than 3 characters and more than 63 characters")
        LOGGER.info(
            "Creating buckets with name less than 3 and more than 63 character length")
        for each_bucket in bkt_ops_conf["test_8538"]["bucket_list"]:
            try:
                s3test_obj.create_bucket(each_bucket)
            except CTException as error:
                LOGGER.error(error.message)
                assert bkt_ops_conf["test_8538"]["error_message"] in error.message, error.message
        LOGGER.info(
            "Creating buckets with name less than 3 and more than 63 characters length is failed")
        LOGGER.info(
            "ENDED: Bucket name with less than 3 characters and more than 63 characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5464", "bucket_workflow_operations")
    def test_1979(self):
        """Bucket names must not contain uppercase characters."""
        LOGGER.info(
            "STARTED: Bucket names must not contain uppercase characters")
        LOGGER.info(
            "Creating a bucket with name : %s",
            bkt_ops_conf["test_8539"]["bucket_name"])
        try:
            s3test_obj.create_bucket(bkt_ops_conf["test_8539"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_ops_conf["test_8539"]["error_message"] in error.message, error.message
        LOGGER.info("Creating a bucket with uppercase letters is failed")
        LOGGER.info(
            "ENDED: Bucket names must not contain uppercase characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5465", "bucket_workflow_operations")
    def test_1980(self):
        """Bucket names must not contain underscores."""
        LOGGER.info("STARTED: Bucket names must not contain underscores")
        LOGGER.info(
            "Creating a bucket with underscore is : %s",
            bkt_ops_conf["test_8540"]["bucket_name"])
        try:
            s3test_obj.create_bucket(bkt_ops_conf["test_8540"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_ops_conf["test_8540"]["error_message"] in error.message, error.message
        LOGGER.info("Creating a bucket with underscore is failed")
        LOGGER.info("ENDED: Bucket names must not contain underscores")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5462", "bucket_workflow_operations")
    def test_1981(self):
        """Bucket names with special characters."""
        LOGGER.info("STARTED: Bucket names with special characters")
        count_limit = random.choice(
            range(
                bkt_ops_conf["test_8541"]["start_range"],
                bkt_ops_conf["test_8541"]["end_range"]))
        special_chars_list = bkt_ops_conf["test_8541"]["special_chars_list"]
        special_chars = "".join(
            random.choices(
                special_chars_list,
                k=bkt_ops_conf["test_8541"]["special_char_len"]))
        chars_name = "".join(
            random.choices(
                bkt_ops_conf["test_8541"]["bucket_name"],
                k=count_limit))
        bucket_name = "{0}{1}".format(chars_name, special_chars)
        LOGGER.info(
            "Creating a bucket with special chars is : %s", bucket_name)
        try:
            s3test_obj.create_bucket(bucket_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_ops_conf["test_8541"]["error_message"] in error.message, error.message
        LOGGER.info("Creating a bucket with special characters is failed")
        LOGGER.info("ENDED: Bucket names with special characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5466", "bucket_workflow_operations")
    def test_1982(self):
        """Bucket names must not be formatted as an IP address (for example, 192.168.5.4)."""
        LOGGER.info(
            "STARTED: Bucket names must not be formatted as an IP address(for eg., 192.168.5.4)")
        LOGGER.info("Creating a bucket with name : %s",
                    bkt_ops_conf["test_8542"]["bucket_name"])
        try:
            s3test_obj.create_bucket(bkt_ops_conf["test_8542"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_ops_conf["test_8542"]["error_message"] in error.message, error.message
        LOGGER.info("Creating a bucket with an IP address format is failed")
        LOGGER.info(
            "ENDED: Bucket names must not be formatted as an IP address (for example, 192.168.5.4)")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5459", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2039(self):
        """Create single bucket."""
        LOGGER.info("STARTED: Create single bucket")
        LOGGER.info(
            "Creating single Bucket with name %s",
            bkt_ops_conf["test_8638"]["bucket_name"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8638"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8638"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            bkt_ops_conf["test_8638"]["bucket_name"])
        LOGGER.info("Verifying that bucket is created")
        resp = s3test_obj.bucket_list()
        assert resp[0], resp[1]
        assert bkt_ops_conf["test_8638"]["bucket_name"] in resp[1]
        LOGGER.info("Verified that bucket is created")
        LOGGER.info("ENDED: Creating single Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5460", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2040(self):
        """Create multiple buckets."""
        LOGGER.info("STARTED: Create multiple buckets")
        LOGGER.info("Creating multiple buckets")
        bucket_list = []
        for each in range(bkt_ops_conf["test_8639"]["range"]):
            bucket_name = "{0}{1}".format(
                bkt_ops_conf["test_8639"]["bucket_str"], each)
            resp = s3test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        LOGGER.info("Created multiple buckets")
        LOGGER.info("Verifying that buckets are created")
        resp = s3test_obj.bucket_list()
        for each_bucket in bucket_list:
            assert each_bucket in resp[1], resp[1]
        LOGGER.info("Verified that buckets are created")
        LOGGER.info("ENDED: Create multiple buckets")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5461", "bucket_workflow_operations")
    def test_2043(self):
        """Create bucket with same bucket name already present."""
        LOGGER.info(
            "STARTED: Create bucket with same bucket name already present")
        LOGGER.info("Creating a bucket with name %s",
                    bkt_ops_conf["test_8642"]["bucket_name"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8642"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8642"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            bkt_ops_conf["test_8642"]["bucket_name"])
        LOGGER.info("Creating a bucket with existing bucket name")
        try:
            s3test_obj.create_bucket(bkt_ops_conf["test_8642"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_ops_conf["test_8642"]["error_message"] in error.message, error.message
        LOGGER.info("Creating a bucket with existing bucket name is failed")
        LOGGER.info(
            "ENDED: Create bucket with same bucket name already present")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5447", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2044(self):
        """Verification of max. no. of buckets user can create."""
        LOGGER.info(
            "STARTED: Verification of max. no. of buckets user can create")
        LOGGER.info("Creating 100 max buckets")
        for each in range(bkt_ops_conf["test_8643"]["bucket_count"]):
            bucket_name = "{0}{1}".format(
                bkt_ops_conf["test_8643"]["bucket_name"], each)
            resp = s3test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
        LOGGER.info("Created 100 buckets")
        LOGGER.info("Verifying that bucket is created")
        resp = s3test_obj.bucket_count()
        assert resp[0], resp[1]
        LOGGER.info("Verified that buckets are created")
        LOGGER.info(
            "ENDED: Verification of max. no. of buckets user can create")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5457", "bucket_workflow_operations")
    def test_2045(self):
        """Delete bucket which has objects."""
        LOGGER.info("STARTED: Delete bucket which has objects")
        LOGGER.info(
            "Creating a Bucket with name %s",
            bkt_ops_conf["test_8644"]["bucket_name"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8644"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8644"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            bkt_ops_conf["test_8644"]["bucket_name"])
        create_file(
            bkt_ops_conf["bucket_workflow"]["file_path"],
            bkt_ops_conf["bucket_workflow"]["file_size"])
        LOGGER.info("Uploading an objects to a bucket")
        for i in range(bkt_ops_conf["test_8644"]["object_count"]):
            objname = "{0}{1}".format(
                bkt_ops_conf["test_8644"]["object_str"], i)
            resp = s3test_obj.object_upload(
                bkt_ops_conf["test_8644"]["bucket_name"],
                objname,
                bkt_ops_conf["bucket_workflow"]["file_path"])
            assert resp[0], resp[1]
        LOGGER.info("Objects are uploaded to a bucket")
        LOGGER.info("Deleting a bucket having objects")
        try:
            s3test_obj.delete_bucket(bkt_ops_conf["test_8644"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_ops_conf["test_8644"]["error_message"] in error.message, error.message
        LOGGER.info("ENDED: Delete bucket which has objects")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5458", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2046(self):
        """Delete bucket forcefully which has objects."""
        LOGGER.info("STARTED: Delete bucket forcefully which has objects")
        LOGGER.info(
            "Creating a bucket with name %s",
            bkt_ops_conf["test_8645"]["bucket_name"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8645"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8645"]["bucket_name"], resp[1]
        create_file(
            bkt_ops_conf["bucket_workflow"]["file_path"],
            bkt_ops_conf["bucket_workflow"]["file_size"])
        LOGGER.info("Uploading multiple objects to a bucket")
        for obj_cnt in range(bkt_ops_conf["test_8645"]["range"]):
            objname = "{0}{1}".format(
                bkt_ops_conf["test_8645"]["bucket_name"], str(obj_cnt))
            resp = s3test_obj.object_upload(
                bkt_ops_conf["test_8645"]["bucket_name"],
                objname,
                bkt_ops_conf["bucket_workflow"]["file_path"])
            assert resp[0], resp[1]
        LOGGER.info("Multiple objects are uploaded to a bucket")
        LOGGER.info("Forcefully deleting bucket having object")
        resp = s3test_obj.delete_bucket(
            bkt_ops_conf["test_8645"]["bucket_name"], force=True)
        assert resp[0], resp[1]
        LOGGER.info("Forcefully deleted a bucket")
        LOGGER.info("ENDED: Delete bucket forcefully which has objects")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5455", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2047(self):
        """Delete empty bucket."""
        LOGGER.info("STARTED: Delete empty bucket")
        LOGGER.info(
            "Creating a bucket with name %s",
            bkt_ops_conf["test_8646"]["bucket_name"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8646"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8646"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            bkt_ops_conf["test_8646"]["bucket_name"])
        LOGGER.info("Deleting a bucket")
        retv = s3test_obj.delete_bucket(
            bkt_ops_conf["test_8646"]["bucket_name"])
        assert retv[0], retv[1]
        LOGGER.info("Bucket is deleted")
        LOGGER.info("ENDED: Delete empty bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5454", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2048(self):
        """Delete multiple empty buckets."""
        LOGGER.info("STARTED: Delete multiple empty buckets")
        LOGGER.info("Creating multiple buckets")
        bucket_list = []
        for count in range(bkt_ops_conf["test_8647"]["bucket_count"]):
            bucket_name = "{0}{1}".format(
                bkt_ops_conf["test_8647"]["bucket_name"], str(count))
            resp = s3test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        LOGGER.info("Multiple buckets are created")
        LOGGER.info("Deleting multiple buckets")
        resp = s3test_obj.delete_multiple_buckets(bucket_list)
        assert resp[0], resp[1]
        LOGGER.info("Multiple buckets are deleted")
        LOGGER.info("ENDED: Delete multiple empty buckets")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5456", "bucket_workflow_operations")
    def test_2049(self):
        """Delete bucket when Bucket does not exists."""
        LOGGER.info("STARTED: Delete bucket when Bucket does not exists")
        LOGGER.info(
            "Deleting bucket which does not exists on s3 server")
        try:
            s3test_obj.delete_bucket(bkt_ops_conf["test_8648"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_ops_conf["test_8648"]["error_message"] in error.message, error.message
        LOGGER.info(
            "Deleting bucket which does not exists on s3 server is failed")
        LOGGER.info(
            "ENDED: Delete bucket which does not exists on s3 server")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5452", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2050(self):
        """List all objects in a bucket."""
        LOGGER.info("STARTED: List all objects in a bucket")
        LOGGER.info(
            "Creating a bucket with name %s",
            bkt_ops_conf["test_8649"]["bucket_name"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8649"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8649"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            bkt_ops_conf["test_8649"]["bucket_name"])
        create_file(
            bkt_ops_conf["bucket_workflow"]["file_path"],
            bkt_ops_conf["bucket_workflow"]["file_size"])
        LOGGER.info("Uploading multiple objects to a bucket")
        object_list = []
        for count in range(bkt_ops_conf["test_8649"]["object_count"]):
            objname = "{0}{1}".format(
                bkt_ops_conf["test_8649"]["bucket_name"], str(count))
            resp = s3test_obj.object_upload(
                bkt_ops_conf["test_8649"]["bucket_name"],
                objname,
                bkt_ops_conf["bucket_workflow"]["file_path"])
            assert resp[0], resp[1]
            object_list.append(objname)
        LOGGER.info("Multiple objects are uploaded")
        LOGGER.info("Listing all objects")
        resp = s3test_obj.object_list(
            bkt_ops_conf["test_8649"]["bucket_name"])
        assert resp[0], resp[1]
        for each_obj in object_list:
            assert each_obj in resp[1], resp[1]
        LOGGER.info("All objects are listed")
        LOGGER.info("ENDED: List all objects in a bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5448", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2051(self):
        """Verification of disk usage by bucket."""
        LOGGER.info("STARTED: Verification of disk usage by bucket")
        LOGGER.info(
            "Creating a bucket with name %s",
            bkt_ops_conf["test_8650"]["bucket_name"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8650"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8650"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            bkt_ops_conf["test_8650"]["bucket_name"])
        create_file(
            bkt_ops_conf["bucket_workflow"]["file_path"],
            bkt_ops_conf["bucket_workflow"]["file_size"])
        LOGGER.info("Uploading multiple objects to a bucket")
        for count in range(bkt_ops_conf["test_8650"]["object_count"]):
            objname = "{0}{1}".format(
                bkt_ops_conf["test_8650"]["bucket_name"], str(count))
            retv = s3test_obj.object_upload(
                bkt_ops_conf["test_8650"]["bucket_name"],
                objname,
                bkt_ops_conf["bucket_workflow"]["file_path"])
            assert retv[0], retv[1]
        LOGGER.info("Multiple objects are uploaded")
        LOGGER.info("Retrieving bucket size")
        resp = s3test_obj.get_bucket_size(
            bkt_ops_conf["test_8650"]["bucket_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved bucket size")
        LOGGER.info("ENDED: Verification of disk usage by bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5453", "bucket_workflow_operations")
    def test_2055(self):
        """HEAD bucket when Bucket does not exists."""
        LOGGER.info("STARTED: HEAD bucket when Bucket does not exists")
        LOGGER.info("Performing head bucket on non existing bucket")
        try:
            s3test_obj.head_bucket(bkt_ops_conf["test_8654"]["bucket_name"])
        except CTException as error:
            LOGGER.error(error.message)
            assert bkt_ops_conf["test_8654"]["error_message"] in error.message, error.message
        LOGGER.info("Head bucket on non existing bucket is failed")
        LOGGER.info("ENDED: HEAD bucket when Bucket does not exists")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5445", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2056(self):
        """Verify HEAD bucket."""
        LOGGER.info("STARTED: Verify HEAD bucket")
        LOGGER.info(
            "Creating a bucket with name %s",
            bkt_ops_conf["test_8655"]["bucket_name"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8655"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8655"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            bkt_ops_conf["test_8655"]["bucket_name"])
        LOGGER.info(
            "Performing head bucket on a bucket %s",
            bkt_ops_conf["test_8655"]["bucket_name"])
        resp = s3test_obj.head_bucket(bkt_ops_conf["test_8655"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1]["BucketName"] == bkt_ops_conf["test_8655"]["bucket_name"], resp
        LOGGER.info(
            "Performed head bucket on a bucket %s",
            bkt_ops_conf["test_8655"]["bucket_name"])
        LOGGER.info("ENDED: Verify HEAD bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5446", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2057(self):
        """Verify 'LIST buckets' command."""
        LOGGER.info("STARTED: Verify 'LIST buckets' command")
        LOGGER.info("Creating multiple buckets")
        bucket_list = []
        for count in range(bkt_ops_conf["test_8656"]["bucket_count"]):
            bucket_name = "{0}{1}".format(
                bkt_ops_conf["test_8656"]["bucket_name"], str(count))
            resp = s3test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[1]
            bucket_list.append(bucket_name)
        LOGGER.info("Multiple buckets are created")
        LOGGER.info("Listing buckets")
        resp = s3test_obj.bucket_list()
        assert resp[0], resp[1]
        for each_bucket in bucket_list:
            assert each_bucket in resp[1], resp[1]
        LOGGER.info("Buckets are listed")
        LOGGER.info("ENDED: Verify 'LIST buckets' command")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5450", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_2059(self):
        """Verification of bucket location."""
        LOGGER.info("STARTED: Verification of bucket location")
        LOGGER.info(
            "Creating a bucket with name %s",
            bkt_ops_conf["test_8658"]["bucket_name"])
        resp = s3test_obj.create_bucket(
            bkt_ops_conf["test_8658"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == bkt_ops_conf["test_8658"]["bucket_name"], resp[1]
        resp = s3test_obj.bucket_location(
            bkt_ops_conf["test_8658"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1]["LocationConstraint"] == \
            bkt_ops_conf["test_8658"]["bucket_location"], resp[1]
        LOGGER.info("ENDED: Verification of bucket location")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8031", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_432(self):
        """Delete multiobjects which are present in bucket."""
        LOGGER.info(
            "STARTED: Delete multiobjects which are present in bucket")
        test_cfg = bkt_ops_conf["test_432"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        obj_cnt = test_cfg["range"]
        LOGGER.info("Step 1: Creating a bucket and putting object")
        res = s3test_obj.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        create_file(bkt_ops_conf["bucket_workflow"]["file_path"],
                    bkt_ops_conf["bucket_workflow"]["file_size"])
        obj_lst = []
        for i in range(obj_cnt):
            obj = "{}{}".format(test_cfg["obj_pre"], str(i))
            res = s3test_obj.put_object(
                bktname, obj, bkt_ops_conf["bucket_workflow"]["file_path"])
            assert res[0], res[1]
            obj_lst.append(obj)
        LOGGER.info("Step 1: Created bucket and object uploaded")
        LOGGER.info("Step 2: Listing all the objects")
        resp = s3test_obj.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        LOGGER.info("Step 2: All the objects listed")
        LOGGER.info("Step 3: Deleting all the object")
        resp = s3test_obj.delete_multiple_objects(bktname, obj_lst)
        assert resp[0], resp[1]
        LOGGER.info("Step 3: All the objects deleted")
        LOGGER.info("Step 4: Check bucket is empty")
        resp = s3test_obj.object_list(bktname)
        assert resp[0], resp[1]
        resp_bkt_lst = None if not resp[1] else resp[1]
        # For checking the object list should be none
        assert resp_bkt_lst is None, resp
        LOGGER.info("Step 4: Verified that bucket was empty")
        LOGGER.info("ENDED: Delete multiobjects which are present in bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8032", "bucket_workflow_operations")
    def test_433(self):
        """Delete multiobjects where the bucket is not present."""
        LOGGER.info(
            "STARTED: Delete multiobjects where the bucket is not present")
        test_cfg = bkt_ops_conf["test_433"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        obj_lst = test_cfg["obj_lst"]
        LOGGER.info("Step 1: Deleting the objects for non-existing bucket")
        try:
            s3test_obj.delete_multiple_objects(bktname, obj_lst)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["err_message"] in error.message, error.message
            LOGGER.info(
                "Step 1: objects delete operation failed with error %s",
                test_cfg["err_message"])
        LOGGER.info("Step 2: List objects for non-existing bucket")
        try:
            s3test_obj.object_list(bktname)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["err_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: List objects for non-existing bucket failed with error %s",
                test_cfg["err_message"])
        LOGGER.info(
            "ENDED: Delete multiobjects where the bucket is not present")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8033", "bucket_workflow_operations")
    def test_434(self):
        """
        create bucket and upload objects from account1.

         and dont give any permissions to account2 and delete multiple objects from account2
        :avocado: tags=bucket_workflow_cross_account
        """
        LOGGER.info(
            "STARTED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
        test_cfg = bkt_ops_conf["test_434"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        obj_cnt = test_cfg["range"]
        acc_name_2 = test_cfg["account_name"].format(self.random_id)
        emailid_2 = test_cfg["email_id"].format(self.random_id)
        LOGGER.info(
            "Step : Creating account with name %s and email_id %s",
            acc_name_2, emailid_2)
        create_account = iam_obj.create_account_s3iamcli(
            acc_name_2,
            emailid_2,
            self.ldap_user,
            self.ldap_pwd)
        assert create_account[0], create_account[1]
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        LOGGER.info("Step Successfully created the s3iamcli account")
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        LOGGER.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = s3test_obj.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        create_file(bkt_ops_conf["bucket_workflow"]["file_path"],
                    bkt_ops_conf["bucket_workflow"]["file_size"])
        obj_lst = []
        for i in range(obj_cnt):
            obj = "{}{}".format(test_cfg["obj_pre"], str(i))
            res = s3test_obj.put_object(
                bktname, obj, bkt_ops_conf["bucket_workflow"]["file_path"])
            assert res[0], res[1]
            obj_lst.append(obj)
        LOGGER.info(
            "Step 1: Created bucket and object uploaded in account 1")
        LOGGER.info("Step 2: Listing all the objects using account 1")
        resp = s3test_obj.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        LOGGER.info("Step 2: All the objects listed using account 1")
        try:
            LOGGER.info("Step 3: Deleting all the object using account 2")
            s3_obj_2.delete_multiple_objects(bktname, obj_lst)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["err_message"] in error.message, error.message
            LOGGER.info(
                "Step 3: deleting objects using account 2 failed with error %s",
                test_cfg["err_message"])
        LOGGER.info(
            "ENDED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8035", "bucket_workflow_operations")
    @CTFailOn(error_handler)
    def test_435(self):
        """
        create bucket and upload objects from account1.

        and dont give any permissions to
        account2 and delete multiple objects from account2
        :avocado: tags=bucket_workflow_cross_account
        """
        LOGGER.info(
            "STARTED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
        test_cfg = bkt_ops_conf["test_435"]
        bktname = test_cfg["bucket_name"].format(self.random_id)
        obj_cnt = test_cfg["range"]
        acc_name_2 = test_cfg["account_name"].format(self.random_id)
        emailid_2 = test_cfg["email_id"].format(self.random_id)
        LOGGER.info(
            "Step : Creating account with name %s and email_id %s",
            acc_name_2, emailid_2)
        create_account = iam_obj.create_account_s3iamcli(
            acc_name_2,
            emailid_2,
            self.ldap_user,
            self.ldap_pwd)
        assert create_account[0], create_account[1]
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        LOGGER.info("Step Successfully created the s3iamcli account")
        cannonical_id = create_account[1]["canonical_id"]
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        LOGGER.info(
            "Step 1: Creating a bucket and putting object using acccount 1")
        res = s3test_obj.create_bucket(bktname)
        assert res[1] == bktname, res[1]
        create_file(bkt_ops_conf["bucket_workflow"]["file_path"],
                    bkt_ops_conf["bucket_workflow"]["file_size"])
        obj_lst = []
        for i in range(obj_cnt):
            obj = "{}{}".format(test_cfg["obj_pre"], str(i))
            res = s3test_obj.put_object(
                bktname, obj, bkt_ops_conf["bucket_workflow"]["file_path"])
            assert res[0], res[1]
            obj_lst.append(obj)
        LOGGER.info(
            "Step 1: Created bucket and object uploaded in account 1")
        LOGGER.info("Step 2: Listing all the objects using account 1")
        resp = s3test_obj.object_list(bktname)
        assert resp[0], resp[1]
        resp[1].sort()
        obj_lst.sort()
        assert resp[1] == obj_lst, resp
        LOGGER.info("Step 2: All the objects listed using account 1")
        LOGGER.info(
            "Step 3: give full-control permissions for account2 for the bucket")
        resp = acl_obj.put_bucket_acl(
            bktname, grant_full_control=test_cfg["id_str"].format(cannonical_id))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Full-control permission was successfully assigned to account 2")
        LOGGER.info("Step 4: Deleting all the object using account 2")
        resp = s3_obj_2.delete_multiple_objects(bktname, obj_lst)
        assert resp[0], resp[1]
        LOGGER.info("Step 4: All the objects deleted")
        LOGGER.info("Step 5: Check bucket is empty")
        acl_obj.put_bucket_acl(
            bktname, acl=bkt_ops_conf["bucket_workflow"]["bkt_permission"])
        resp = s3test_obj.object_list(bktname)
        assert resp[0], resp[1]
        resp_bkt_lst = None if not resp[1] else resp[1]
        # For checking the object list should be none
        assert resp_bkt_lst is None, resp
        LOGGER.info("Step 5: Verified that bucket was empty")
        resp = s3test_obj.delete_bucket(bktname, force=True)
        assert resp[0], resp[1]
        LOGGER.info(
            "ENDED: create bucket and upload objects from account1 and dont give"
            " any permissions to account2 and delete multiple objects from account2")
