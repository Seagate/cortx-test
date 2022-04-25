#!/usr/bin/python # pylint: disable=C0302
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
#

"""
HA test suite for Cluster Shutdown: Immediate.
"""

import logging
import os
import random
import threading
import time
from http import HTTPStatus
from multiprocessing import Queue
from time import perf_counter_ns

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import create_file
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import remove_dirs
from commons.utils.system_utils import remove_file
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
class TestClusterShutdownStart:
    """
    Test suite for Cluster shutdown: Immediate.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        cls.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.username = []
        cls.password = []
        cls.host_master_list = []
        cls.node_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.restored = True
        cls.s3_clean = {}
        cls.test_prefix = cls.s3bench_cleanup = cls.random_time = cls.s3ios = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.multipart_obj_path = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = random.SystemRandom()

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                cls.host_master_list.append(cls.host)
                cls.node_master_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
            else:
                cls.host_worker_list.append(cls.host)
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        cls.rest_obj = S3AccountOperations()
        cls.rest_hlt_obj = SystemHealth()
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.test_file = "ha-mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.restored = True
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        self.s3acc_name = "{}_{}".format("ha_s3acc", int(perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.bucket_name = "ha-mp-bkt-{}".format(self.random_time)
        self.object_name = "ha-mp-obj-{}".format(self.random_time)
        if not os.path.exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Done: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restored:
            LOGGER.info("Cleanup: Check cluster status and start it if not up.")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            if not resp[0]:
                LOGGER.debug("Cluster status: %s", resp)
                resp = self.ha_obj.restart_cluster(self.node_master_list[0])
                assert_utils.assert_true(resp[0], resp[1])
            if self.s3_clean:
                LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
                resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
                assert_utils.assert_true(resp[0], resp[1])

            # Check if s3bench objects cleanup is required
            if self.s3bench_cleanup:
                for user_info in self.s3bench_cleanup.values():
                    resp = self.ha_obj.ha_s3_workload_operation(
                        s3userinfo=user_info, log_prefix=self.test_prefix,
                        skipwrite=True, skipread=True)
                    assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info("Cleanup: Deleted s3 objects and buckets.")

            if os.path.exists(self.test_dir_path):
                remove_dirs(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29301")
    @CTFailOn(error_handler)
    def test_cluster_shutdown_start(self):
        """
        This test tests the cluster shutdown and start functionality.
        """
        LOGGER.info(
            "STARTED: Test to verify cluster shutdown and restart functionality.")

        LOGGER.info("Step 1: Check the status of the pods running in cluster.")

        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: All pods are running.")

        LOGGER.info("Step 2: Start IOs (create s3 acc, buckets and upload objects).")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29301'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: IOs are completed successfully.")

        LOGGER.info("Step 3: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(operation="shutdown_signal",
                                                          resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster shutdown signal is successful.")

        LOGGER.info("Step 4: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Cluster restarted fine and all Pods online.")

        LOGGER.info("Step 5: Check DI for IOs run before restart.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Verified DI for IOs run before restart.")

        LOGGER.info("Step 6: Create new S3 account and perform IOs.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29301-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: IOs completed successfully with new S3 account.")

        LOGGER.info(
            "Completed: Test to verify cluster shutdown and restart functionality.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29468")
    @CTFailOn(error_handler)
    def test_cluster_restart_multiple(self):
        """
        This test tests the cluster shutdown and start functionality, in loop
        to check the consistency.
        """
        LOGGER.info(
            "STARTED: Test to verify cluster shutdown and restart functionality in loop.")

        LOGGER.info("Step 1: Check the status of the pods running in cluster.")
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: All pods are running.")
        wr_bucket = self.system_random.randrange(5, 20, 5)
        event = threading.Event()
        wr_output = Queue()
        del_output = Queue()
        rd_output = Queue()

        loop_count = HA_CFG["common_params"]["loop_count"]
        LOGGER.info("Create s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"][
                                                    "password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-29468'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)
        for loop in range(1, loop_count):
            LOGGER.info("Checking cluster restart for %s count", loop)

            LOGGER.info("Step 2: Create %s buckets and perform WRITEs with variable size objects.",
                        wr_bucket)

            LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
            args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                    'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

            self.ha_obj.put_get_delete(event, s3_test_obj, **args)
            wr_resp = ()
            while len(wr_resp) != 3:
                wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            s3_data = wr_resp[0]  # Contains s3 data for passed buckets
            buckets = s3_test_obj.bucket_list()[1]
            assert_utils.assert_equal(len(buckets), wr_bucket,
                                      f"Failed to create {wr_bucket} number "
                                      f"of buckets. Created {len(buckets)} "
                                      f"number of buckets")
            LOGGER.info("Step 2: Sucessfully created %s buckets & "
                        "perform WRITEs with variable size objects.", wr_bucket)

            LOGGER.info("Step 3: Send the cluster shutdown signal through CSM REST.")
            resp = self.rest_hlt_obj.cluster_operation_signal(operation="shutdown_signal",
                                                              resource="cluster")
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3: Cluster shutdown signal is successful.")

            LOGGER.info("Step 4: Restart the cluster and check cluster status.")
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 4: Cluster restarted fine and all Pods online.")

            LOGGER.info("Step 5: Verify READs and DI check for buckets: %s", wr_bucket)

            args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                    'skipput': True, 'skipdel': True, 's3_data': s3_data, 'di_check': True,
                    'output': rd_output}
            self.ha_obj.put_get_delete(event, s3_test_obj, **args)
            rd_resp = ()
            while len(rd_resp) != 4:
                rd_resp = rd_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            event_bkt_get = rd_resp[0]
            fail_bkt_get = rd_resp[1]
            event_di_bkt = rd_resp[2]
            fail_di_bkt = rd_resp[3]

            # Above four lists are expected to be empty as all pass expected
            assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt) or len(event_bkt_get) or
                                      len(event_di_bkt), "Expected pass in read and di check "
                                                         "operations. Found failures in READ: "
                                                         f"{fail_bkt_get} {event_bkt_get}"
                                                         f"or DI_CHECK: {fail_di_bkt}"
                                                         f" {event_di_bkt}")
            LOGGER.info("Step 5: Performed READs and verified DI on the written data for %s "
                        "buckets", wr_bucket)

            LOGGER.info("Step 6: Deleting %s buckets.", wr_bucket)
            args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                    'skipput': True, 'skipget': True, 'output': del_output}
            self.ha_obj.put_get_delete(event, s3_test_obj, **args)
            del_resp = ()
            while len(del_resp) != 2:
                del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            event_del_bkt = del_resp[0]
            fail_del_bkt = del_resp[1]
            assert_utils.assert_false(len(event_del_bkt) or len(fail_del_bkt),
                                      f"Failed to delete: {event_del_bkt} or {fail_del_bkt}")
            LOGGER.info("Cleaning up s3 user data")
            resp = s3_test_obj.bucket_list()[1]
            assert_utils.assert_equal(len(resp), 0, f"Failed to delete {wr_bucket} buckets")
            LOGGER.info("Step 6: Successfully deleted %s buckets.", wr_bucket)

            LOGGER.info("Step 7: Create new S3 account and perform IOs.")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-29468-1'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 7: IOs completed successfully with new S3 account.")
            LOGGER.info("Cluster restart was successful for %s count", loop)

        LOGGER.info(
            "Completed: Test to verify cluster shutdown and restart functionality in loop.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="F-20C not completely supported with RGW.")
    @pytest.mark.tags("TEST-29472")
    @CTFailOn(error_handler)
    def test_mpu_with_cluster_restart_29472(self):
        """
        This test tests multipart upload and download with cluster restart
        """
        LOGGER.info(
            "STARTED: Test to verify multipart upload and download with cluster restart")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)

        LOGGER.info("Step 1: Do multipart upload for 5GB object")
        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.debug("Response: %s", resp)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=self.bucket_name,
                                                         object_name=self.object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        upload_checksum = str(resp[2])

        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(operation="shutdown_signal",
                                                          resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Cluster shutdown signal sent successfully.")

        LOGGER.info("Step 3: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster restarted successfully and all Pods are online.")

        LOGGER.info("Step 4: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 4: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        remove_file(self.multipart_obj_path)
        remove_file(download_path)

        LOGGER.info("Step 5: Create new bucket and multipart upload and then download 5GB object")
        bucket_name = "mp-bkt-{}".format(self.random_time)
        object_name = "mp-obj-{}".format(self.random_time)
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=bucket_name,
                                                         object_name=object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        upload_checksum1 = resp[2]

        resp = s3_test_obj.object_download(bucket_name, object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum1 = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                              compare=False)[0]
        assert_utils.assert_equal(upload_checksum1, download_checksum1,
                                  f"Failed to match checksum: {upload_checksum1},"
                                  f" {download_checksum1}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum1, download_checksum1)
        LOGGER.info("Step 5: Successfully created bucket and did multipart upload and download "
                    "with 5GB object")

        LOGGER.info("ENDED: Test to verify multipart upload and download with cluster restart")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="F-20C not completely supported for RGW.")
    @pytest.mark.tags("TEST-29474")
    @CTFailOn(error_handler)
    def test_partial_mpu_bfr_aftr_clstr_rstrt_29474(self):
        """
        This test tests partial multipart upload before and after cluster restart
        """
        LOGGER.info(
            "STARTED: Test to verify partial multipart upload before and after cluster restart")

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = random.sample(range(1, total_parts+1), total_parts//2)
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        if os.path.exists(self.multipart_obj_path):
            os.remove(self.multipart_obj_path)
        create_file(self.multipart_obj_path, file_size)

        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]

        LOGGER.info("Step 1: Start multipart upload for 5GB object in multiple parts and complete "
                    "partially")
        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        s3_mp_test_obj = S3MultipartTestLib(access_key=access_key, secret_key=secret_key,
                                            endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=part_numbers,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=self.multipart_obj_path)
        mpu_id = resp[1]
        object_path = resp[2]
        parts_etag1 = resp[3]
        assert_utils.assert_true(resp[0], f"Failed to upload parts. Response: {resp}")
        LOGGER.info("Step 1: Successfully completed partial multipart upload")

        LOGGER.info("Step 2: Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(part_numbers, part_n["PartNumber"])
        LOGGER.info("Step 2: Listed parts of partial multipart upload: %s", res[1])

        LOGGER.info("Step 3: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(operation="shutdown_signal",
                                                          resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster shutdown signal sent successfully.")

        LOGGER.info("Step 4: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Cluster restarted successfully and all Pods are online.")

        LOGGER.info("Step 5: Upload remaining parts")
        remaining_parts = list(filter(lambda i: i not in part_numbers,
                                      list(range(1, total_parts+1))))

        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=remaining_parts,
                                                    remaining_upload=True, mpu_id=mpu_id,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=object_path)

        assert_utils.assert_true(resp[0], f"Failed to upload parts {resp[1]}")
        parts_etag2 = resp[3]
        LOGGER.info("Step 5: Successfully uploaded remaining parts")

        etag_list = parts_etag1 + parts_etag2
        parts_etag = sorted(etag_list, key=lambda d: d['PartNumber'])

        LOGGER.info("Step 6: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 6: Listed parts of multipart upload: %s", res[1])
        LOGGER.info("Step 7: Completing multipart upload")
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, self.bucket_name,
                                                       self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        if self.object_name not in res[1]:
            assert_utils.assert_true(False, res)
        LOGGER.info("Step 7: Multipart upload completed")

        LOGGER.info("Step 8: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 8: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 9: Create multiple buckets and run IOs")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29474'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify partial multipart upload before and after cluster "
                    "restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29469")
    @CTFailOn(error_handler)
    def test_reads_after_cluster_restart(self):
        """
        This test verifies READs after cluster restart on WRITEs before shutdown
        """
        LOGGER.info("Started: Test to check READs after cluster restart on WRITEs before shutdown.")
        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29469'
        self.s3_clean = self.s3bench_cleanup = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipread=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")
        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 3: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster restarted fine and all Pods online.")
        LOGGER.info("Step 4: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipwrite=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed READs and verified DI on the written data")

        LOGGER.info(
            "Completed: Test to check READs after cluster restart on WRITEs before shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29470")
    @CTFailOn(error_handler)
    def test_write_after_cluster_restart(self):
        """
        This test verifies WRITEs after cluster restart
        """
        LOGGER.info("Started: Test to check WRITEs after cluster restart.")
        LOGGER.info("STEP 1: Perform IOs with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29470'
        self.s3_clean = self.s3bench_cleanup = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed IOs with variable sizes objects.")
        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 3: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster restarted fine and all Pods online.")
        LOGGER.info("STEP 4: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB). "
                    "Verify READs and DI on the written data.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29470-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs with variable sizes objects."
                    "Verified READs and verified DI on the written data.")

        LOGGER.info("Completed: Test to check WRITEs after cluster restart.")

    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-29473")
    @CTFailOn(error_handler)
    def test_mpu_during_cluster_restart_29473(self):
        """
        This test tests multipart upload and download during cluster restart
        """
        LOGGER.info("STARTED: Test to verify multipart upload and download during cluster restart")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = list(range(1, total_parts+1))
        random.shuffle(part_numbers)
        output = Queue()
        parts_etag = list()
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        event = threading.Event()  # Event to be used to send intimation of cluster restart

        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        s3_mp_test_obj = S3MultipartTestLib(access_key=access_key, secret_key=secret_key,
                                            endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Start multipart upload of 5GB object in background")
        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'file_size': file_size, 'total_parts': total_parts,
                'multipart_obj_path': self.multipart_obj_path, 'part_numbers': part_numbers,
                'parts_etag': parts_etag, 'output': output}
        thread = threading.Thread(target=self.ha_obj.start_random_mpu, args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Started multipart upload of 5GB object in background")
        time.sleep(HA_CFG["common_params"]["90sec_delay"])

        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(operation="shutdown_signal",
                                                          resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Cluster shutdown signal sent successfully.")

        LOGGER.info("Step 3: Restart the cluster and check cluster status.")
        event.set()
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster restarted successfully and all Pods are online.")

        thread.join()
        responses = tuple()
        while len(responses) < 4:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])

        if not responses:
            assert_utils.assert_true(False, "Background process failed to do multipart upload")

        exp_failed_parts = responses[0]
        failed_parts = responses[1]
        parts_etag = responses[2]
        mpu_id = responses[3]
        LOGGER.debug("Responses received from background process:\nexp_failed_parts: "
                     "%s\nfailed_parts: %s\nparts_etag: %s\nmpu_id: %s", exp_failed_parts,
                     failed_parts, parts_etag, mpu_id)
        if len(exp_failed_parts) == 0 and len(failed_parts) == 0:
            LOGGER.info("All the parts are uploaded successfully")
        elif failed_parts:
            assert_utils.assert_true(False, "Failed to upload parts when cluster was in good "
                                            f"state. Failed parts: {failed_parts}")
        elif exp_failed_parts:
            LOGGER.info("Step 4: Upload remaining parts")
            resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                        bucket_name=self.bucket_name,
                                                        object_name=self.object_name,
                                                        part_numbers=exp_failed_parts,
                                                        remaining_upload=True,
                                                        multipart_obj_size=file_size,
                                                        total_parts=total_parts,
                                                        multipart_obj_path=self.multipart_obj_path,
                                                        mpu_id=mpu_id)

            assert_utils.assert_true(resp[0], f"Failed to upload parts {resp[1]}")
            LOGGER.info("Step 4: Successfully uploaded remaining parts")

        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]

        parts_etag = sorted(parts_etag, key=lambda d: d['PartNumber'])
        LOGGER.info("Step 5: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 5: Listed parts of multipart upload: %s", res[1])

        LOGGER.info("Step 6: Completing multipart upload")
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, self.bucket_name,
                                                       self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, res[1], res)
        LOGGER.info("Step 6: Multipart upload completed")

        LOGGER.info("Step 7: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 7: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 8: Create multiple buckets and run IOs")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29473-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify multipart upload and download during cluster restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="copy object not available in RGW yet")
    @pytest.mark.tags("TEST-29475")
    @CTFailOn(error_handler)
    def test_copy_obj_bfr_clstr_rstrt_29475(self):
        """
        This test tests copy object to other buckets before cluster shutdown and download and
        verify checksum after cluster starts.
        """
        LOGGER.info("STARTED: Test to verify copy object to other buckets before cluster shutdown "
                    "and download and verify checksum after cluster starts.")
        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        event = threading.Event()
        bkt_obj_dict = dict()
        for i in range(bkt_cnt):
            bkt_obj_dict["ha-bkt{}-{}".format(i, self.random_time)] = \
                "ha-obj{}-{}".format(i, self.random_time)

        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Create multiple buckets and upload object to %s and copy to other "
                    "buckets", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: Successfully Created multiple buckets and uploaded object to %s "
                    "and copied to other buckets", self.bucket_name)

        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(operation="shutdown_signal",
                                                          resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Cluster shutdown signal sent successfully.")

        LOGGER.info("Step 3: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster restarted successfully and all Pods are online.")

        LOGGER.info("Step 4: Download the uploaded object and verify checksum")
        for k, v in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=k, key=v)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {v} of bucket {k}. Put and Get "
                                                          "Etag mismatch")

        LOGGER.info("Step 4: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 5: Create s3 account and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29475-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify copy object to other buckets before cluster shutdown "
                    "and download and verify checksum after cluster starts.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-29476")
    @CTFailOn(error_handler)
    def test_copy_obj_during_clstr_rstrt_29476(self):
        """
        This test tests copy object to other buckets during cluster restart
        """
        LOGGER.info("STARTED: Test to verify copy object to other buckets during cluster restart")
        event = threading.Event()
        bkt_obj_dict = dict()
        bkt_obj_dict["ha-bkt-{}".format(self.random_time)] = "ha-obj-{}".format(self.random_time)
        output = Queue()

        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Create multiple buckets and upload object to %s and copy to other "
                    "buckets", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: Successfully Created multiple buckets and uploaded object to %s "
                    "and copied to other buckets", self.bucket_name)

        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(operation="shutdown_signal",
                                                          resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Cluster shutdown signal sent successfully.")

        bkt_obj_dict1 = dict()
        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_multi"]
        for cnt in range(bkt_cnt):
            rd_time = perf_counter_ns()
            s3_test_obj.create_bucket(f"ha-bkt{cnt}-{rd_time}")
            bkt_obj_dict1[f"ha-bkt{cnt}-{rd_time}"] = f"ha-obj{cnt}-{rd_time}"
        LOGGER.debug("New bucket-object dict: %s", bkt_obj_dict1)
        bkt_obj_dict.update(bkt_obj_dict1)
        LOGGER.info("Step 3: Copy object from %s to other buckets in background", self.bucket_name)
        args = {'s3_test_obj': s3_test_obj, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'bkt_obj_dict': bkt_obj_dict1, 'output': output,
                'file_path': self.multipart_obj_path, 'background': True, 'bkt_op': False,
                'put_etag': put_etag}
        thread = threading.Thread(target=self.ha_obj.create_bucket_copy_obj, args=(event,),
                                  kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 3: Successfully started background process for copy object")
        # While loop to sync this operation with background thread to achieve expected scenario
        LOGGER.info("Waiting for creation of %s buckets", bkt_cnt)
        bkt_list = list()
        timeout = time.time() + 60 * 3
        while len(bkt_list) < bkt_cnt:
            time.sleep(HA_CFG["common_params"]["20sec_delay"])
            bkt_list = s3_test_obj.bucket_list()[1]
            if timeout < time.time():
                LOGGER.error("Bucket creation is taking longer than 3 mins")
                assert_utils.assert_true(False, "Please check background process logs")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])

        LOGGER.info("Step 4: Restart the cluster and check cluster status.")
        event.set()
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Cluster restarted successfully and all Pods are online.")

        event.clear()
        LOGGER.info("Step 5: Checking response from background process of copy object")
        thread.join()
        responses = tuple()
        while len(responses) < 3:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])

        if not responses:
            assert_utils.assert_true(False, "Background process failed to do copy object")

        put_etag = responses[0]
        exp_fail_bkt_obj_dict = responses[1]
        failed_bkts = responses[2]
        LOGGER.debug("Responses received from background process:\nput_etag: "
                     "%s\nexp_fail_bkt_obj_dict: %s\nfailed_bkts: %s", put_etag,
                     exp_fail_bkt_obj_dict, failed_bkts)
        if len(exp_fail_bkt_obj_dict) == 0 and len(failed_bkts) == 0:
            LOGGER.info("Copy object operation for all the buckets completed successfully. ")
        elif failed_bkts:
            assert_utils.assert_true(False, "Failed to do copy object when cluster was in degraded "
                                            f"state. Failed buckets: {failed_bkts}")
        elif exp_fail_bkt_obj_dict:
            LOGGER.info("Step 5.1: Retrying copy object to buckets %s",
                        list(exp_fail_bkt_obj_dict.keys()))
            resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                      bucket_name=self.bucket_name,
                                                      object_name=self.object_name,
                                                      bkt_obj_dict=exp_fail_bkt_obj_dict,
                                                      bkt_op=False, put_etag=put_etag)
            assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
            put_etag = resp[1]
        LOGGER.info("Step 5: Successfully checked responses from background process.")

        LOGGER.info("Step 6: Download the uploaded object and verify checksum")
        for k, v in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=k, key=v)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {v} of bucket {k}. Put and Get "
                                                          "Etag mismatch")
        LOGGER.info("Step 6: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 7: Create s3 account and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29476-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify copy object to other buckets during cluster restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29479")
    @CTFailOn(error_handler)
    def test_cluster_restart_without_signal(self):
        """
        This test tests the cluster restart functionality without sending the shutdown signal.
        """
        LOGGER.info(
            "STARTED: Test to verify cluster restart functionality without sending the "
            "shutdown signal.")

        LOGGER.info("Step 1: Check the status of the pods running in cluster.")
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: All pods are running.")

        LOGGER.info(
            "Step 2: Start IOs (create s3 acc, buckets and upload objects).")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29479'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: IOs are completed successfully.")

        LOGGER.info(
            "Step 3: Restart the cluster and check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info(
            "Step 3: Cluster restarted fine and all Pods online.")

        LOGGER.info("Step 4: Check DI for IOs run before restart.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Verified DI for IOs run before restart.")

        LOGGER.info("Step 5: Create new S3 account and perform IOs.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29479-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: IOs running successfully with new S3 account.")

        LOGGER.info(
            "Completed: Test to verify cluster restart functionality without sending the"
            "shutdown signal.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29480")
    @CTFailOn(error_handler)
    def test_cluster_start_before_shutdown(self):
        """
        This test tests the cluster behaviour when cluster restarted before shutdown completes.
        (negative scenario)
        """
        LOGGER.info(
            "STARTED: Test to check cluster stability when cluster start is initiated before"
            "shutdown completes.")

        LOGGER.info("Step 1: Check the status of the pods running in cluster.")
        resp = self.ha_obj.check_pod_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: All pods are running.")

        LOGGER.info("Step 2: Start IOs (create s3 acc, buckets and upload objects).")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29480'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: IOs are completed successfully.")

        LOGGER.info("Step 3: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(operation="shutdown_signal",
                                                          resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster shutdown signal is successful.")

        LOGGER.info("Step 4: Shutdown the cluster and start it back before shutdown completes.")
        thread = threading.Thread(target=self.ha_obj.cortx_stop_cluster,
                                  args=(self.node_master_list[0],))
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Cluster Stop started and waiting for %s seconds.",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Check the cluster status has failures after stop cluster")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], "Cluster has not started shutdown yet.")
        LOGGER.info("Checked the cluster status has failures after stop cluster")
        LOGGER.info("Cluster start started.")
        resp = self.ha_obj.cortx_start_cluster(self.node_master_list[0])
        LOGGER.info("Response for cluster start: %s", resp)
        thread.join(HA_CFG["common_params"]["thread_join_delay"])
        LOGGER.info("Step 4: Shutdown and restart completed.")

        LOGGER.info("Step 5: Check the cluster status and start the cluster "
                    "in case its still down.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            LOGGER.info("Cluster not in good state, trying to restart it.")
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster is up and running.")
        LOGGER.info("Step 5: Cluster is back online.")

        LOGGER.info("Step 6: Check DI for IOs run before restart.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Verified DI for IOs run before restart.")

        LOGGER.info("Step 7: Create new S3 account and perform IOs.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29480-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: IOs running successfully with new S3 account.")

        LOGGER.info("Completed: Test to check cluster stability when cluster start is initiated "
                    "before shutdown completes.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29471")
    @CTFailOn(error_handler)
    def test_delete_after_cluster_restart(self):
        """
        This test verifies DELETE IOs operation on bucket objects after cluster restart on
        bucket objects Created before cluster restart.
        """
        LOGGER.info("Started: Test to check DELETEs after cluster restart.")

        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
        event = threading.Event()
        wr_output = Queue()
        del_output = Queue()
        rd_output = Queue()

        LOGGER.info("Step 1: Create %s buckets and run IOs on variable size objects.", wr_bucket)
        LOGGER.info("Create s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-29471'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)

        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           f"number of buckets")
        LOGGER.info("Perform READs and Verify on %s buckets", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 's3_data': s3_data,
                'di_check': True, 'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = ()
        while len(rd_resp) != 4:
            rd_resp = rd_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        event_bkt_get = rd_resp[0]
        fail_bkt_get = rd_resp[1]
        event_di_bkt = rd_resp[2]
        fail_di_bkt = rd_resp[3]
        # Above four lists are expected to be empty as all pass expected
        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt) or len(event_bkt_get) or
                                  len(event_di_bkt), "Expected pass in read and di check "
                                                     "operations. Found failures in READ: "
                                                     f"{fail_bkt_get} {event_bkt_get}"
                                                     f"or DI_CHECK: {fail_di_bkt} {event_di_bkt}")
        LOGGER.info("Step 1: Sucessfully created %s buckets & ran IOs on variable size objects.",
                    wr_bucket)
        LOGGER.info("Step 2: Verify %s has %s buckets created", self.s3acc_name,
                    wr_bucket)
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(wr_bucket, len(resp[1]), resp)
        LOGGER.info("Step 2: Verified %s has %s buckets created", self.s3acc_name,
                    wr_bucket)
        r_buck = wr_bucket - del_bucket
        LOGGER.info("Step 3: Verify DI and DELETE %s buckets and verify remaining count is %s ",
                    del_bucket, r_buck)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'bkts_to_del': del_bucket, 'output': del_output,
                'di_check': True, 's3_data': s3_data}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        while del_output.qsize() != 2:
            LOGGER.info("Waiting for all items to get populated in queue")
            time.sleep(HA_CFG["common_params"]["60sec_delay"])

        get_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])

        LOGGER.info("Verifying get operation response")
        event_bkt_get = get_resp[0]  # Contains buckets when event was set
        fail_bkt_get = get_resp[1]  # Contains buckets which failed when event was clear
        event_di_bkt = get_resp[2]  # Contains buckets when event was set
        fail_di_bkt = get_resp[3]  # Contains buckets which failed when event was clear
        # Above four lists are expected to be empty as all pass expected
        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt) or len(event_bkt_get) or
                                  len(event_di_bkt), "Expected pass in read and di check "
                                                     "operations. Found failures in READ: "
                                                     f"{fail_bkt_get} {event_bkt_get}"
                                                     f"or DI_CHECK: {fail_di_bkt} {event_di_bkt}")
        LOGGER.info("Successfully verified READs and DI check")

        LOGGER.info("Verifying delete operation response")
        remain_bkt = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(remain_bkt), r_buck,
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket}. Remaining {len(remain_bkt)} number of buckets")
        LOGGER.info("Step 3: Sucessfully verified DI on objects & deleted %s buckets. Remaining "
                    "buckets are %s.", del_bucket, r_buck)
        LOGGER.info("Step 4: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 5: Restart the cluster & check cluster status.")
        resp = self.ha_obj.restart_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Cluster restarted fine & all Pods are online.")
        LOGGER.info("Step 6: Verify %s has %s buckets are remaining", self.s3acc_name, r_buck)
        resp = s3_test_obj.bucket_list()
        assert_utils.assert_equal(r_buck, len(resp[1]), resp)
        LOGGER.info("Step 6: Verified %s has %s buckets are remaining", self.s3acc_name, r_buck)
        LOGGER.info("Step 7: Delete %s's remaining %s buckets", self.s3acc_name, r_buck)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': r_buck, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = ()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        resp = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(resp), 0, f"Failed to delete remaining {r_buck} buckets")
        LOGGER.info("Step 7: Sucessfully deleted %s's remaining %s buckets",
                    self.s3acc_name, r_buck)
        LOGGER.info("Step 8: Create new buckets. Run IOs & verify DI. Delete created buckets.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29471-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Created new buckets. Run IOs & verify DI. Delete created buckets.")
        LOGGER.info("Completed: Test to check DELETEs after cluster restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-29478")
    @CTFailOn(error_handler)
    def test_ios_during_cluster_restart(self):
        """
        This test verifies IOs during cluster restart
        """
        LOGGER.info("Started: Test to check IOs during cluster restart.")
        event = threading.Event()  # Event to be used to send when data pod restart start
        LOGGER.info("Step 1. Start parallel S3 IOs during cluster restart.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29478'
        self.s3_clean = users
        output = Queue()

        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 8, 'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        event.set()
        LOGGER.info("Step 1. Started parallel S3 IOs during cluster restart.")
        LOGGER.info("Step 2: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 3: Shutdown the cluster and check the cluster status.")
        resp = self.ha_obj.cortx_stop_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info("Step 3: Sucessfully shutdown the cluster and verified all pods are offline.")
        LOGGER.info("Step 4: Start the cluster and verify all pods are running.")
        resp = self.ha_obj.cortx_start_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=300)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Sucessfully started the cluster and verified all pods are running.")
        LOGGER.info("Step 5. Stop parallel S3 and verify the log results.")
        event.clear()
        thread.join()
        responses = {}
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Expected Pass, But Logs which contain failures:"
                                                f" {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) < len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")
        LOGGER.info("Step 5. Stopped parallel S3 and verified the log results.")
        LOGGER.info("Step 6: Create 10 buckets and run S3 IOs on variable size objects.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-29478-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Created 10 buckets and ran S3 IOs on variable size objects.")
        LOGGER.info("Completed: Test to check IOs during cluster restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-29481")
    @CTFailOn(error_handler)
    def test_cluster_shutdown_signal_negative_rest_resp(self):
        """
        This test verifies CSM REST API responses - negative scenario (REST API options validation)
        """
        LOGGER.info("Started: Test to check CSM REST API responses - REST API options validation.")
        LOGGER.info("Step 1: Verify REST API cluster shutdown signal with bad request body")
        resp = self.rest_hlt_obj.cluster_operation_signal(
            operation="xyz_signal", resource="cluster", expected_response=HTTPStatus.BAD_REQUEST)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Verified REST API cluster shutdown signal with bad request body.")
        LOGGER.info("Step 2: Verify REST API cluster shutdown signal with unauthorized request")
        resp = self.rest_hlt_obj.cluster_operation_signal(
            operation="shutdown_signal",
            resource="cluster",
            expected_response=HTTPStatus.UNAUTHORIZED,
            negative_resp="Bearer 1232sdfsdf34#232")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Verified REST API cluster shutdown signal with unauthorized request")
        LOGGER.info("Step 3: Send the cluster shutdown signal through CSM REST.")
        resp = self.rest_hlt_obj.cluster_operation_signal(
            operation="shutdown_signal", resource="cluster")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Successfully sent the cluster shutdown signal through CSM REST.")
        LOGGER.info("Step 4: Shutdown the cluster and make it unavailable.")
        resp = self.ha_obj.cortx_stop_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info("Step 4: Successfully shutdown the cluster and verified all pods are offline.")
        LOGGER.info("Step 5: Start the cluster and verify all pods are running.")
        resp = self.ha_obj.cortx_start_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=300)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Successfully started the cluster and verified all pods are running.")

        LOGGER.info("Completed: Test to check CSM REST API responses - "
                    "REST API options validation.")
