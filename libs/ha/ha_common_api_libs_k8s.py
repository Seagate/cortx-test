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

"""
HA common utility methods for API tests
"""
import logging
import os
import random
import time
from http import HTTPStatus

from commons import constants as common_const
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from config import CSM_REST_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_core_lib import RestClient
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.ha.ha_common_libs_k8s import HAK8s

LOGGER = logging.getLogger(__name__)


class HAK8sApiLibs:
    """
    This class contains common utility methods for HA related operations.
    """

    def __init__(self):
        self.system_health = SystemHealth()
        self.ha_obj = HAK8s()
        self.dir_path = common_const.K8S_SCRIPTS_PATH
        self.restapi = RestClient(CSM_REST_CFG)

    # pylint: disable-msg=too-many-locals
    @staticmethod
    def parallel_put_object(event, s3_test_obj, bkt_name: str, obj_name: str, output=None,
                            **kwargs):
        """
        Function to upload object
        Upload an object to a versioning enabled/suspended bucket and return list of dictionary of
        uploaded versions in parallel or non parallel.
        :param event: event to intimate thread about main thread operations
        :param s3_test_obj: Object of the s3 test lib
        :param bkt_name: Bucket name for calling PUT Object
        :param obj_name: Object name for calling PUT Object
        :param output: Output queue in which results should be put
        :keyword file_path: File path that can be used for PUT Object call
        :keyword count: Count for number of PUT object call
        :keyword chk_null_version: True, if 'null' version id is expected, else False
        :keyword background: Set to true if background function call
        :keyword is_unversioned: Set to true if object is uploaded to an unversioned bucket
        Can be used for setting up pre-existing objects before enabling/suspending bucket
        versioning
        :return: Tuple (bool, list)
        """
        chk_null_version = kwargs.get("chk_null_version", False)
        file_path = kwargs.get("file_path")
        count = kwargs.get("count", 1)
        is_unversioned = kwargs.get("is_unversioned", False)
        background = kwargs.get("background", False)
        pass_put_ver = list()
        fail_put_ver = list()
        for put in range(count):
            try:
                put_resp = s3_test_obj.put_object(bucket_name=bkt_name, object_name=obj_name,
                                                  file_path=file_path)
                if is_unversioned:
                    version_id = "null"
                else:
                    version_id = put_resp[1].get("VersionId", None)
                    etag = put_resp[1].get("ETag", None)
                    if chk_null_version:
                        if version_id != "null":
                            fail_put_ver.append({version_id: etag})
                    else:
                        if version_id is None:
                            fail_put_ver.append({version_id: etag})
                versions_dict = {version_id: put_resp[1]["ETag"]}
                pass_put_ver.append(versions_dict)
            except CTException as error:
                LOGGER.exception("Error in %s: %s", HAK8sApiLibs.parallel_put_object.__name__,
                                 error)
                if event.is_set():
                    continue
                fail_put_ver.append(put)
        if fail_put_ver and not background:
            return False, fail_put_ver
        return True, pass_put_ver if not background else output.put((pass_put_ver, fail_put_ver))

    @staticmethod
    def parallel_get_object(event, s3_ver_obj, bkt_name: str, obj_name: str, ver_etag: list,
                            **kwargs):
        """
        Function to GET a version of an object in parallel or non parallel and verify Etag for
        the same version object with expected PUT object response in ver_etag list.
        :param event: event to intimate thread about main thread operations
        :param s3_ver_obj: S3VersioningTestLib instance
        :param bkt_name: Target bucket for GET Object with VersionId call.
        :param obj_name: Target key for GET Object with VersionId call.
        :param ver_etag: Target list of dictionary of uploaded versions to be GET
        :keyword output: Output queue in which results should be put
        :keyword background: Set to true if background function call
        :return: Tuple (bool, list)
        """
        background = kwargs.get("background", False)
        output = kwargs.get("output", None)

        fail_get_ver = list()
        pass_get_ver = list()
        for v_etag in ver_etag:
            v_id = list(v_etag.keys())[0]
            etag = list(v_etag.values())[0]
            try:
                get_resp = s3_ver_obj.get_object_version(bucket=bkt_name, key=obj_name,
                                                         version_id=v_id)
                if get_resp[1]["VersionId"] != v_id or get_resp[1]["ETag"] != etag:
                    failed = {v_id: [get_resp[1]["VersionId"], get_resp[1]["ETag"]]}
                    fail_get_ver.append(failed)
                else:
                    pass_get_ver.append(v_etag)
            except CTException as error:
                LOGGER.exception("Error in %s: %s", HAK8sApiLibs.parallel_get_object.__name__,
                                 error)
                if event.is_set():
                    continue
                fail_get_ver.append(v_etag)
        if fail_get_ver and not background:
            return False, fail_get_ver
        return True, pass_get_ver if not background else output.put((pass_get_ver, fail_get_ver))

    @staticmethod
    def list_verify_version(s3_ver_obj, bucket_name: str, expected_versions: dict):
        """
        Function to List all the versions of bucket objects and verify the output with expected
        version etag values
        :param s3_ver_obj: S3VersioningTestLib instance
        :param bucket_name: Target bucket for List Object version
        :param expected_versions: Target list of dictionary of uploaded versions to be List and
        verify
        :return: Tuple (bool, str)
        """
        resp = s3_ver_obj.list_object_versions(bucket_name)
        v_etag = list()
        list_version = resp[1]["Versions"]
        for v_e in list_version:
            versions_dict = {v_e["VersionId"]: v_e["ETag"]}
            v_etag.append(versions_dict)
        for v_e in v_etag:
            if v_e not in expected_versions:
                return False, "Fetched list of VersionId-Etag is not matching with Expected"
        return True, "Fetched list of VersionId-Etag is as Expected"

    def crt_bkt_put_obj_enbl_ver(self, event, s3_test, bkt, obj, **kwargs):
        """
        Function will create a new bucket and upload an new object on un-versioned bucket.
        If enable_ver is set to true, it will enable versioning on given bucket.
        :param event: event to intimate thread about main thread operations
        :param s3_test: Object of the s3 test lib
        :param bkt: Bucket name for calling PUT Object
        :param obj: Object name for calling PUT Object
        :keyword file_path: File path that can be used for PUT Object call
        :keyword count: Count for number of PUT object call
        :keyword chk_null_version: True, if 'null' version id is expected, else False
        :keyword background: Set to true if background function call
        :keyword is_unversioned: Set to true if object is uploaded to an unversioned bucket
        :keyword enable_ver: Set to true if want to enable versioning on given bucket
        Can be used for setting up pre-existing objects before enabling/suspending bucket
        versioning
        :kwargs s3_ver: S3VersioningTestLib instance
        :return: Tuple (bool, response)
        """
        chk_null_version = kwargs.get("chk_null_version", False)
        file_path = kwargs.get("file_path")
        f_size = kwargs.get("f_size", str(HA_CFG["5gb_mpu_data"]["file_size_512M"]) + "M")
        f_count = kwargs.get("f_count", 1)
        put_count = kwargs.get("put_count", 1)
        is_unversioned = kwargs.get("is_unversioned", False)
        enable_ver = kwargs.get("enable_ver", False)
        LOGGER.info("Create bucket with %s name.", bkt)
        resp = s3_test.create_bucket(bkt)
        if not resp[1]:
            return resp
        LOGGER.info("Created bucket with %s name.", bkt)
        LOGGER.info("Creating file %s.", file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        system_utils.create_file(file_path, b_size=f_size, count=f_count)
        args = {'chk_null_version': chk_null_version, 'is_unversioned': is_unversioned,
                'file_path': file_path, 'count': put_count}
        LOGGER.info("Upload object %s before enabling versioning", obj)
        put_resp = self.parallel_put_object(event, s3_test, bkt, obj, **args)
        if not put_resp[0]:
            return False, f"Upload Object failed {put_resp[1]}"
        LOGGER.info("Successfully uploaded object %s", obj)
        if enable_ver:
            try:
                s3_ver = kwargs.get("s3_ver")
            except KeyError:
                return False, "Required s3_ver argument is not passed"
            LOGGER.info("Enable versioning on %s.", bkt)
            resp = s3_ver.put_bucket_versioning(bucket_name=bkt)
            if not resp[0]:
                return False, f"Enabling versioning failed with {resp[1]}"
            LOGGER.info("Enabled versioning on %s.", bkt)
        return put_resp

    # pylint: disable=too-many-arguments
    def object_overwrite_dnld(self, s3_test_obj, s3_data, iteration, random_size, event=None,
                              queue=None, background=False):
        """
        Function to create bucket, put object and overwrite existing object
        :param s3_test_obj: Object of s3 test lib
        :param s3_data: Dict that contains bucket and object info
        ({self.bucket_name: [self.object_name, file_size]})
        :param iteration: Number of iterations for overwrite
        :param random_size: Flag to select random size of object
        :param event: Event for background IOs
        :param queue: Queue to fill output in case of background IOs
        :param background: Flag to start background process
        :return: (bool, dict)
        """
        checksums = dict()
        fail_count = 0
        exp_fail_count = 0
        test_dir_path = os.path.join(TEST_DATA_FOLDER, "HAOverWrite")
        if not os.path.isdir(test_dir_path):
            LOGGER.debug("Creating file path %s", test_dir_path)
            system_utils.make_dirs(test_dir_path)

        resp = s3_test_obj.bucket_list()[1]
        for bkt, value in s3_data.items():
            object_name = value[0]
            object_size = value[1]
            if bkt not in resp:
                LOGGER.info("Creating a bucket with name %s and uploading object of size %s MB",
                            bkt, object_size)
                file_path = os.path.join(test_dir_path, f"{bkt}.txt")
                _ = s3_test_obj.create_bucket_put_object(bkt, object_name, file_path, object_size)
                LOGGER.info("Created a bucket with name %s and uploaded object %s of size %s MB",
                            bkt, object_name, object_size)
                system_utils.remove_file(file_path)

        LOGGER.info("Total Iteration : %s", iteration)
        for bucket_name, value in s3_data.items():
            object_name = value[0]
            object_size = value[1]
            LOGGER.info("Bucket Name : %s", bucket_name)
            LOGGER.info("Object Name : %s", object_name)
            LOGGER.info("Max Object size : %s MB", object_size)
            for i_i in range(iteration):
                loop = i_i + 1
                LOGGER.info("Iteration : %s", loop)
                file_size = random.SystemRandom().randint(0, object_size) if random_size \
                    else object_size
                try:
                    upload_path = os.path.join(test_dir_path, f"{object_name}_upload.txt")
                    LOGGER.info("Creating a file with name %s", object_name)
                    system_utils.create_file(upload_path, file_size, "/dev/urandom", '1M')
                    LOGGER.info("Retrieving checksum of file %s", upload_path)
                    up_checksum = self.ha_obj.cal_compare_checksum([upload_path], compare=False)[0]
                    LOGGER.info("Uploading object (Overwriting)...")
                    _ = s3_test_obj.put_object(bucket_name, object_name, upload_path)

                    LOGGER.info("Downloading object...")
                    download_path = os.path.join(test_dir_path, f"{object_name}_download.txt")
                    _ = s3_test_obj.object_download(bucket_name, object_name, download_path)
                    dnld_checksum = self.ha_obj.cal_compare_checksum([download_path],
                                                                     compare=False)[0]
                    checksums[f"{bucket_name}_{loop}"] = [up_checksum, dnld_checksum]
                except CTException as error:
                    if event.is_set:
                        LOGGER.error("Event is set, overwrite/object download failure is expected. "
                                     "Error: %s", error)
                        exp_fail_count += 1
                    else:
                        LOGGER.error("Event is cleared, Overwrite failed or Object download "
                                     "failed. \nError: %s", error)
                        fail_count += 1
                finally:
                    system_utils.cleanup_dir(test_dir_path)
        LOGGER.debug("Fail count is : %s", fail_count)
        return not fail_count, checksums, exp_fail_count if not background else \
            queue.put((not fail_count, checksums, exp_fail_count))

    def create_iam_user_with_header(self, i_d, header):
        """
        Function create IAM user with give header info.
        :param i_d: Int count number for IAM user name creation
        :param header: Existing header to use for IAM user creation post request
        :return: None if IAM user REST req fails or Dict response for IAM user successful creation
        """
        user = None
        payload = {}
        name = f"ha_iam_{i_d}_{time.perf_counter_ns()}"
        payload.update({"uid": name})
        payload.update({"display_name": name})
        LOGGER.info("Creating IAM user request....")
        endpoint = CSM_REST_CFG["s3_iam_user_endpoint"]
        resp = self.restapi.rest_call("post", endpoint=endpoint, json_dict=payload,
                                      headers=header)
        LOGGER.info("IAM user request successfully sent...")
        if resp.status_code == HTTPStatus.CREATED:
            resp = resp.json()
            user = dict()
            user.update({resp["keys"][0]["user"]: {
                "user_name": resp["keys"][0]["user"],
                "password": S3_CFG["CliConfig"]["s3_account"]["password"],
                "accesskey": resp["keys"][0]["access_key"],
                "secretkey": resp["keys"][0]["secret_key"]}})
        return user

    def delete_iam_user_with_header(self, user, header):
        """
        Function delete IAM user with give header info.
        :param user: IAM user name to be deleted
        :param header: Existing header to use for IAM user delete request
        :return: Tuple
        """
        endpoint = CSM_REST_CFG["s3_iam_user_endpoint"] + "/" + user
        LOGGER.info("Sending Delete IAM user request...")
        response = self.restapi.rest_call("delete", endpoint=endpoint, headers=header)
        if response.status_code == HTTPStatus.OK:
            return True, "Deleted user successfully"
        LOGGER.debug(response.json())
        return False, response.json()["message"]
