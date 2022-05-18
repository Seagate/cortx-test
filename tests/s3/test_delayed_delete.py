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


"""S3Background or Delayed Delete test module."""

import logging
import os
import time
from multiprocessing import Pool

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config.s3 import MPART_CFG, S3_BLKBOX_CFG, DEL_CFG, S3_OBJ_TST
from libs.s3 import S3H_OBJ, ACCESS_KEY, SECRET_KEY
from libs.s3 import S3_CFG
from libs.s3.s3_blackbox_test_lib import JCloudClient
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench


class TestDelayedDelete:
    """S3Background or Delayed Delete test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        """
        cls.log = logging.getLogger(__name__)
        logging.info("STARTED: Setup operations")
        cls.s3_test_obj = S3TestLib()
        cls.s3_mp_test_obj = S3MultipartTestLib()
        cls.jclient_obj = JCloudClient()
        cls.aws_config_path = []
        cls.aws_config_path.append(S3_CFG["aws_config_path"])
        cls.actions = ["backup", "restore"]
        cls.random_time = int(time.time())
        cls.bucket_name = S3_OBJ_TST["s3_object"]["bucket_name"].format(
            time.perf_counter_ns())
        cls.object_name = S3_OBJ_TST["s3_object"]["object_name"].format(
            time.perf_counter_ns())
        cls.s3_url = S3_CFG['s3_url'].replace("https://", "").replace("http://", "")
        cls.s3_iam = S3_CFG['iam_url'].strip("https://").strip("http://").strip(":9443")
        cls.test_file = "testfile-{}.txt".format(time.perf_counter_ns())
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestDelayedDelete")
        cls.test_file_path = os.path.join(cls.test_dir_path, cls.test_file)
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)
        if not system_utils.path_exists(cls.test_dir_path):
            system_utils.make_dirs(cls.test_dir_path)
            logging.info("Created path: %s", cls.test_dir_path)
        logging.info("Test file path: %s", cls.test_file_path)
        cls.config_backup_path = os.path.join(
            cls.test_dir_path, "config_backup")
        logging.info("config_backup path: %s", cls.config_backup_path)
        cls.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        cls.access_key = ACCESS_KEY
        cls.secret_key = SECRET_KEY
        cls.rest_obj = S3AccountOperations()
        cls.file_path_lst = []
        cls.bucket_list = []
        resp = system_utils.backup_or_restore_files(
            cls.actions[0], cls.config_backup_path,
            cls.aws_config_path)
        assert_utils.assert_true(resp[0], resp[1])
        logging.info("Taken a backup of aws config"
                     " file located at %s to %s", cls.aws_config_path,
                     cls.config_backup_path)
        cls.s3_url = S3_CFG['s3_url'].replace("https://", "").replace("http://", "")
        cls.s3_iam = S3_CFG['iam_url'].strip("https://").strip("http://").strip(":9443")
        logging.info("ENDED: Setup operations")

    def setup_method(self):
        """Configuring all pre-requisite for tests"""
        self.log.info("STARTED: Test Setup")
        res_ls = system_utils.execute_cmd("ls scripts/jcloud/")[1]
        res = ".jar" in res_ls
        if not res:
            res = self.jclient_obj.configure_jclient_cloud(
                source=S3_CFG["jClientCloud_path"]["source"],
                destination=S3_CFG["jClientCloud_path"]["dest"],
                nfs_path=S3_CFG["nfs_path"],
                ca_crt_path=S3_CFG["s3_cert_path"])
            logging.info(res)
        assert_utils.assert_true(res)
        self.jclient_obj.update_jclient_jcloud_properties()
        logging.info("S3_SERVER_OBJECT_DELAYED_DELETE"
                     " value in s3config.yaml should be "
                     "set to True.")
        status, response = S3H_OBJ.update_s3config(
            parameter="S3_SERVER_OBJECT_DELAYED_DELETE", value=True)
        assert_utils.assert_true(status, response)
        res_ls = system_utils.execute_cmd("ls scripts/jcloud/")[1]
        res = ".jar" in res_ls
        if not res:
            res = self.jclient_obj.configure_jclient_cloud(
                source=S3_CFG["jClientCloud_path"]["source"],
                destination=S3_CFG["jClientCloud_path"]["dest"],
                nfs_path=S3_CFG["nfs_path"],
                ca_crt_path=S3_CFG["s3_cert_path"])
            logging.info(res)
            assert_utils.assert_true(res)

        self.jclient_obj.update_jclient_jcloud_properties()
        if not system_utils.path_exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", resp)
        self.test_file_path = os.path.join(self.test_dir_path,
                                           self.test_file.format(str(int(time.time()))))
        logging.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case.
        It will clean up resources which are getting
        created during test case execution.
        This function will delete files and buckets.
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
        resp = system_utils.backup_or_restore_files(
            self.actions[1], self.config_backup_path,
            self.aws_config_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Restored aws config file from %s to %s",
            self.config_backup_path,
            self.aws_config_path)
        self.log.info("Deleting a backup file and directory...")
        dir_lst = [self.test_file_path, self.config_backup_path]
        res = os.listdir(path=self.test_dir_path)
        res.remove("config_backup")
        self.log.info("The files list is %s", res)
        for file in res:
            file = os.path.join(self.test_dir_path, file)
            if system_utils.path_exists(file):
                system_utils.remove_file(file)
                self.log.info("Deleted the files %s", file)
        for dirs in dir_lst:
            if system_utils.path_exists(dirs):
                system_utils.remove_dirs(dirs)
                self.log.info("Deleted the directory %s", dirs)
        self.log.info("Deleted a backup file and directory")
        self.log.info("ENDED: Teardown operations")

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
        :keyword m_key: Key for metadata
        :keyword m_value: Value for metadata
        """
        m_key = kwargs.get("m_key", None)
        m_value = kwargs.get("m_value", None)
        self.log.info("Creating a bucket %s", bucket_name)
        resp = self.s3_test_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info("Created a bucket %s", bucket_name)
        system_utils.create_file(file_path, mb_count)
        self.log.info(
            "Uploading an object %s to bucket %s",
            obj_name, bucket_name)
        resp = self.s3_test_obj.put_object(
            bucket_name, obj_name, file_path, m_key=m_key, m_value=m_value)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Uploaded an object %s to bucket %s", obj_name, bucket_name)
        self.log.info("Listing objects from a bucket %s", bucket_name)
        resp = self.s3_test_obj.object_list(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert obj_name in resp[1], resp[1]
        self.log.info(
            "Objects are listed from a bucket %s", bucket_name)
        if m_key:
            self.log.info(
                "Retrieving metadata of an object %s", obj_name)
            resp = self.s3_test_obj.object_info(bucket_name, obj_name)
            assert_utils.assert_true(resp[0], resp[1])
            assert m_key in resp[1]["Metadata"], resp[1]
            self.log.info(
                "Retrieved metadata of an object %s", obj_name)

    def create_put_object_jclient(self,
                                  bucket_name,
                                  test_file_path,
                                  option
                                  ):
        """
        This Function creates the bucket
        and put the object using jclient
        :param: bucket_name
        :param: test_file_path
        :option: Its to select teh create and put operation
        """
        self.log.info("STARTED: put object using jcloudclient")
        if option == 1:
            self.log.info("Creating bucket %s", bucket_name)
            command = self.jclient_obj.create_cmd(bucket_name, "mb",
                                                  jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"])
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
            command = self.jclient_obj.create_cmd_format(
                bucket_name,
                put_cmd_str,
                jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jclient_tool"],
                chunk=True)
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
        obj_dict = {}
        for obj in object_lst:
            resp = self.s3_test_obj.object_info(
                bucket_name,
                obj)
            assert resp[0], resp[1]
            obj_dict[obj] = [resp[1]["LastModified"],
                             resp[1]["ETag"],
                             resp[1]["ContentLength"]]
        return obj_dict

    @pytest.mark.s3_ops
    @pytest.mark.s3_delete
    @pytest.mark.tags('TEST-28995')
    @CTFailOn(error_handler)
    def test_28995(self):
        """
        To test the multiple object upload of random size
        with delayed delete option is set to TRUE.
        """
        logging.info("STEP 1: Creating bucket")
        self.s3_test_obj.create_bucket(self.bucket_name)
        logging.info("STEP 2: Uploading the object")
        resp = self.s3_test_obj.put_random_size_objects(
            self.bucket_name,
            self.object_name,
            S3_OBJ_TST["s3_object"]["obj_min_size"],
            S3_OBJ_TST["s3_object"]["obj_max_size"],
            object_count=S3_OBJ_TST["s3_object"]["object_count"],
            file_path=self.test_file_path, delete_file=False)
        object_lst = resp[1]
        logging.info("STEP 2:Object is uploaded %s", object_lst)
        result = self.get_multiple_object_head(self.bucket_name,
                                               object_lst)
        logging.info("STEP 3:Re-upload same file")
        res = self.put_multiple_objects(
            self.bucket_name,
            object_lst,
            file_path=self.test_file_path)
        assert_utils.assert_true(res[0], res[1])
        logging.info(
            "Uploaded an object %s to bucket %s", res[1],
            self.bucket_name)
        result_r = self.get_multiple_object_head(self.bucket_name,
                                                 object_lst)
        for objects in object_lst:
            if result_r[objects][0] > result[objects][0]:
                logging.info("The Last modified time"
                             " is changed of %s", {objects})

    @pytest.mark.s3_ops
    @pytest.mark.s3_delete
    @pytest.mark.tags('TEST-29032')
    @CTFailOn(error_handler)
    def test_29032(self):
        """
        This Test will perform the re-upload of object
        with multipart upload
        """
        self.log.info("Initiate Multipart upload")
        mp_config = MPART_CFG["test_8660_8664_8665_8668"]
        self.log.info("STEP 1:Creating a bucket with name : %s",
                      self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("STEP 1 :"
                      "Created a bucket with name : %s", self.bucket_name)
        res = self.s3_mp_test_obj.create_multipart_upload(
            self.bucket_name, self.object_name,
            m_key=S3_OBJ_TST["test_8554"]["key"],
            m_value=S3_OBJ_TST["test_8554"]["value"])
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("STEP 2:"
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
        self.log.info("STEP 2: Multipart upload completed")
        resp = self.s3_test_obj.object_info(
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        last_m_time_o = resp[1]["LastModified"]
        self.log.info("STEP 3: Re-upload the same file in"
                      " single upload===")
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            file_path=self.mp_obj_path,
            m_key=S3_OBJ_TST["test_8554"]["key"],
            m_value=S3_OBJ_TST["test_8554"]["value"]
        )
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("STEP 4: Get Object details after"
                      " re-upload")
        resp = self.s3_test_obj.object_info(
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        last_m_time_r = resp[1]["LastModified"]
        if last_m_time_o < last_m_time_r:
            self.log.info("The last modified time is changed"
                          "Old time is %s new time is %s",
                          {last_m_time_o}, {last_m_time_r})

    @pytest.mark.s3_ops
    @pytest.mark.s3_delete
    @pytest.mark.tags('TEST-28444')
    @CTFailOn(error_handler)
    def test_28444(self):
        """
        To test the simple upload of 50 Mb object
        with delayed delete option is set to TRUE.
        and kill the s3backgrounddelete service.
        """
        logging.info("STEP 1: Creating bucket")
        logging.info(
            "Bucket and Object : %s %s",
            self.bucket_name,
            self.object_name)
        logging.info("STEP 2: Uploading the object")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["mb_count"],
            m_key=S3_OBJ_TST["test_8554"]["key"],
            m_value=S3_OBJ_TST["test_8554"]["value"])
        logging.info("STEP 2: Object is uploaded %s", )
        resp = self.s3_test_obj.object_info(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_8554"]["key"] in resp[1]["Metadata"], resp[1]
        last_m_time_o = resp[1]["LastModified"]
        etag = resp[1]["ETag"]
        size_o = resp[1]["ContentLength"]
        logging.info("STEP 3 Fetch object details")
        logging.info("Last Modified Time of object info %s", last_m_time_o)
        logging.info("ETag of object info %s", etag)
        logging.info("Size of object %s", size_o)
        time.sleep(60)
        logging.info("STEP 4:Re-upload same file")
        logging.info("Uploading an object %s to bucket %s",
                     self.object_name, self.bucket_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name, self.object_name, self.test_file_path,
            m_key=S3_OBJ_TST["test_8554"]["key"],
            m_value=S3_OBJ_TST["test_8554"]["value"])
        # TODO: KILL the s3backgrounddelete service
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
        logging.info("Last Modified time of object on re-upload %s", last_m_time_r)
        logging.info("Size of object on re-upload %s", size_r)
        if size_o == size_r:
            logging.info("The Size of objects are  of same size on first upload"
                         " %s,size on re-upload %s", size_o, size_r)
        else:
            logging.error("The size of objects are different"
                          " a: %s,b: %s", size_o, size_r)
        if last_m_time_o == last_m_time_r:
            logging.error("The time is same seems object re-upload failed")
        else:
            logging.info("The Last modified time"
                         " is different %s, %s", last_m_time_o, last_m_time_r)

    @pytest.mark.s3_ops
    @pytest.mark.s3_delete
    @pytest.mark.tags('TEST-29043')
    @CTFailOn(error_handler)
    def test_29043(self):
        """
        Test to verify deletion of objects when
        delayed delete option is enabled using simple object
        upload chunk.
        """
        self.log.info("STEP 1: Create bucket and "
                      "put object using jcloudclient %s",
                      self.test_file)
        self.s3_test_obj.create_bucket(self.bucket_name)
        self.create_put_object_jclient(self.bucket_name, self.test_file_path,
                                       option=1)
        self.log.info("STEP 2: Fetch Object details")
        result = self.s3_test_obj.object_info(self.bucket_name,
                                              self.test_file)
        obj_last_m_t = result[1]["LastModified"]
        obj_size = result[1]["ContentLength"]
        self.log.info("STEP 3: Re-Upload the same file")
        self.create_put_object_jclient(self.bucket_name,
                                       self.test_file_path,
                                       option="PUT")
        self.log.info("STEP 4: Fetch Object details")
        result = self.s3_test_obj.object_info(self.bucket_name,
                                              self.test_file)
        obj_last_m_t_r = result[1]["LastModified"]
        obj_size_r = result[1]["ContentLength"]
        self.log.info("STEP 5: Compare Object details "
                      "before and after re-upload")
        if obj_last_m_t < obj_last_m_t_r:
            self.log.info("The Object is overwrite and its"
                          " Last modified time is changed"
                          "new time %s and old time %s",
                          {obj_last_m_t_r}, {obj_last_m_t})
        if obj_size_r == obj_size:
            self.log.info("Obj size are same %s", {obj_size_r})
        self.log.info("STEP 6: Deleting the Chunk uploaded Objects")
        result = self.s3_test_obj.delete_object(self.bucket_name, self.test_file)
        assert_utils.assert_true(result[0], result[1])
        resp = self.s3_test_obj.object_list(self.bucket_name)
        if not resp:
            self.log.info("The given Object %s is deleted"
                          " from bucket %s", self.test_file,
                          self.bucket_name)

    @pytest.mark.s3_ops
    @pytest.mark.s3_delete
    @pytest.mark.tags('TEST-29159')
    @CTFailOn(error_handler)
    def test_29159(self):
        """
        This Function test the Object deletion
        when delayed delete is set to False
        """
        self.log.info("STEP 1: Testing when DELAYED DELETE is set to False\n")
        self.log.info(
            "S3_SERVER_OBJECT_DELAYED_DELETE value in s3config.yaml"
            " set to False.")
        status, response = S3H_OBJ.update_s3config(
            parameter="S3_SERVER_OBJECT_DELAYED_DELETE", value=False)
        assert_utils.assert_true(status, response)
        self.log.info("STEP 2: put object using jcloudclient %s",
                      self.test_file)
        self.create_put_object_jclient(self.bucket_name,
                                       self.test_file_path, 1)
        self.log.info("STEP 3: Fetch Object details")
        result = self.s3_test_obj.object_info(self.bucket_name,
                                              self.test_file)
        obj_last_m_t = result[1]["LastModified"]
        obj_size = result[1]["ContentLength"]
        self.log.info("STEP 4: Re-Upload the same file")
        self.create_put_object_jclient(self.bucket_name,
                                       self.test_file_path,
                                       "PUT")
        self.log.info("STEP 5: Fetch Object details")
        result = self.s3_test_obj.object_info(self.bucket_name,
                                              self.test_file)
        obj_last_m_t_r = result[1]["LastModified"]
        obj_size_r = result[1]["ContentLength"]
        self.log.info("STEP 6: Compare Object details"
                      " before and after re-upload")
        if obj_last_m_t < obj_last_m_t_r:
            self.log.info("The Object is overwrite"
                          " as its Last modified time is changed"
                          "new time %s and old time %s", {obj_last_m_t_r},
                          {obj_last_m_t})
        if obj_size_r == obj_size:
            self.log.info("Obj size are same %s", {obj_size_r})

    @pytest.mark.s3_ops
    @pytest.mark.s3_delete
    @pytest.mark.tags("TEST-28990")
    @CTFailOn(error_handler)
    def test_28990(self):
        """Verify background deletes using multiple objects delete operation"""
        self.log.info("Started: Verify background deletes using multiple objects delete operation")

        bucket_name = f"test-28990-bucket-{str(int(time.time()))}"
        clients = 5
        samples = 1000
        object_size = "2Mb"

        # Run s3bench workload of 1000 objects with cleanup option
        resp = s3bench.setup_s3bench()
        assert_utils.assert_true(resp, "Could not setup s3bench.")
        resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name, num_clients=clients,
                               num_sample=samples, obj_name_pref="test-object-",
                               obj_size=object_size, skip_cleanup=False, duration=None,
                               log_file_prefix="TEST-28990", end_point=S3_CFG["s3_url"],
                               validate_certs=S3_CFG["validate_certs"])
        self.log.info("Log Path %s", resp[1])
        assert_utils.assert_false(s3bench.check_log_file_error(resp[1]),
                                  f"S3bench workload for object size {object_size} failed."
                                  f"Please read log file {resp[1]}")

        # Check bucket is not accessible
        buckets = self.s3_test_obj.bucket_list()[1]
        assert_utils.assert_not_in(bucket_name, buckets, f"{bucket_name} bucket is present")

        self.log.info("Completed: Verify background deletes using multiple "
                      "objects delete operation")

    @pytest.mark.s3_ops
    @pytest.mark.s3_delete
    @pytest.mark.tags("TEST-28991")
    @CTFailOn(error_handler)
    def test_28991(self):
        """Verify background deletes when ran s3bench workload on multiple buckets"""
        self.log.info("Started: Verify background deletes when ran s3bench workload "
                      "on multiple buckets")

        # Run s3bench workload of 1000 objects parallel on 3 buckets with cleanup option
        resp = s3bench.setup_s3bench()
        assert_utils.assert_true(resp, "Could not setup s3bench.")
        pool = Pool(processes=3)
        buckets = [f"test-28991-bucket-{i}-{str(int(time.time()))}" for i in range(3)]
        end_point = S3_CFG["s3_url"]
        validate_certs = S3_CFG["validate_certs"]
        pool.starmap(s3bench.s3bench_workload,
                     [(end_point, buckets[0], "TEST-28991", "2Mb", 3, 400, ACCESS_KEY, SECRET_KEY,
                       validate_certs),
                      (end_point, buckets[1], "TEST-28991", "2Mb", 3, 400, ACCESS_KEY, SECRET_KEY,
                       validate_certs),
                      (end_point, buckets[2], "TEST-28991", "2Mb", 3, 400, ACCESS_KEY, SECRET_KEY,
                       validate_certs)])

        # Check if entries are getting deleted
        listed_buckets = self.s3_test_obj.bucket_list()[1]
        for bucket in buckets:
            assert_utils.assert_not_in(bucket, listed_buckets, f"{bucket} bucket is present")

        self.log.info("Completed: Verify background deletes when ran s3bench workload "
                      "on multiple buckets")

    @pytest.mark.s3_ops
    @pytest.mark.s3_delete
    @pytest.mark.tags("TEST-28992")
    @CTFailOn(error_handler)
    def test_28992(self):
        """Verify if deletion is successful post simple object delete"""
        self.log.info("Started: Verify if deletion is successful post simple object delete")

        # Create a bucket
        bucket_name = f"test-28992-bucket-{int(time.time())}"
        res = self.s3_test_obj.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Bucket %s is created", bucket_name)

        # Create a object
        self.log.info("Create file: %s", self.test_file_path)
        system_utils.create_file(self.test_file_path, 2, "/dev/urandom", '1M')

        # Upload a object
        object_name = self.test_file
        resp = self.s3_test_obj.put_object(bucket_name, object_name, self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])

        # Get LastModified time using head object
        res = self.s3_test_obj.object_info(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        old_last_modified = res[1]["LastModified"]

        # Re-upload same object
        time.sleep(5)
        resp = self.s3_test_obj.put_object(bucket_name, object_name, self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])

        # Get LastModified time using head object
        res = self.s3_test_obj.object_info(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        new_last_modified = res[1]["LastModified"]

        # Make sure the LastModified time is changed after re-uploading the object
        assert_utils.assert_true(new_last_modified > old_last_modified,
                                 f"LastModified for the old object {old_last_modified}. "
                                 f"LastModified for the new object is {new_last_modified}")

        # Deleting buckets & objects
        self.log.info("Deleting bucket %s", bucket_name)
        res = self.s3_test_obj.delete_bucket(bucket_name, True)
        assert_utils.assert_true(res[0], res[1])

        self.log.info("Completed: Verify if deletion is successful post simple object delete")

    @pytest.mark.s3_ops
    @pytest.mark.s3_delete
    @pytest.mark.tags("TEST-28993")
    @CTFailOn(error_handler)
    def test_28993(self):
        """Verify if deletion is successful post Multipart object delete"""
        self.log.info("Started: Verify if deletion is successful post Multipart object delete")

        test_config = DEL_CFG["test_28993"]

        # Create bucket
        bucket_name = f"test-28993-bucket-{int(time.time())}"
        res = self.s3_test_obj.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Created a bucket with name : %s", bucket_name)

        # Do multipart upload
        object_name = self.test_file
        self.s3_mp_test_obj.simple_multipart_upload(bucket_name,
                                                    object_name,
                                                    test_config["file_size"],
                                                    self.test_file_path,
                                                    test_config["total_parts"])

        # Delete object
        res = self.s3_test_obj.delete_object(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])

        # Verify object should not present after deletion
        try:
            response = self.s3_test_obj.object_info(bucket_name, object_name)
        except CTException as error:
            self.log.error("%s", error)
            assert_utils.assert_in("Not Found", error.message, error.message)
        else:
            self.log.error("Response = %s", response)
            assert_utils.assert_true(False, f"{object_name} object is still accessible "
                                            f"from bucket {bucket_name}")

        # Deleting buckets & objects
        self.log.info("Deleting bucket %s", bucket_name)
        res = self.s3_test_obj.delete_bucket(bucket_name, True)
        assert_utils.assert_true(res[0], res[1])

        self.log.info("Completed: Verify if deletion is successful post Multipart object delete")
