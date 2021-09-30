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

"""Delayed Delete test module."""

import os
import time
import logging
import pytest
from random import choice, randint

from commons.ct_fail_on import CTFailOn
from commons.exceptions import CTException
from commons.errorcodes import error_handler, S3_CLIENT_ERROR
from commons.utils.system_utils import create_file, remove_file, path_exists
from commons.utils.system_utils import backup_or_restore_files, split_file, remove_dirs
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.configmanager import get_config_wrapper, config_utils
from commons.utils.config_utils import read_yaml
from commons.params import TEST_DATA_FOLDER
from config import S3_OBJ_TST
from libs.s3 import S3_CFG
from libs.s3 import S3H_OBJ, ACCESS_KEY, SECRET_KEY
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations

MPART_CFG = read_yaml("config/s3/test_multipart_upload.yaml")[1]
BLACKBOX_CONF = get_config_wrapper(fpath="config/blackbox/test_blackbox.yaml")


class TestDelayedDelete:
    """Delayed Delete Test Suite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        self.aws_config_path = []
        self.aws_config_path.append(S3_CFG["aws_config_path"])
        self.actions = ["backup", "restore"]
        self.random_time = int(time.time())
        self.bucket_name = S3_OBJ_TST["s3_object"]["bucket_name"].format(
            time.perf_counter_ns())
        self.object_name = S3_OBJ_TST["s3_object"]["object_name"].format(
            time.perf_counter_ns())
        self.test_file = "testfile-{}.txt".format(time.perf_counter_ns())
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestDelayedDelete")
        self.test_file_path = os.path.join(self.test_dir_path, self.test_file)
        self.mp_obj_path = os.path.join(self.test_dir_path, self.test_file)
        self.config_backup_path = os.path.join(self.test_dir_path, "config_backup")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.log.info("Test file path: %s", self.test_file_path)
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.access_key = ACCESS_KEY
        self.secret_key = SECRET_KEY
        self.start_range = S3_OBJ_TST["s3_object"]["start_range"]
        self.end_range = S3_OBJ_TST["s3_object"]["end_range"]
        self.random_num = str(
            choice(
                range(
                    self.start_range,
                    self.end_range)))
        res_ls = system_utils.execute_cmd(
            "ls scripts/jcloud/")[1]
        res = ".jar" in res_ls
        if not res:
            res = system_utils.configure_jclient_cloud(
                source=S3_CFG["jClientCloud_path"]["source"],
                destination=S3_CFG["jClientCloud_path"]["dest"],
                nfs_path=S3_CFG["nfs_path"],
                ca_crt_path=S3_CFG["s3_cert_path"]
            )
            self.log.info(res)
            if not res:
                raise CTException(
                    S3_CLIENT_ERROR,
                    "Error: jcloudclient.jar or jclient.jar file does not exists")
        self.s3_url = S3_CFG['s3_url'].replace("https://", "").replace("http://", "")
        self.s3_iam = S3_CFG['iam_url'].strip("https://").strip("http://").strip(":9443")
        resp = self.update_jclient_jcloud_properties()
        assert_utils.assert_true(resp, resp)
        self.account_name = "objaclacc{}".format(time.perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.account_name)
        self.account_name_1 = "objaclacc_one{}".format(time.perf_counter_ns())
        self.email_id_1 = "{}@seagate.com".format(self.account_name_1)
        self.account_name_2 = "objaclacc_two{}".format(time.perf_counter_ns())
        self.email_id_2 = "{}@seagate.com".format(self.account_name_2)
        self.rest_obj = S3AccountOperations()
        self.account_list = []
        self.log.info(
            "Taking a backup of aws config file located at %s to %s...",
            self.aws_config_path, self.config_backup_path)
        resp = backup_or_restore_files(
            self.actions[0], self.config_backup_path, self.aws_config_path)
        assert (resp[0], resp[1])
        self.log.info(
            "Taken a backup of aws config file located at %s to %s",
            self.aws_config_path, self.config_backup_path)
        self.log.info(
            "S3_SERVER_OBJECT_DELAYED_DELETE value in s3config.yaml should be "
            "set to True.")
        status, response = S3H_OBJ.update_s3config(
            parameter="S3_SERVER_OBJECT_DELAYED_DELETE", value=True)
        assert_utils.assert_true(status, response)
        yield
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info(
            "S3_SERVER_OBJECT_DELAYED_DELETE value in s3config.yaml should be "
            "set to True.")
        status, response = S3H_OBJ.update_s3config(
            parameter="S3_SERVER_OBJECT_DELAYED_DELETE", value=True)
        assert_utils.assert_true(status, response)
        resp = self.s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in resp[1] if
            each_bucket.startswith("testbucket")]
        if pref_list:
            resp = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert resp[0], resp[1]
        self.log.info(
            "Restoring aws config file from %s to %s...",
            self.config_backup_path,
            self.aws_config_path)
        resp = backup_or_restore_files(
            self.actions[1], self.config_backup_path, self.aws_config_path)
        assert resp[0], resp[1]
        self.log.info(
            "Restored aws config file from %s to %s",
            self.config_backup_path,
            self.aws_config_path)
        self.log.info("Deleting a backup file and directory...")
        if path_exists(self.config_backup_path):
            remove_dirs(self.config_backup_path)
        if path_exists(self.mp_obj_path):
            remove_file(self.mp_obj_path)
        self.log.info("Deleted a backup file and directory")
        self.log.info("ENDED: Teardown operations")

    def create_cmd(self, bucket, operation, jtool=None):
        """
        Function forms a command to perform specified operation.

        using given bucket name and returns a single line command.
        :param str bucket: Name of the s3 bucket
        :param str operation: type of operation to be performed on s3
        :param str jtool: Name of the java jar tool
        :return: str command: cli command to be executed
        """
        if jtool == BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"]:
            java_cmd = BLACKBOX_CONF["jcloud_cfg"]["jcloud_cmd"]
            aws_keys_str = "--access-key {} --secret-key {}".format(
                self.access_key, self.secret_key)
            bucket_url = "s3://{}".format(bucket)
            cmd = "{} {} {} {} {}".format(java_cmd, operation, bucket_url,
                                          aws_keys_str, "-p")
            self.log.info("jcloud command: %s", cmd)
        else:
            java_cmd = BLACKBOX_CONF["jcloud_cfg"]["jclient_cmd"]
            aws_keys_str = "--access_key {} --secret_key {}".format(
                self.access_key, self.secret_key)
            bucket_url = "s3://{}".format(bucket)
            cmd = "{} {} {} {} {} {}".format(java_cmd, operation, bucket_url,
                                             aws_keys_str, "-p", "-C")
            self.log.info("jclient command: %s", cmd)

        return cmd

    def update_jclient_jcloud_properties(self):
        """
        Update jclient, jcloud properties with correct s3, iam endpoint.

        :return: True
        """
        resp = False
        for prop_path in [BLACKBOX_CONF["jcloud_cfg"]["jclient_properties_path"],
                          BLACKBOX_CONF["jcloud_cfg"]["jcloud_properties_path"]]:
            self.log.info("Updating: %s", prop_path)
            prop_dict = config_utils.read_properties_file(prop_path)
            if prop_dict:
                if prop_dict['iam_endpoint'] != self.s3_iam:
                    prop_dict['iam_endpoint'] = self.s3_iam
                if prop_dict['s3_endpoint'] != self.s3_url:
                    prop_dict['s3_endpoint'] = self.s3_url
                resp = config_utils.write_properties_file(prop_path, prop_dict)

        return resp

    def create_bucket_put_list_object(
            self,
            bucket_name,
            obj_name,
            file_path,
            mb_count,
            **kwargs):
        """
        Function creates a bucket, uploads an object.

        to the bucket and list objects from the bucket.
        :param bucket_name: Name of bucket to be created
        :param obj_name: Name of an object to be put to the bucket
        :param file_path: Path of the file to be created and uploaded to bucket
        :param mb_count: Size of file in MBs
        :param m_key: Key for metadata
        :param m_value: Value for metadata
        """
        m_key = kwargs.get("m_key", None)
        m_value = kwargs.get("m_value", None)
        self.log.info("Creating a bucket %s", bucket_name)
        resp = self.s3_test_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info("Created a bucket %s", bucket_name)
        create_file(file_path, mb_count)
        self.log.info(
            "Uploading an object %s to bucket %s",
            obj_name, bucket_name)
        resp = self.s3_test_obj.put_object(
            bucket_name, obj_name, file_path, m_key=m_key, m_value=m_value)
        assert resp[0], resp[1]
        self.log.info(
            "Uploaded an object %s to bucket %s", obj_name, bucket_name)
        self.log.info("Listing objects from a bucket %s", bucket_name)
        resp = self.s3_test_obj.object_list(bucket_name)
        assert resp[0], resp[1]
        assert obj_name in resp[1], resp[1]
        self.log.info(
            "Objects are listed from a bucket %s", bucket_name)
        if m_key:
            self.log.info(
                "Retrieving metadata of an object %s", obj_name)
            resp = self.s3_test_obj.object_info(bucket_name, obj_name)
            assert resp[0], resp[1]
            assert m_key in resp[1]["Metadata"], resp[1]
            self.log.info(
                "Retrieved metadata of an object %s", obj_name)

    def create_put_object_jclient(self,
                                  bucket_name,
                                  test_file_path,
                                  option
                                  ):
        self.file_path_lst = []
        self.bucket_list = []
        self.log.info("STARTED: put object using jcloudclient")
        if option == 1:
            self.log.info("Creating bucket %s", bucket_name)
            command = self.create_cmd(
                      bucket_name,
                      "mb",
                      jtool=BLACKBOX_CONF["jcloud_cfg"]["jcloud_tool"])
            resp = system_utils.execute_cmd(command)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_in(
                "Bucket created successfully", resp[1][:-1], resp[1])
            self.log.info("Bucket was created %s", bucket_name)
            res = system_utils.create_file(test_file_path,
                                           2048)
            logging.info("The file is %s", res)

        if option in ("PUT", 1):
            self.log.info("Put object to a bucket %s", bucket_name)
            put_cmd_str = "{} {}".format("put",
                                         test_file_path)
            command = self.create_cmd(
                            bucket_name,
                            put_cmd_str,
                            jtool=BLACKBOX_CONF["jcloud_cfg"]["jclient_tool"])
            resp = system_utils.execute_cmd(command)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_in(
               "Object put successfully", resp[1][:-1], resp[1])
            self.log.info(
                "Put object to a bucket %s was successful", bucket_name)
            self.file_path_lst.append(test_file_path)
            self.bucket_list.append(bucket_name)

    def put_multiple_objects(self,
                             bucket_name,
                             object_lst, file_path):
        """
        This functions put the multiple objects to the bucket.
        :param bucket_name: Name of the bucket
        :param object_lst: list of the object
        :param file_path: Path of the file
        :return: (Boolean, object of put object method)
        """
        self.log.info("Putting object %s", object_lst)
        for obj_name in object_lst:
            logging.info("Uploading the objects %s", obj_name)
            self.s3_test_obj.put_object(bucket_name, obj_name, file_path)
            logging.info("Object %s is Uploaded to %s", obj_name,
                         bucket_name)
        return True, object_lst

    def get_multiple_object_head(self, bucket_name, object_lst):
        """
        This Function fetch the head of the object
        for multiple objects and returns the size list,
        last modified time list, etag list of the objects
        """
        time_lst = []
        size_lst = []
        etag_lst = []
        self.log.info("The obj list in mthd is %s", object_lst)
        for obj in object_lst:
            resp = self.s3_test_obj.object_info(
                   bucket_name,
                   obj)
            assert resp[0], resp[1]
            last_m_time_o = resp[1]["LastModified"]
            etag = resp[1]["ETag"]
            size_o = resp[1]["ContentLength"]
            time_lst.append(last_m_time_o)
            size_lst.append(size_o)
            etag_lst.append(etag)
        return time_lst, size_lst, etag_lst

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28995')
    @CTFailOn(error_handler)
    def test_28995(self):
        """
        To test the multiple object upload of random size
        with delayed delete option is set to TRUE.
        """
        logging.info("Creating bucket")
        self.s3_test_obj.create_bucket(self.bucket_name)
        logging.info("Uploading the object")
        resp = self.s3_test_obj.put_random_size_objects(
            self.bucket_name,
            self.object_name,
            S3_OBJ_TST["s3_object"]["obj_min_size"],
            S3_OBJ_TST["s3_object"]["obj_max_size"],
            object_count=S3_OBJ_TST["s3_object"]["object_count"],
            file_path=self.test_file_path)
        object_lst = resp[1]
        logging.info("Object is uploaded %s", object_lst)
        result = self.get_multiple_object_head(self.bucket_name,
                                               object_lst)
        logging.info("Last Modified Time of object info %s", result[0])
        logging.info("Size of object %s", result[1])
        logging.info("ETag of object info %s", result[2])
        logging.info("=== Re-upload same file ===")
        res = self.put_multiple_objects(
            self.bucket_name,
            object_lst,
            file_path=self.test_file_path)
        assert_utils.assert_true(res[0], res[1])
        logging.info(
            "Uploaded an object %s to bucket %s", res[1],
            self.bucket_name)
        result_r = self.get_multiple_object_head(self.bucket_name,
                                                 res[1])
        for last_mod_time, r_last_mod_time in zip(result[0], result_r[0]):
            assert_utils.assert_true(
                last_mod_time < r_last_mod_time,
                f"LastModified for the old object {last_mod_time}. "
                f"LastModified for the new object is {r_last_mod_time}")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29032')
    @CTFailOn(error_handler)
    def test_29032(self):
        """
        This Test will perform the re-upload of object
        with multipart upload
        """
        self.log.info("Initiate Multipart upload")
        mp_config = MPART_CFG["test_8660_8664_8665_8668"]
        self.log.info("Creating a bucket with name : %s",
                      self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s", self.bucket_name)
        res = self.s3_mp_test_obj.create_multipart_upload(
            self.bucket_name, self.object_name,
            m_key=S3_OBJ_TST["test_8554"]["key"],
            m_value=S3_OBJ_TST["test_8554"]["value"])
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info(
            "Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Uploading parts into bucket")
        res = self.s3_mp_test_obj.upload_parts(
            mpu_id,
            self.bucket_name,
            self.object_name,
            mp_config["file_size"],
            total_parts=mp_config["total_parts"],
            multipart_obj_path=self.mp_obj_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]),
                                  mp_config["total_parts"], res[1])
        parts = res[1]
        self.log.info("Uploaded parts into bucket: %s", parts)
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  mp_config["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        resp = self.s3_test_obj.object_info(
               self.bucket_name,
               self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        last_m_time_o = resp[1]["LastModified"]
        self.log.info("===Re-upload the same file in"
                      " single upload===")
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            file_path=self.mp_obj_path,
            m_key=S3_OBJ_TST["test_8554"]["key"],
            m_value=S3_OBJ_TST["test_8554"]["value"]
            )
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_test_obj.object_info(
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        last_m_time_r = resp[1]["LastModified"]
        assert_utils.assert_true(last_m_time_o < last_m_time_r,
                                 f"The last modified time is changed"
                                 f"Old time is {last_m_time_o},"
                                 f"new time is {last_m_time_r}")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28444')
    @CTFailOn(error_handler)
    def test_28444(self):
        """
        To test the simple upload of 50 Mb object
        with delayed delete option is set to TRUE.
        and kill the s3backgrounddelete service.
        """
        logging.info("Creating bucket")
        logging.info(
            "Bucket and Object : %s %s",
            self.bucket_name,
            self.object_name)
        logging.info("Uploading the object")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["mb_count"],
            m_key=S3_OBJ_TST["test_8554"]["key"],
            m_value=S3_OBJ_TST["test_8554"]["value"])
        logging.info("Object is uploaded %s", )
        resp = self.s3_test_obj.object_info(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_8554"]["key"] in resp[1]["Metadata"], resp[1]
        last_m_time_o = resp[1]["LastModified"]
        etag = resp[1]["ETag"]
        size_o = resp[1]["ContentLength"]
        logging.info("Last Modified Time of object info %s", last_m_time_o)
        logging.info("ETag of object info %s", etag)
        logging.info("Size of object %s", size_o)
        time.sleep(60)
        logging.info("Re-upload same file")
        logging.info("Uploading an object %s to bucket %s",
                     self.object_name, self.bucket_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name, self.object_name, self.test_file_path,
            m_key=S3_OBJ_TST["test_8554"]["key"],
            m_value=S3_OBJ_TST["test_8554"]["value"])
        # TODO KILL the s3backgrounddelete service
        assert resp[0], resp[1]
        logging.info(
            "Uploaded an object %s to bucket %s", self.object_name, self.bucket_name)
        logging.info("Listing objects from a bucket %s", self.bucket_name)
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert resp[0], resp[1]
        assert self.object_name in resp[1], resp[1]
        logging.info(
            "Objects are listed from a bucket %s", self.bucket_name)
        logging.info("Object is re-uploaded %s", self.object_name)
        resp = self.s3_test_obj.object_info(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_8554"]["key"] in resp[1]["Metadata"], resp[1]
        etag_r = resp[1]["ETag"]
        last_m_time_r = resp[1]["LastModified"]
        size_r = resp[1]["ContentLength"]
        logging.info("ETag of object on re-upload %s", etag_r)
        logging.info("Last Modified time of object on re-upload %s"
                     , last_m_time_r)
        logging.info("Size of object on re-upload %s", size_r)
        if size_o == size_r:
            logging.info("The Size of objects are  of same size on first upload"
                         " %s,size on re-upload %s", size_o, size_r)
        else:
            logging.error("The size of objects are different"
                          " a: %s, b: %s", size_o, size_r)
        if last_m_time_o == last_m_time_r:
            logging.error("The time is same seems object re-upload failed")
        else:
            logging.info("The Last modified time"
                         " is different %s, %s", last_m_time_o, last_m_time_r)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29043')
    @CTFailOn(error_handler)
    def test_29043(self):
        """
        Test to verify deletion of objects when
        delayed delete option is enabled using simple object
        upload chunk.
        """
        self.log.info("STARTED: put object using jcloudclient %s",
                      self.test_file)
        self.create_put_object_jclient(self.bucket_name,
                                       self.test_file_path, 1)

        result = self.s3_test_obj.object_info(self.bucket_name,
                                              self.test_file)
        obj_last_m_t = result[1]["LastModified"]
        obj_size = result[1]["ContentLength"]
        self.log.info("Re-Upload the same file")
        self.create_put_object_jclient(self.bucket_name,
                                       self.test_file_path,
                                       "PUT")
        result = self.s3_test_obj.object_info(self.bucket_name,
                                              self.test_file)
        obj_last_m_t_r = result[1]["LastModified"]
        obj_size_r = result[1]["ContentLength"]
        assert_utils.assert_true(obj_last_m_t < obj_last_m_t_r,
                                 f"The Object is overwrite"
                                 f" as its Last modified time is changed"
                                 f"new time {obj_last_m_t_r}"
                                 f" and old time {obj_last_m_t}")
        assert_utils.assert_true(obj_size_r == obj_size,
                                 f"Obj size are same {obj_size_r}")
        self.log.info("Deleting the Chunk uploaded Objects")
        result = self.s3_test_obj.delete_object(self.bucket_name, self.test_file)
        assert_utils.assert_true(result[0], result[1])
        resp = self.s3_test_obj.object_list(self.bucket_name)
        if not resp:
            self.log.info("The given Object %s is deleted"
                          " from bucket %s", self.test_file,
                          self.bucket_name)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-17122')
    @CTFailOn(error_handler)
    def test_17122(self):
        """
        This Function test the Object deletion
        when delayed delete is set to False
        """
        self.log.info("Testing when DELAYED DELETE is set to False\n")
        self.log.info(
            "S3_SERVER_OBJECT_DELAYED_DELETE value in s3config.yaml should be "
            "set to True.")
        status, response = S3H_OBJ.update_s3config(
            parameter="S3_SERVER_OBJECT_DELAYED_DELETE", value=False)
        assert_utils.assert_true(status, response)
        self.log.info("STARTED: put object using jcloudclient %s",
                      self.test_file)
        self.create_put_object_jclient(self.bucket_name,
                                       self.test_file_path, 1)

        result = self.s3_test_obj.object_info(self.bucket_name,
                                              self.test_file)
        obj_last_m_t = result[1]["LastModified"]
        obj_size = result[1]["ContentLength"]
        self.log.info("Re-Upload the same file")
        self.create_put_object_jclient(self.bucket_name,
                                       self.test_file_path,
                                       "PUT")
        result = self.s3_test_obj.object_info(self.bucket_name,
                                              self.test_file)
        obj_last_m_t_r = result[1]["LastModified"]
        obj_size_r = result[1]["ContentLength"]
        assert_utils.assert_true(obj_last_m_t < obj_last_m_t_r,
                                 f"The Object is overwrite"
                                 f" as its Last modified time is changed"
                                 f"new time {obj_last_m_t_r}"
                                 f" and old time {obj_last_m_t}")
        assert_utils.assert_true(obj_size_r == obj_size,
                                 f"Obj size are same {obj_size_r}")
