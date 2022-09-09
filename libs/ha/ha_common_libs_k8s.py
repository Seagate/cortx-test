#!/usr/bin/python  # pylint: disable=too-many-lines
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
HA common utility methods
"""
import copy
import json
import logging
import os
import random
import secrets
import sys
import time
from ast import literal_eval
from http import HTTPStatus
from time import perf_counter_ns

import yaml
from requests import exceptions as req_exception

from commons import commands as common_cmd
from commons import constants as common_const
from commons import pswdmanager
from commons.constants import Rest as Const
from commons.exceptions import CTException
from commons.helpers.pods_helper import LogicalNode
from commons.utils import config_utils
from commons.utils import system_utils
from commons.utils.system_utils import run_local_cmd
from config import CMN_CFG
from config import CSM_REST_CFG
from config import HA_CFG
from config.s3 import S3_BLKBOX_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_core_lib import RestClient
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.di.di_mgmt_ops import ManagementOPs
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_common_test_lib import empty_versioned_bucket
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from scripts.s3_bench import s3bench

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class HAK8s:
    """
    This class contains common utility methods for HA related operations.
    """

    def __init__(self):
        self.system_health = SystemHealth()
        self.setup_type = CMN_CFG["setup_type"]
        self.vm_username = os.getenv(
            "QA_VM_POOL_ID", pswdmanager.decrypt(HA_CFG["vm_params"]["uname"]))
        self.vm_password = os.getenv("QA_VM_POOL_PASSWORD", HA_CFG["vm_params"]["passwd"])
        self.bmc_user = CMN_CFG.get('bmc', {}).get('username')
        self.bmc_pwd = CMN_CFG.get('bmc', {}).get('password')
        self.t_power_on = HA_CFG["common_params"]["power_on_time"]
        self.t_power_off = HA_CFG["common_params"]["power_off_time"]
        self.mgnt_ops = ManagementOPs()
        self.num_nodes = len(CMN_CFG["nodes"])
        self.num_pods = ""
        self.s3_rest_obj = S3AccountOperationsRestAPI()
        self.parallel_ios = None
        self.system_random = secrets.SystemRandom()
        self.dir_path = common_const.K8S_SCRIPTS_PATH
        self.restapi = RestClient(CSM_REST_CFG)

    def polling_host(self,
                     max_timeout: int,
                     host: str,
                     exp_resp: bool,
                     bmc_obj=None):
        """
        Helper function to poll for host ping response
        :param max_timeout: Max timeout allowed for expected response from ping
        :param host: Host to ping
        :param exp_resp: Expected resp True/False for host state Reachable/Unreachable
        :param bmc_obj: BMC object
        :return: bool
        """
        poll = time.time() + max_timeout  # max timeout
        while poll > time.time():
            time.sleep(20)
            resp = system_utils.check_ping(host)
            if self.setup_type == "VM":
                vm_name = host.split(".")[0]
                LOGGER.info("Refreshing %s", vm_name)
                system_utils.execute_cmd(
                    common_cmd.CMD_VM_REFRESH.format(
                        self.vm_username, self.vm_password, vm_name))
                vm_info = system_utils.execute_cmd(
                    common_cmd.CMD_VM_INFO.format(
                        self.vm_username, self.vm_password, vm_name))
                if not vm_info[0]:
                    LOGGER.error("Unable to get VM power status for %s", vm_name)
                    return False
                data = vm_info[1].split("\\n")
                pw_state = ""
                for lines in data:
                    if 'power_state' in lines:
                        pw_state = (lines.split(':')[1].strip('," '))
                LOGGER.debug("Power state for %s : %s", host, pw_state)
                if exp_resp:
                    exp_state = pw_state == 'up'
                else:
                    exp_state = pw_state == 'down'
            else:
                out = bmc_obj.bmc_node_power_status(self.bmc_user, self.bmc_pwd)
                if exp_resp:
                    exp_state = "on" in out
                else:
                    exp_state = "off" in out

            if resp == exp_resp and exp_state:
                return True
        return False

    def host_power_on(self, host: str, bmc_obj=None):
        """
        Helper function for host power on
        :param host: Host to be power on
        :param bmc_obj: BMC object
        :rtype: boolean from polling_host() response
        """

        if self.setup_type == "VM":
            vm_name = host.split(".")[0]
            resp = system_utils.execute_cmd(
                common_cmd.CMD_VM_POWER_ON.format(
                    self.vm_username, self.vm_password, vm_name))
            if not resp[0]:
                LOGGER.info("Response for failed VM power on command: %s", resp)
                return False
        else:
            bmc_obj.bmc_node_power_on_off(self.bmc_user, self.bmc_pwd, "on")

        LOGGER.info("Check if %s is powered on.", host)
        # SSC cloud is taking time to on VM host hence timeout
        resp = self.polling_host(max_timeout=self.t_power_on, host=host,
                                 exp_resp=True, bmc_obj=bmc_obj)
        return resp

    def host_safe_unsafe_power_off(self, host: str, bmc_obj=None,
                                   pod_obj=None, is_safe: bool = False):
        """
        Helper function for safe/unsafe host power off
        :param host: Host to be power off
        :param bmc_obj: BMC object
        :param pod_obj: Pod object
        :param is_safe: Power off host with safe/unsafe shutdown
        :rtype: boolean from polling_host() response
        """
        if is_safe:
            resp = pod_obj.execute_cmd(cmd="shutdown -P now", exc=False)
            LOGGER.debug("Response for shutdown: %s", resp)
        else:
            if self.setup_type == "VM":
                vm_name = host.split(".")[0]
                resp = system_utils.execute_cmd(
                    common_cmd.CMD_VM_POWER_OFF.format(
                        self.vm_username, self.vm_password, vm_name))
                if not resp[0]:
                    LOGGER.info("Response for failed VM power off command: %s", resp)
                    return False
            else:
                bmc_obj.bmc_node_power_on_off(self.bmc_user, self.bmc_pwd, "off")

        LOGGER.info("Check if %s is powered off.", host)
        # SSC cloud is taking time to off VM host hence timeout
        resp = self.polling_host(
            max_timeout=self.t_power_off, host=host, exp_resp=False, bmc_obj=bmc_obj)
        return resp

    # pylint: disable-msg=too-many-locals
    def delete_s3_acc_buckets_objects(self, s3_data: dict, obj_crud: bool = False):
        """
        This function deletes all s3 buckets objects(Versioned or unversioned) for the s3 account
        and all s3 accounts
        :param s3_data: Dictionary for s3 operation info
        :param obj_crud: If true, it will delete only objects of all buckets
        :return: (bool, response)
        """
        try:
            if obj_crud:
                for details in s3_data.values():
                    s3_del = S3TestLib(endpoint_url=S3_CFG["s3_url"],
                                       access_key=details['accesskey'],
                                       secret_key=details['secretkey'])
                    bucket_list = s3_del.bucket_list()[1]
                    for _bucket in bucket_list:
                        obj_list = s3_del.object_list(_bucket)
                        LOGGER.debug("List of object response for %s bucket is %s", _bucket,
                                     obj_list)
                        response = s3_del.delete_multiple_objects(_bucket, obj_list[1], quiet=True)
                        LOGGER.debug("Delete multiple objects response %s", response)
                return True, "Successfully performed Objects Delete operation"
            for details in s3_data.values():
                s3_del = S3TestLib(endpoint_url=S3_CFG["s3_url"],
                                   access_key=details['accesskey'], secret_key=details['secretkey'])
                s3_ver = S3VersioningTestLib(access_key=details['accesskey'],
                                             secret_key=details['secretkey'],
                                             endpoint_url=S3_CFG["s3_url"])
                buckets = s3_del.bucket_list()[1]
                LOGGER.info("Delete all versions and delete markers present for all the buckets.")
                for _bucket in buckets:
                    empty_versioned_bucket(s3_ver, _bucket)
                    obj_list = s3_del.object_list(_bucket)
                    LOGGER.debug("List of object response for %s bucket %s", _bucket, obj_list)
                    response = s3_del.delete_multiple_objects(_bucket, obj_list[1], quiet=True)
                    LOGGER.debug("Delete multiple objects response %s", response[1])
                    s3_del.delete_bucket(_bucket, force=True)
                response = self.s3_rest_obj.delete_s3_account(details['user_name'])
                if not response[0]:
                    return response
            return True, "Successfully performed S3 clean up operations"
        except (ValueError, KeyError, CTException) as error:
            LOGGER.exception("%s %s: %s", Const.EXCEPTION_ERROR,
                             HAK8s.delete_s3_acc_buckets_objects.__name__, error)
            return False, error

    # pylint: disable=too-many-arguments
    def ha_s3_workload_operation(
            self,
            log_prefix: str,
            s3userinfo: dict,
            skipread: bool = False,
            skipwrite: bool = False,
            skipcleanup: bool = False,
            nsamples: int = 10,
            nclients: int = 10,
            large_workload: bool = False,
            setup_s3bench: bool = True,
            end_point=S3_CFG["s3_url"],
            connect_timeout=None,
            **kwargs):
        """
        This function creates s3 acc, buckets and performs WRITEs/READs/DELETEs
        operations on VM/HW
        :param log_prefix: Test number prefix for log file
        :param s3userinfo: S3 user info
        :param skipread: Skip reading objects created in this run if True
        :param skipwrite: Skip writing objects created in this run if True
        :param skipcleanup: Skip deleting objects created in this run if True
        :param nsamples: Number of samples of object
        :param nclients: Number of clients/workers
        :param large_workload: Flag to start large workload IOs
        :param setup_s3bench: Flag if s3bench need to be setup
        :param end_point: Endpoint to run IOs
        :param connect_timeout: Maximum amount of time a dial will wait for a connect to complete
        :return: bool/operation response
        """
        host = kwargs.get("host", None)
        user = kwargs.get("user", None)
        pwd = kwargs.get("pwd", None)
        remote = True if host else False
        workloads = copy.deepcopy(HA_CFG["s3_bench_workloads"])
        if self.setup_type == "HW" or large_workload:
            workloads.extend(HA_CFG["s3_bench_large_workloads"])

        if setup_s3bench:
            resp = s3bench.setup_s3bench(hostname=host, username=user, password=pwd, remote=remote)
            if not resp:
                return resp, "Couldn't setup s3bench on client machine."
        for workload in workloads:
            resp = s3bench.s3bench(
                s3userinfo['accesskey'], s3userinfo['secretkey'],
                bucket=f"bucket-{workload.lower()}-{log_prefix}",
                num_clients=nclients, num_sample=nsamples, obj_name_pref=f"ha_{log_prefix}",
                obj_size=workload, skip_write=skipwrite, skip_read=skipread,
                skip_cleanup=skipcleanup, log_file_prefix=log_prefix.upper(),
                end_point=end_point, validate_certs=S3_CFG["validate_certs"], host=host,
                user=user, pwd=pwd, remote=remote, connectTimeout=connect_timeout)
            resp = system_utils.validate_s3bench_parallel_execution(log_path=resp[1])
            if not resp[0]:
                return False, f"s3bench operation failed: {resp[1]}"
        return True, "Successfully completed s3bench operation"

    def cortx_start_cluster(self, pod_obj, dir_path=None):
        """
        This function starts the cluster
        :param pod_obj : Pod object from which the command should be triggered
        :param dir_path : Path to repo scripts
        :return: Boolean, response
        """
        LOGGER.info("Start the cluster")
        cmd_path = dir_path if dir_path else self.dir_path
        resp = pod_obj.execute_cmd(common_cmd.CLSTR_START_CMD.format(cmd_path),
                                   read_lines=True, exc=False)
        LOGGER.debug("Cluster start response: %s", resp)
        if resp[0]:
            return True, resp
        return False, resp

    def cortx_stop_cluster(self, pod_obj, dir_path=None):
        """
        This function stops the cluster
        :param pod_obj : Pod object from which the command should be triggered
        :param dir_path : Path to repo scripts
        :return: Boolean, response
        """
        LOGGER.info("Stop the cluster")
        if dir_path:
            resp = pod_obj.execute_cmd(common_cmd.CLSTR_STOP_CMD.format(dir_path),
                                       read_lines=True, exc=False)
        else:
            resp = pod_obj.execute_cmd(common_cmd.CLSTR_STOP_CMD.format(self.dir_path),
                                       read_lines=True, exc=False)
        LOGGER.info("Cluster stop response: %s", resp)
        if resp[0]:
            return True, resp
        return False, resp

    def restart_cluster(self, pod_obj, sync=False):
        """
        Restart the cluster and check all node's health
        :param pod_obj: pod object for stop/start cluster
        :param sync: Flag to run sync command
        """
        if sync:
            LOGGER.info("Send sync command")
            resp = pod_obj.send_sync_command(common_const.POD_NAME_PREFIX)
            if not resp:
                LOGGER.info("Cluster is restarting without sync")
        LOGGER.info("Stop the cluster")
        resp = self.cortx_stop_cluster(pod_obj)
        if not resp[0]:
            return False, "Error during Stopping cluster"
        LOGGER.info("Check all Pods are offline.")
        resp = self.check_cluster_status(pod_obj)
        if resp[0]:
            return False, "Pods are still running."
        LOGGER.info("Start the cluster")
        resp = self.cortx_start_cluster(pod_obj)
        if not resp[0]:
            return False, "Error during Starting cluster"
        LOGGER.info("Check all Pods and cluster online.")
        resp = self.poll_cluster_status(pod_obj)
        if not resp[0]:
            return False, "Cluster is not started"
        if sync:
            LOGGER.info("Send sync command")
            resp = pod_obj.send_sync_command(common_const.POD_NAME_PREFIX)
            if not resp:
                LOGGER.info("Sync command is not executed")
        return True, resp

    @staticmethod
    def check_pod_status(pod_obj):
        """
        Helper function to check pods status.
        :param pod_obj: Pod object
        :return:
        """
        LOGGER.info("Checking if all Pods are online.")
        resp = pod_obj.execute_cmd(common_cmd.CMD_POD_STATUS, read_lines=True)
        resp.pop(0)
        for line in resp:
            if "Running" not in line:
                return False, resp
        return True, resp

    # pylint: disable=too-many-return-statements
    def create_bucket_to_complete_mpu(self, s3_data, bucket_name, object_name, file_size,
                                      total_parts, multipart_obj_path):
        """
        Helper function to complete multipart upload
        :param s3_data: s3 account details
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param file_size: Size of the file to be created to upload
        :param total_parts: Total parts to be uploaded
        :param multipart_obj_path: Path of the file to be uploaded
        :return: response
        """
        access_key = s3_data["s3_acc"]["accesskey"]
        secret_key = s3_data["s3_acc"]["secretkey"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        s3_mp_test_obj = S3MultipartTestLib(access_key=access_key,
                                            secret_key=secret_key, endpoint_url=S3_CFG["s3_url"])

        LOGGER.info("Checking if bucket %s already exists", bucket_name)
        resp = s3_test_obj.bucket_list()
        bkt_flag = bucket_name not in resp[1]
        if bkt_flag:
            LOGGER.info("Creating a bucket with name : %s", bucket_name)
            res = s3_test_obj.create_bucket(bucket_name)
            if not res[0] or res[1] != bucket_name:
                return res, "Failed in bucket creation"
            LOGGER.info("Created a bucket with name : %s", bucket_name)
        LOGGER.info("Initiating multipart upload")
        res = s3_mp_test_obj.create_multipart_upload(bucket_name, object_name)
        if not res[0]:
            return res, "Failed in initiate multipart upload"
        mpu_id = res[1]["UploadId"]
        LOGGER.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        LOGGER.info("Uploading parts into bucket")
        res = s3_mp_test_obj.upload_parts(mpu_id=mpu_id, bucket_name=bucket_name,
                                          object_name=object_name, multipart_obj_size=file_size,
                                          total_parts=total_parts,
                                          multipart_obj_path=multipart_obj_path)
        if not res[0]:
            return res, "Failed in upload parts"
        parts = res[1]
        LOGGER.info("Uploaded parts into bucket: %s", parts)
        LOGGER.info("Successfully uploaded object")

        checksum = self.cal_compare_checksum(file_list=[multipart_obj_path], compare=False)[0]

        LOGGER.info("Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, bucket_name, object_name)
        if not res[0] or len(res[1]["Parts"]) != len(parts):
            return res, "Failed in list parts of multipart upload"
        LOGGER.info("Listed parts of multipart upload: %s", res[1])
        LOGGER.info("Completing multipart upload")
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts, bucket_name, object_name)
        if not res[0]:
            return res, "Failed in completing multipart upload"
        res = s3_test_obj.object_list(bucket_name)
        if object_name not in res[1]:
            return res, "Failed in object listing"
        LOGGER.info("Multipart upload completed")
        return True, s3_data, checksum

    def partial_multipart_upload(self, s3_data, bucket_name, object_name, part_numbers, **kwargs):
        """
        Helper function to do partial multipart upload
        :param s3_data: s3 account details
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param part_numbers: List of parts to be uploaded
        :return: response
        """
        try:
            total_parts = kwargs.get("total_parts", None)
            multipart_obj_size = kwargs.get("multipart_obj_size", None)
            multipart_obj_path = kwargs.get("multipart_obj_path", None)
            remaining_upload = kwargs.get("remaining_upload", False)
            mpu_id = kwargs.get("mpu_id", None)
            access_key = s3_data["s3_acc"]["accesskey"]
            secret_key = s3_data["s3_acc"]["secretkey"]
            parts_etag = list()
            s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                    endpoint_url=S3_CFG["s3_url"])
            s3_mp_test_obj = S3MultipartTestLib(access_key=access_key, secret_key=secret_key,
                                                endpoint_url=S3_CFG["s3_url"])

            if not remaining_upload:
                LOGGER.info("Creating a bucket with name : %s", bucket_name)
                res = s3_test_obj.create_bucket(bucket_name)
                if not res[0] or res[1] != bucket_name:
                    return res
                LOGGER.info("Created a bucket with name : %s", bucket_name)
                LOGGER.info("Initiating multipart upload")
                res = s3_mp_test_obj.create_multipart_upload(bucket_name, object_name)
                if not res[0]:
                    return res
                mpu_id = res[1]["UploadId"]
                LOGGER.info("Multipart Upload initiated with mpu_id %s", mpu_id)

            LOGGER.info("Creating parts of data")
            parts = self.create_multiple_data_parts(multipart_obj_size=multipart_obj_size,
                                                    multipart_obj_path=multipart_obj_path,
                                                    total_parts=total_parts)

            LOGGER.info("Uploading parts %s", part_numbers)

            for part in part_numbers:
                resp = s3_mp_test_obj.upload_multipart(body=parts[part],
                                                       bucket_name=bucket_name,
                                                       object_name=object_name,
                                                       upload_id=mpu_id,
                                                       part_number=part)
                p_etag = resp[1]
                LOGGER.debug("Part : %s", str(p_etag))
                parts_etag.append({"PartNumber": part, "ETag": p_etag["ETag"]})
                LOGGER.info("Uploaded part %s", part)
            return True, mpu_id, multipart_obj_path, parts_etag
        except CTException as error:
            LOGGER.exception("Error in %s: %s", HAK8s.partial_multipart_upload.__name__, error)
            return False, error

    @staticmethod
    def create_multiple_data_parts(multipart_obj_path, multipart_obj_size, total_parts):
        """
         Function to create multiple data parts
        :param multipart_obj_size: Size of the file to be created to upload
        :param total_parts: Total parts to be uploaded
        :param multipart_obj_path: Path of the file to be uploaded
        """
        parts = {}
        uploaded_bytes = 0
        single_part_size = int(multipart_obj_size) // int(total_parts)
        with open(multipart_obj_path, "rb") as file_pointer:
            i = 1
            while True:
                data = file_pointer.read(1048576 * single_part_size)
                LOGGER.info("Part %s data_len %s", i, str(len(data)))
                if not data:
                    file_pointer.close()
                    LOGGER.info("Created multiple data parts")
                    break
                parts[i] = data
                uploaded_bytes += len(data)
                i += 1

        return parts

    # pylint: disable-msg=too-many-locals
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-return-statements
    @staticmethod
    def create_bucket_copy_obj(event, s3_test_obj=None, bucket_name=None, object_name=None,
                               bkt_obj_dict=None, output=None, **kwargs):
        """
        Function create multiple buckets and upload and copy objects (Can be used to start
        background process for the same)
        :param event: Thread event to be sent in case of parallel IOs
        :param s3_test_obj: s3 test lib object
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param bkt_obj_dict: Dict of buckets and objects
        :param output: Queue used to fill output
        :return: response
        """
        file_path = kwargs.get("file_path", None)
        background = kwargs.get("background", False)
        bkt_op = kwargs.get("bkt_op", True)
        put_etag = kwargs.get("put_etag", None)
        exp_fail_bkt_obj_dict = dict()
        failed_bkts = list()
        event_clear_flg = False
        if bkt_op:
            LOGGER.info("Create bucket and put object.")
            resp = s3_test_obj.create_bucket(bucket_name)
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                return resp if not background else sys.exit(1)
            resp, bktlist = s3_test_obj.bucket_list()
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Bucket list: %s", bktlist)
            if bucket_name not in bktlist:
                return False, bktlist if not background else sys.exit(1)
            resp = system_utils.create_file(fpath=file_path, count=1000, b_size="1M")
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                return resp if not background else sys.exit(1)
            put_resp = s3_test_obj.put_object(bucket_name=bucket_name, object_name=object_name,
                                              file_path=file_path,
                                              metadata={"City": "Pune", "Country": "India"})
            LOGGER.info("Put object response: %s", put_resp)
            if not put_resp[0]:
                return resp if not background else sys.exit(1)
            put_etag = put_resp[1]["ETag"]
            resp = s3_test_obj.object_list(bucket_name)
            LOGGER.info("Response: %s", resp)
            if not resp[0] or object_name not in resp[1]:
                return resp if not background else sys.exit(1)

        LOGGER.info("Creating buckets for copy object to different bucket with different object "
                    "name.")
        for bkt_name, obj_name in bkt_obj_dict.items():
            resp, bktlist = s3_test_obj.bucket_list()
            LOGGER.info("Bucket list: %s", bktlist)
            if bkt_name not in bktlist:
                resp = s3_test_obj.create_bucket(bkt_name)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    return resp if not background else sys.exit(1)

        LOGGER.info("Start copy object to buckets: %s", list(bkt_obj_dict.keys()))
        for bkt_name, obj_name in bkt_obj_dict.items():
            try:
                status, response = s3_test_obj.copy_object(source_bucket=bucket_name,
                                                           source_object=object_name,
                                                           dest_bucket=bkt_name,
                                                           dest_object=obj_name)
                LOGGER.info("status is %s with Response: %s", status, response)
                copy_etag = response['CopyObjectResult']['ETag']
                if put_etag.strip('"') == copy_etag.strip('"'):
                    LOGGER.info("Object %s copied to bucket %s with object name %s successfully",
                                object_name, bkt_name, obj_name)
                else:
                    LOGGER.error("Etags don't match for copy object %s to bucket %s with object "
                                 "name %s", object_name, bkt_name, obj_name)
                    failed_bkts.append(bkt_name)
            except CTException as error:
                LOGGER.exception("Error: %s", error)
                if event.is_set():
                    exp_fail_bkt_obj_dict[bkt_name] = obj_name
                    event_clear_flg = True
                else:
                    if event_clear_flg:
                        exp_fail_bkt_obj_dict[bkt_name] = obj_name
                        event_clear_flg = False
                        continue
                    failed_bkts.append(bkt_name)
                LOGGER.info("Failed to copy object to bucket %s", bkt_name)

        if failed_bkts and not background:
            return False, failed_bkts

        return True, put_etag if not background else output.put((put_etag, exp_fail_bkt_obj_dict,
                                                                 failed_bkts))

    # pylint: disable-msg=too-many-locals
    def start_random_mpu(self, event, s3_data, bucket_name, object_name, file_size, total_parts,
                         multipart_obj_path, part_numbers, parts_etag, output):
        """
        Helper function to start mpu (To start mpu in background, this function needs to be used)
        :param event: Thread event to be sent in case of parallel IOs
        :param s3_data: s3 account details
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param file_size: Size of the file to be created to upload
        :param total_parts: Total parts to be uploaded
        :param multipart_obj_path: Path of the file to be uploaded
        :param part_numbers: List of random parts to be uploaded
        :param parts_etag: List containing uploaded part number with its ETag
        :param output: Queue used to fill output
        :return: response
        """
        access_key = s3_data["s3_acc"]["accesskey"]
        secret_key = s3_data["s3_acc"]["secretkey"]
        failed_parts = []
        exp_failed_parts = []
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        s3_mp_test_obj = S3MultipartTestLib(access_key=access_key,
                                            secret_key=secret_key, endpoint_url=S3_CFG["s3_url"])

        try:
            LOGGER.info("Creating a bucket with name : %s", bucket_name)
            res = s3_test_obj.create_bucket(bucket_name)
            LOGGER.info("Response: %s", res)
            LOGGER.info("Created a bucket with name : %s", bucket_name)
            LOGGER.info("Initiating multipart upload")
            res = s3_mp_test_obj.create_multipart_upload(bucket_name, object_name)
            LOGGER.info("Response: %s", res)
            mpu_id = res[1]["UploadId"]
            LOGGER.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        except CTException as error:
            LOGGER.exception("Failed mpu due to error %s. Exiting from background process.", error)
            sys.exit(1)

        LOGGER.info("Creating parts of data")
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        system_utils.create_file(multipart_obj_path, file_size)
        parts = self.create_multiple_data_parts(multipart_obj_size=file_size,
                                                multipart_obj_path=multipart_obj_path,
                                                total_parts=total_parts)
        LOGGER.info("Uploading parts into bucket: %s", part_numbers)
        for i in part_numbers:
            try:
                resp = s3_mp_test_obj.upload_multipart(body=parts[i], bucket_name=bucket_name,
                                                       object_name=object_name, upload_id=mpu_id,
                                                       part_number=i)
                LOGGER.info("Response: %s", resp)
                p_tag = resp[1]
                LOGGER.debug("Part : %s", str(p_tag))
                parts_etag.append({"PartNumber": i, "ETag": p_tag["ETag"]})
                LOGGER.info("Uploaded part %s", i)
            except CTException as error:
                LOGGER.exception("Error: %s", error)
                if event.is_set():
                    exp_failed_parts.append(i)
                else:
                    failed_parts.append(i)
                LOGGER.info("Failed to upload part %s", i)

        res = (exp_failed_parts, failed_parts, parts_etag, mpu_id)
        output.put(res)

    def check_cluster_status(self, pod_obj, pod_list=None, dir_path=None):
        """
        Function to check cluster status
        :param pod_obj: Object for master node
        :param pod_list: Data pod name list to get the hctl status
        :param dir_path : Path to repo scripts
        :return: boolean, response
        """
        LOGGER.info("Check the overall K8s cluster status.")
        try:
            cmd_path = dir_path if dir_path else self.dir_path
            resp = pod_obj.execute_cmd(common_cmd.CLSTR_STATUS_CMD.format(cmd_path))
        except IOError as error:
            LOGGER.error("Error: Cluster status has some failures.")
            return False, error
        resp = (resp.decode('utf-8')).split('\n')
        for line in resp:
            if "FAILED" in line:
                LOGGER.error("Response for K8s cluster status: %s", resp)
                return False, "K8S cluster status has Failures"
        if pod_list is None:
            pod_list = pod_obj.get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        for pod_name in pod_list:
            res = pod_obj.send_k8s_cmd(
                operation="exec", pod=pod_name, namespace=common_const.NAMESPACE,
                command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} -- "
                               f"{common_cmd.MOTR_STATUS_CMD}", decode=True)
            for line in res.split("\n"):
                if common_const.MOTR_CLIENT not in line:
                    if "failed" in line or "offline" in line or "unknown" in line:
                        LOGGER.error("Response for data pod %s's hctl status: %s", pod_name, res)
                        return False, f"Cortx HCTL status has Failures in pod {pod_name}"
        return True, "K8s and cortx both cluster up and clean."

    @staticmethod
    def cal_compare_checksum(file_list, compare=False):
        """
        Helper function to calculate ro compare the checksums of given files
        :param file_list: List of files of which checksum is to be calculated
        :param compare: Flag to compare checksums of files
        :return: List of md5 content or bool for md5 comparison
        """
        md5_list = []
        for file in file_list:
            cmd = common_cmd.MD5SUM.format("-t", file)
            resp = run_local_cmd(cmd=cmd)
            md5 = (resp[1].split())[0]
            md5_list.append(md5.replace("b'", ""))

        if not compare:
            return md5_list
        return all(md5_list[0] == x for x in md5_list)

    def poll_cluster_status(self, pod_obj, timeout=1200):         # default 20mins timeout
        """
        Helper function to poll the cluster status
        :param pod_obj: Object for master nodes
        :param timeout: Timeout value
        :return: bool, response
        """
        resp = False
        LOGGER.info("Polling cluster status")
        start_time = int(time.time())
        while timeout > int(time.time()) - start_time:
            time.sleep(60)
            resp = self.check_cluster_status(pod_obj)
            if resp[0]:
                LOGGER.info("Cortx cluster is up")
                break

        LOGGER.debug("Time taken by cluster restart is %s seconds", int(time.time()) - start_time)
        return resp

    def restore_pod(self, pod_obj, restore_method, restore_params: dict = None,
                    clstr_status=False):
        """
        Helper function to restore pod based on way_to_restore
        :param pod_obj: Object of master node
        :param restore_method: Restore method to be used depending on shutdown method
        ("scale_replicas", "k8s", "helm")
        :param restore_params: Dict which has parameters required to restore pods
        :param clstr_status: Flag to check cluster status after pod restored
        :return: Bool, response
        """
        resp = False
        deployment_name = restore_params.get("deployment_name", None)
        deployment_backup = restore_params.get("deployment_backup", None)
        set_name = restore_params.get("set_name", None)
        num_replica = restore_params.get("num_replica", 1)

        if restore_method == common_const.RESTORE_SCALE_REPLICAS:
            resp = pod_obj.create_pod_replicas(num_replica=num_replica, deploy=deployment_name,
                                               set_name=set_name)
        elif restore_method == common_const.RESTORE_DEPLOYMENT_K8S:
            resp = pod_obj.recover_deployment_k8s(deployment_name=deployment_name,
                                                  backup_path=deployment_backup)
        elif restore_method == common_const.RESTORE_DEPLOYMENT_HELM:
            resp = pod_obj.recover_deployment_helm(deployment_name=deployment_name)

        if resp[0] and clstr_status:
            resp_clstr = self.poll_cluster_status(pod_obj, timeout=180)
            LOGGER.debug("Cluster status: %s", resp_clstr)
            return resp_clstr
        return resp

    def event_s3_operation(self, event, setup_s3bench=True, log_prefix=None, s3userinfo=None,
                           skipread=False, skipwrite=False, skipcleanup=False, nsamples=10,
                           nclients=10, output=None, event_set_clr=None, max_retries=None,
                           httpclientimeout=HA_CFG["s3_operation_data"]["httpclientimeout"],
                           connect_timeout=None, end_point=S3_CFG["s3_url"], **kwargs):
        """
        This function executes s3 bench operation on VM/HW.(can be used for parallel execution)
        :param event: Thread event to be sent in case of parallel IOs
        :param setup_s3bench: Flag to setup or not s3bench
        :param log_prefix: Test number prefix for log file
        :param s3userinfo: S3 user info
        :param skipread: Skip reading objects created in this run if True
        :param skipwrite: Skip writing objects created in this run if True
        :param skipcleanup: Skip deleting objects created in this run if True
        :param nsamples: Number of samples of object
        :param nclients: Number of clients/workers
        :param output: Queue to fill results
        :param httpclientimeout: Time limit in ms for requests made by this Client.
        :param event_set_clr: Thread event set-clear flag reference when s3bench workload
        execution miss the event set-clear time window
        :param max_retries: Number of retries for IO operations
        :param connect_timeout: Maximum amount of time a dial will wait for a connect to complete
        :param end_point: Endpoint to run IOs
        :return: None
        """
        pass_res = []
        fail_res = []
        results = dict()
        host = kwargs.get("host", None)
        user = kwargs.get("user", None)
        pwd = kwargs.get("pwd", None)
        remote = True if host else False
        workloads = HA_CFG["s3_bench_workloads"]
        if self.setup_type == "HW":
            workloads.extend(HA_CFG["s3_bench_large_workloads"])
        if setup_s3bench:
            resp = s3bench.setup_s3bench(hostname=host, username=user, password=pwd, remote=remote)
            if not resp:
                status = (resp, "Couldn't setup s3bench on client machine.")
                output.put(status)
                sys.exit(1)
        for workload in workloads:
            resp = s3bench.s3bench(
                s3userinfo['accesskey'], s3userinfo['secretkey'],
                bucket=f"bucket-{workload.lower()}-{log_prefix}", num_clients=nclients,
                num_sample=nsamples, obj_name_pref=f"ha_{log_prefix}",
                skip_write=skipwrite, skip_read=skipread, obj_size=workload,
                skip_cleanup=skipcleanup, log_file_prefix=f"log_{log_prefix}",
                end_point=end_point, validate_certs=S3_CFG["validate_certs"],
                httpclientimeout=httpclientimeout, max_retries=max_retries,
                connectTimeout=connect_timeout, host=host, user=user, pwd=pwd, remote=remote)
            if event.is_set() or (isinstance(event_set_clr, list) and event_set_clr[0]):
                LOGGER.debug("The state of event set clear Flag is %s", event_set_clr)
                fail_res.append(resp)
                if isinstance(event_set_clr, list):
                    event_set_clr[0] = False
            else:
                pass_res.append(resp)
        results["pass_res"] = pass_res
        results["fail_res"] = fail_res

        output.put(results)

    @staticmethod
    def check_s3bench_log(file_paths: list, pass_logs=True):
        """
        Function to find out error is reported in given file or not
        :param str file_paths: log file paths to be parsed
        :param pass_logs: if True check for passed logs else check for failed logs
        :return: False (if error is seen) else True
        :rtype: Boolean, list
        """
        log_list = []
        resp = (False, "Logs not found")
        for log in file_paths:
            LOGGER.info("Parsing log file %s", log)
            resp = system_utils.validate_s3bench_parallel_execution(log_path=log)
            if not resp[0] and pass_logs:
                LOGGER.error(resp[1])
            log_list.append(log) if (pass_logs and not resp[0]) or \
                                    (not pass_logs and resp[0]) else log

        return resp[0], log_list

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches
    def put_get_delete(self, event, s3_test_obj, **kwargs):
        """
        Helper function to put, get and delete objects
        :param event: Thread event to be sent for parallel IOs
        :param s3_test_obj: s3 test object for the buckets to be deleted
        :param kwargs:
        test_prefix: Mandatory param,
        test_dir_path: Mandatory param,
        output: Mandatory param,
        skipput: True if put is expected to be skipped,
        skipget: True if get is expected to be skipped,
        skipdel: True if delete is expected to be skipped,
        bkt_list: List of buckets on which operations to be performed (optional),
        s3_data: Dict to store bucket, object and checksum related info (Mandatory for get),
        bkts_to_wr: Mandatory param for put,
        di_check: Flag to enable/disable di check (optional),
        bkts_to_del: Required in case of counted delete operation (optional)
        :return: None
        """
        workload = HA_CFG["s3_bucket_data"]["workload_sizes_mbs"]
        test_prefix = kwargs.get("test_prefix")
        test_dir_path = kwargs.get("test_dir_path")
        output = kwargs.get("output")
        skipput = kwargs.get("skipput", False)
        skipget = kwargs.get("skipget", False)
        skipdel = kwargs.get("skipdel", False)
        bkt_list = kwargs.get("bkt_list", list())
        s3_data = kwargs.get("s3_data", dict())
        if not skipput:
            bkts_to_wr = kwargs.get("bkts_to_wr")
            event_bkt_put = []
            fail_bkt_put = []
            i = 0
            while i < bkts_to_wr:
                size_mb = random.sample(workload, 1)[0]
                bucket_name = f"{test_prefix}-{i}-{size_mb}-{perf_counter_ns()}"
                object_name = f"obj_{bucket_name}"
                file_path = os.path.join(test_dir_path, f"{bucket_name}.txt")
                try:
                    s3_test_obj.create_bucket_put_object(bucket_name, object_name, file_path,
                                                         size_mb)
                    upload_chm = self.cal_compare_checksum(file_list=[file_path], compare=False)[0]
                    s3_data.update({bucket_name: (object_name, upload_chm)})
                except CTException as error:
                    LOGGER.exception("Error in %s: %s", HAK8s.put_get_delete.__name__, error)
                    if event.is_set():
                        event_bkt_put.append(bucket_name)
                    else:
                        fail_bkt_put.append(bucket_name)

                i += 1

            res = (s3_data, event_bkt_put, fail_bkt_put)
            output.put(res)

        if not skipget:
            di_check = kwargs.get("di_check", False)
            bkt_list = bkt_list if bkt_list else s3_test_obj.bucket_list()[1]
            event_bkt_get = []
            fail_bkt_get = []
            event_di_bkt = []
            fail_di_bkt = []
            for bkt in bkt_list:
                download_file = "Download_" + str(bkt)
                download_path = os.path.join(test_dir_path, download_file)
                try:
                    resp = s3_test_obj.object_download(bkt, s3_data[bkt][0], download_path)
                    LOGGER.info("Download object response: %s", resp)
                except CTException as error:
                    LOGGER.exception("Error in %s: %s", HAK8s.put_get_delete.__name__, error)
                    if event.is_set():
                        event_bkt_get.append(bkt)
                    else:
                        fail_bkt_get.append(bkt)

                if di_check:
                    download_checksum = self.cal_compare_checksum(file_list=[download_path],
                                                                  compare=False)[0]
                    if event.is_set():
                        event_di_bkt.append(bkt)
                    elif not event.is_set() and s3_data[bkt][1] != download_checksum:
                        fail_di_bkt.append(bkt)

            res = (event_bkt_get, fail_bkt_get, event_di_bkt, fail_di_bkt)
            output.put(res)

        if not skipdel:
            bkts_to_del = kwargs.get("bkts_to_del", None)
            bucket_list = bkt_list if bkt_list else s3_test_obj.bucket_list()[1]
            bkts_to_del = bkts_to_del if bkts_to_del is not None else len(bucket_list)
            LOGGER.info("Count of bucket to be deleted : %s", bkts_to_del)
            event_del_bkt = []
            fail_del_bkt = []
            count = 0
            while count < bkts_to_del:
                for _ in range(len(bucket_list)):
                    try:
                        s3_test_obj.delete_bucket(bucket_name=bucket_list[0], force=True)
                    except CTException as error:
                        LOGGER.exception("Error in %s: %s", HAK8s.put_get_delete.__name__, error)
                        if event.is_set():
                            event_del_bkt.append(bucket_list[0])
                        else:
                            fail_del_bkt.append(bucket_list[0])
                    bucket_list.remove(bucket_list[0])
                    count += 1
                    if count >= bkts_to_del:
                        break
                    if not bkt_list and not bucket_list:
                        while True:
                            time.sleep(HA_CFG["common_params"]["5sec_delay"])
                            bucket_list = s3_test_obj.bucket_list()[1]
                            if len(bucket_list) > 0:
                                time.sleep(HA_CFG["common_params"]["10sec_delay"])
                                break

            LOGGER.info("Deleted %s number of buckets.", count)

            res = (event_del_bkt, fail_del_bkt)
            output.put(res)

    @staticmethod
    def get_data_pod_no_ha_control(data_pod_list: list, pod_obj):
        """
        Helper function to get the data pod name which is not hosted on same node
        as that of HA or control pod
        :param data_pod_list: list for all data pods in cluster
        :param pod_obj: object for master node for pods_helper
        :return: data_pod_name, data_pod_fqdn
        """
        LOGGER.info("Check the node which has the control or HA pod running and"
                    "select data pod which is not hosted on any of these nodes.")
        control_pods = pod_obj.get_pods_node_fqdn(common_const.CONTROL_POD_NAME_PREFIX)
        control_pod_name = list(control_pods.keys())[0]
        control_node_fqdn = control_pods.get(control_pod_name)
        LOGGER.info("Control pod %s is hosted on %s node", control_pod_name, control_node_fqdn)
        ha_pods = pod_obj.get_pods_node_fqdn(common_const.HA_POD_NAME_PREFIX)
        ha_pod_name = list(ha_pods.keys())[0]
        ha_node_fqdn = ha_pods.get(ha_pod_name)
        LOGGER.info("HA pod %s is hosted on %s node", ha_pod_name, ha_node_fqdn)
        LOGGER.info("Get the data pod running on %s node and %s node",
                    control_node_fqdn, ha_node_fqdn)
        data_pods = pod_obj.get_pods_node_fqdn(common_const.POD_NAME_PREFIX)
        data_pod_name2 = data_pod_name1 = server_pod_name = None
        for pod_name, node in data_pods.items():
            if node == control_node_fqdn:
                data_pod_name1 = pod_name
            if node == ha_node_fqdn:
                data_pod_name2 = pod_name
        new_list = [pod_name for pod_name in data_pod_list
                    if pod_name not in (data_pod_name1, data_pod_name2)]
        data_pod_name = random.sample(new_list, 1)[0]
        LOGGER.info("%s data pod is not hosted either on control or ha node",
                    data_pod_name)
        data_node_fqdn = data_pods.get(data_pod_name)
        server_pods = pod_obj.get_pods_node_fqdn(common_const.SERVER_POD_NAME_PREFIX)
        for pod_name, node in server_pods.items():
            if node == data_node_fqdn:
                server_pod_name = pod_name
        LOGGER.info("Node %s is hosting data pod %s nd server pod %s",
                    data_node_fqdn, data_pod_name, server_pod_name)

        return data_pod_name, server_pod_name, data_node_fqdn

    @staticmethod
    def get_nw_iface_node_down(host_list: list, node_list: list, node_fqdn: str):
        """
        Helper function to get the network interface of data node, put it down
        and check if it's not pinging
        :param host_list: list of worker nodes' hosts
        :param node_list: node object list for all worker nodes
        :param node_fqdn: fqdn of the data node
        :return: boolean, response
        """
        for count, host in enumerate(host_list):
            if host == node_fqdn:
                node_ip = CMN_CFG["nodes"][count+1]["ip"]
                resp = node_list[count].execute_cmd(
                    cmd=common_cmd.CMD_IFACE_IP.format(node_ip), read_lines=True)
                node_iface = resp[0].strip(":\n")
                resp = node_list[count].execute_cmd(
                    cmd=common_cmd.CMD_GET_IP_IFACE.format("eth1"), read_lines=True)
                # TODO: Check for HW configuration
                LOGGER.info("Getting another IP from same node %s", node_fqdn)
                new_ip = resp[0].strip("'\\\n'b'")
                new_worker_obj = LogicalNode(hostname=new_ip,
                                             username=CMN_CFG["nodes"][count+1]["username"],
                                             password=CMN_CFG["nodes"][count+1]["password"])
                LOGGER.info("Make %s interface down for %s node", node_iface, host)
                new_worker_obj.execute_cmd(
                    cmd=common_cmd.IP_LINK_CMD.format(node_iface, "down"), read_lines=True)
                resp = system_utils.check_ping(host=node_ip)
                if not resp:
                    return False, node_ip, node_iface, new_worker_obj
                return True, node_ip, node_iface, new_worker_obj
        return False, "Worker node and Fqdn of data node not same"

    @staticmethod
    def create_bucket_chunk_upload(s3_data, bucket_name, file_size, chunk_obj_path, output=None,
                                   bkt_op=True, background=True):
        """
        Helper function to do chunk upload
        :param s3_data: s3 account details
        :param bucket_name: Name of the bucket
        :param file_size: Size of the file to be created to upload
        :param chunk_obj_path: Path of the file to be uploaded
        :param output: Queue used to fill output
        :param bkt_op: Flag to create bucket and object
        :param background: Flag to indicate if background process or not
        :return: response
        """
        jclient_prop = S3_BLKBOX_CFG["jcloud_cfg"]["jclient_properties_path"]
        access_key = s3_data["s3_acc"]["accesskey"]
        secret_key = s3_data["s3_acc"]["secretkey"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])

        if bkt_op:
            LOGGER.info("Creating a bucket with name : %s", bucket_name)
            res = s3_test_obj.create_bucket(bucket_name)
            if not res[0] or res[1] != bucket_name:
                if not background:
                    return False
                output.put(False)
                sys.exit(1)
            LOGGER.info("Created a bucket with name : %s", bucket_name)

            LOGGER.info("Creating object file of 5GB")
            resp = system_utils.create_file(chunk_obj_path, file_size)
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                if not background:
                    return False
                output.put(False)
                sys.exit(1)

        java_cmd = S3_BLKBOX_CFG["jcloud_cfg"]["jclient_cmd"]
        put_cmd = f"{java_cmd} -c {jclient_prop} put {chunk_obj_path} s3://{bucket_name} " \
                  f"--access_key {access_key} --secret_key {secret_key}"
        LOGGER.info("Running command %s", put_cmd)
        resp = system_utils.execute_cmd(put_cmd)
        if not resp:
            if not background:
                return False
            output.put(False)
            sys.exit(1)

        if not background:
            return True
        output.put(True)
        sys.exit(0)

    @staticmethod
    def setup_jclient(jc_obj):
        """
        Helper function to setup jclient
        :param jc_obj: Object for jclient
        :return: response
        """
        LOGGER.info("Setup jClientCloud on runner.")
        res_ls = system_utils.execute_cmd("ls scripts/jcloud/")[1]
        res = ".jar" in res_ls
        if not res:
            res = jc_obj.configure_jclient_cloud(
                source=S3_CFG["jClientCloud_path"]["source"],
                destination=S3_CFG["jClientCloud_path"]["dest"],
                nfs_path=S3_CFG["nfs_path"],
                ca_crt_path=S3_CFG["s3_cert_path"]
            )
            LOGGER.info(res)
            if not res:
                LOGGER.error("Error: jcloudclient.jar or jclient.jar file does not exist")
                return res
        resp = jc_obj.update_jclient_jcloud_properties()
        return resp

    @staticmethod
    def get_config_value(pod_obj, pod_list=None):
        """
        Function to fetch data from file (e.g. conf files)
        :param pod_obj: Object for master node
        :param pod_list: Data pod name list to get the cluster.conf File
        :return: (bool, response)
        """
        if pod_list is None:
            pod_list = pod_obj.get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        conf_cp = common_cmd.K8S_CP_TO_LOCAL_CMD.format(pod_name,
                                                        common_const.CLUSTER_CONF_PATH,
                                                        common_const.LOCAL_CONF_PATH,
                                                        common_const.HAX_CONTAINER_NAME)
        try:
            resp_node = pod_obj.execute_cmd(cmd=conf_cp, read_lines=False)
        except IOError as error:
            LOGGER.exception("Error: Not able to get cluster config file")
            return False, error
        LOGGER.debug("%s response %s ", conf_cp, resp_node)
        local_conf = os.path.join(os.getcwd(), "cluster.conf")
        if os.path.exists(local_conf):
            os.remove(local_conf)
        resp = pod_obj.copy_file_to_local(
            remote_path=common_const.LOCAL_CONF_PATH, local_path=local_conf)
        if not resp[0]:
            LOGGER.error("Error: Failed to copy cluster.conf to local")
            return False, resp
        try:
            with open(local_conf, "r", encoding="utf-8") as file_data:
                data = yaml.safe_load(file_data)
        except IOError as error:
            LOGGER.exception("Error: Not able to read local config file")
            return False, error

        return True, data

    @staticmethod
    def setup_mock_monitor(node_obj):
        """
        :param node_obj: Object for node
        :return: Bool
        """
        LOGGER.info("Get HA pod name for setting up mock monitor")
        ha_pod = node_obj.get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)[0]
        LOGGER.info("Copying file %s to %s", common_const.MOCK_MONITOR_LOCAL_PATH,
                    common_const.MOCK_MONITOR_REMOTE_PATH)
        resp = node_obj.copy_file_to_remote(local_path=common_const.MOCK_MONITOR_LOCAL_PATH,
                                            remote_path=common_const.MOCK_MONITOR_REMOTE_PATH)
        if not resp[0]:
            LOGGER.error("Failed in copy file due to : %s", resp[1])
            return resp[0]

        try:
            LOGGER.info("Convert script in linux compatible format")
            node_obj.execute_cmd(cmd=common_cmd.DOS2UNIX_CMD.format(
                common_const.MOCK_MONITOR_REMOTE_PATH))
            LOGGER.info("Changing access mode of file")
            node_obj.execute_cmd(cmd=common_cmd.FILE_MODE_CHANGE_CMD.format(
                common_const.MOCK_MONITOR_REMOTE_PATH))
            LOGGER.info("Copying file inside pod %s", ha_pod)
            node_obj.execute_cmd(common_cmd.HA_COPY_CMD.format(
                common_const.MOCK_MONITOR_REMOTE_PATH, ha_pod,
                common_const.MOCK_MONITOR_REMOTE_PATH))
        except IOError as error:
            LOGGER.exception("Failed to copy %s inside ha pod %s due to error: %s",
                             common_const.MOCK_MONITOR_LOCAL_PATH, ha_pod, error)
            return False
        return True

    def simulate_disk_cvg_failure(self, node_obj, source: str, resource_status: str,
                                  resource_type: str, node_type: str = 'data',
                                  resource_cnt: int = 1, node_cnt: int = 1, **kwargs):
        """
        Function to simulate disk cvg failure
        :param node_obj: Object for node
        :param source: Source of the event | monitor, ha, hare, etc.
        :param resource_status: recovering, online, failed, unknown, degraded, repairing,
        repaired, rebalancing, offline, etc.
        :param resource_type: node, cvg, disk, etc.
        :param node_type: Type of the node (data, server)
        :param resource_cnt: Count of the resources
        :param node_cnt: Count of the nodes on which failure to be simulated
        :keyword delay: Delay between two events (Optional)
        :keyword specific_info: Dictionary with Key-value
        pairs e.g. "generation_id": "xxxx"(Optional)
        :keyword node_id: node_id of the pod (Optional)
        :keyword resource_id: resource_id of the pod (Optional)
        Format of events file:
        {
        "events":
            {
                "1": { # Any key
                    "source": "hare", # Source of the event, monitor, ha, hare, etc.
                    "node_id": "xxxx", # Node id fetched with -gdt/-gs arguments above.
                    "resource_type": "node", # Resource type, node, cvg, disk, etc.
                    "resource_id": "xxxx", # Resource id fetched with -gdt/-gs/get-cvgs/get-disks
                    options above.
                    "resource_status": "online", # Resource status, recovering, online, failed,
                    unknown, degraded, repairing, repaired, rebalancing, offline, etc.
                    "specific_info": {} # Key-value pairs e.g. "generation_id": "xxxx"
                    },
                # Repeat the dictionary above with specific values if multiple events to be sent
            },
        "delay": xxxx # If present this will add delay of specified seconds between the events
        }
        :return: Bool, config_dict/error
        """
        delay = kwargs.get("delay", None)
        specific_info = kwargs.get("specific_info", dict())
        node_id = kwargs.get("node_id", None)
        resource_id = kwargs.get("resource_id", None)
        config_json_file = "config_mock.json"
        config_dict = dict()
        config_dict["events"] = {}
        node_id_list = self.get_node_resource_ids(node_obj=node_obj, r_type='node',
                                                  n_type=node_type)
        if len(node_id_list) < node_cnt:
            LOGGER.error("Please provide correct count for nodes")
            return False, node_id_list
        count = 0
        user_val = False
        if node_id and resource_id:
            # If user provide node_id and resource_id
            n_id = node_id
            r_id = resource_id
            user_val = True
        elif node_id and resource_type == 'node':
            # If user provide node_id
            n_id = node_id
            r_id = node_id
            user_val = True
        elif resource_id and resource_type == 'node':
            # If user provide resource_id
            n_id = resource_id
            r_id = resource_id
            user_val = True
        for n_cnt in range(node_cnt):
            if resource_type != 'node':
                resource_id_list = self.get_node_resource_ids(node_obj=node_obj,
                                                              r_type=resource_type,
                                                              node_id=node_id_list[n_cnt])
            else:
                resource_id_list = node_id_list
            if len(resource_id_list) < resource_cnt:
                LOGGER.error("Please provide correct count for resources")
                return False, resource_id_list
            for d_cnt in range(resource_cnt):
                count += 1
                config_dict["events"][f"{count}"] = {}
                config_dict["events"][f"{count}"]["resource_type"] = resource_type
                config_dict["events"][f"{count}"]["source"] = source
                config_dict["events"][f"{count}"]["resource_status"] = resource_status
                if user_val:
                    config_dict["events"][f"{count}"]["node_id"] = n_id
                    config_dict["events"][f"{count}"]["resource_id"] = r_id
                else:
                    # If user don't provide anything
                    config_dict["events"][f"{count}"]["node_id"] = node_id_list[n_cnt]
                    config_dict["events"][f"{count}"]["resource_id"] = resource_id_list[d_cnt]
                config_dict["events"][f"{count}"]["specific_info"] = specific_info
        if delay:
            config_dict["delay"] = delay
        with open(config_json_file, "w", encoding="utf-8") as outfile:
            json.dump(config_dict, outfile)
        LOGGER.info("Publishing mock events: %s", config_dict)
        LOGGER.info("Get HA pod name for publishing event")
        ha_pod = node_obj.get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)[0]
        LOGGER.info("Publishing event %s for %s resource type through ha pod %s", resource_status,
                    resource_type, ha_pod)
        resp = node_obj.copy_file_to_remote(local_path=config_json_file,
                                            remote_path=common_const.HA_CONFIG_FILE)
        if not resp[0]:
            LOGGER.error("Failed in copy file due to : %s", resp[1])
            return resp[0]
        cmd = common_cmd.PUBLISH_CMD.format(common_const.MOCK_MONITOR_REMOTE_PATH,
                                            common_const.HA_CONFIG_FILE)
        try:
            node_obj.execute_cmd(
                cmd=common_cmd.K8S_CP_TO_CONTAINER_CMD.format
                (common_const.HA_CONFIG_FILE, ha_pod,
                 common_const.HA_CONFIG_FILE, common_const.HA_FAULT_TOLERANCE_CONTAINER_NAME))
            node_obj.send_k8s_cmd(operation="exec", pod=ha_pod,
                                  namespace=common_const.NAMESPACE + " -- ", command_suffix=cmd,
                                  decode=True)
        except IOError as error:
            LOGGER.exception("Failed to publish the event due to error: %s", error)
            return False, error

        return True, config_dict

    @staticmethod
    def get_node_resource_ids(node_obj, r_type, n_type=None, node_id=None):
        """
        Function to get node resource ids
        :param node_obj: Object of master node
        :param r_type: Type of resource (node, disk, cvg)
        :param n_type: Type of the node (data, server)
        :param node_id: ID of node from which resource IDs to be extracted (Required only for
        disk and cvg)
        :return: List
        """
        switcher = {
            'node': {
                'data': {
                    'cmd': common_cmd.GET_DATA_NODE_ID_CMD.format(
                        common_const.MOCK_MONITOR_REMOTE_PATH)},
                'server': {
                    'cmd': common_cmd.GET_SERVER_NODE_ID_CMD.format(
                        common_const.MOCK_MONITOR_REMOTE_PATH)}},
            'disk': {
                'cmd': common_cmd.GET_DISK_ID_CMD.format(common_const.MOCK_MONITOR_REMOTE_PATH,
                                                         node_id)},
            'cvg': {
                'cmd': common_cmd.GET_CVG_ID_CMD.format(common_const.MOCK_MONITOR_REMOTE_PATH,
                                                        node_id)}
        }

        LOGGER.info("Get HA pod name for publishing event")
        ha_pod = node_obj.get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)[0]
        if r_type == 'node':
            cmd = switcher[r_type][n_type]['cmd']
        else:
            cmd = switcher[r_type]['cmd']
        LOGGER.info("Running command %s on pod %s", cmd, ha_pod)
        try:
            resp = node_obj.send_k8s_cmd(operation="exec", pod=ha_pod,
                                         namespace=common_const.NAMESPACE + " -- ",
                                         command_suffix=cmd, decode=True)
            resp = literal_eval(resp)
        except IOError as error:
            LOGGER.error("Failed to get resource IDs for %s", r_type)
            LOGGER.exception("Error in %s: %s", HAK8s.get_node_resource_ids.__name__, error)
            raise error

        LOGGER.info("Resource IDs for %s are: %s", r_type, resp)
        return resp

    def delete_kpod_with_shutdown_methods(self, master_node_obj, health_obj,
                                          pod_prefix=None, kvalue=1, delete_pod=None,
                                          down_method=common_const.RESTORE_SCALE_REPLICAS,
                                          event=None, event_set_clr=None, num_replica=0):
        """
        Delete K pods by given shutdown method. Check and verify deleted/remaining pod's services
        status, cluster status
        :param master_node_obj: Master node object list
        :param health_obj: Health object
        :param pod_prefix: Pod prefix to be deleted (Expected List type)
        :param down_method: Pod shutdown/delete method.
        :param kvalue: Number of pod to be shutdown/deleted.
        :param delete_pod: pod name to be deleted (optional)
        :param event_set_clr: Thread event set-clear flag reference when s3bench workload
        execution miss the event set-clear time window
        :param event: Thread event to set/clear before/after pods/nodes
        :param num_replica: Number of replicas of the pod to be created
        shutdown with parallel IOs
        return : tuple
        """
        if pod_prefix is None:
            pod_prefix = [common_const.POD_NAME_PREFIX]
        pod_info = dict()
        total_pod_type = [common_const.POD_NAME_PREFIX, common_const.SERVER_POD_NAME_PREFIX]
        pod_data = {"method": None, "deployment_name": None, "deployment_backup": None,
                    "hostname": None}
        delete_pods = list()
        remaining = list()
        if delete_pod is not None:
            delete_pods.extend(delete_pod)
        else:
            for ptype in pod_prefix:
                pod_list = master_node_obj.get_all_pods(pod_prefix=ptype)
                # Get the list of Kvalue pods to be deleted for given pod_prefix list
                delete_pods.extend(random.sample(pod_list, kvalue))

        LOGGER.info("Get the list of all pods of total pod types.")
        for ptype in total_pod_type:
            remaining.extend(master_node_obj.get_all_pods(pod_prefix=ptype))

        LOGGER.info("Delete %s by %s method", delete_pods, down_method)
        for pod in delete_pods:
            hostname = master_node_obj.get_pod_hostname(pod_name=pod)
            if event is not None:
                LOGGER.debug("Setting the Thread event")
                event.set()
            LOGGER.info("Deleting pod %s by %s method", pod, down_method)
            if down_method == common_const.RESTORE_SCALE_REPLICAS:
                resp = master_node_obj.create_pod_replicas(num_replica=num_replica, pod_name=pod)
                if resp[0]:
                    return False, pod_info
                pod_info[pod] = pod_data.copy()
                pod_info[pod]['deployment_name'] = resp[1]
            elif down_method == common_const.RESTORE_DEPLOYMENT_K8S:
                resp = master_node_obj.delete_deployment(pod_name=pod)
                if resp[0]:
                    return False, pod_info
                pod_info[pod] = pod_data.copy()
                pod_info[pod]['deployment_backup'] = resp[1]
                pod_info[pod]['deployment_name'] = resp[2]
            pod_info[pod]['method'] = down_method
            pod_info[pod]['hostname'] = hostname
            if event is not None:
                LOGGER.debug("Clearing the Thread event and setting event set_clear flag")
                event.clear()
                if isinstance(event_set_clr, list):
                    event_set_clr[0] = True
            LOGGER.info("Check services status that were running on pod %s", pod)
            resp = health_obj.get_pod_svc_status(pod_list=[pod], fail=True,
                                                 hostname=pod_info[pod]['hostname'])
            LOGGER.debug("Response: %s", resp)
            if not resp[0] or False in resp[1]:
                return False, pod_info
        LOGGER.info("Successfully deleted %s by %s method", delete_pods, down_method)

        LOGGER.info("Check cluster status")
        resp = self.check_cluster_status(master_node_obj)
        if resp[0]:
            return False, pod_info
        LOGGER.info("Cluster has failures as pod %s has been shutdown", delete_pods)

        # Get the remaining pods except deleted one, to check its service status not affected
        remaining_pods = list(set(remaining) - set(delete_pods))
        LOGGER.info("Check services status on remaining pods %s", remaining_pods)
        resp = health_obj.get_pod_svc_status(pod_list=remaining_pods, fail=False)
        LOGGER.debug("Response: %s", resp)
        if not resp[0]:
            return False, pod_info
        LOGGER.info("Services of remaining pods are in online state")
        return True, pod_info

    def get_replace_recursively(self, search_dict, field, replace_key=None, replace_val=None):
        """
        Function to find value from nested dicts and nested lists for given key and replace it
        :param search_dict: Dict in which key to be searched
        :param field: Key to be searched
        :param replace_key: Key with which older key to be replaced
        :param replace_val: Value with which older value to be replaced
        :return: str (value)
        """
        fields_found = []
        for key, value in search_dict.items():
            if key == field:
                fields_found.append(value)
                if replace_key:
                    search_dict[replace_key] = search_dict.pop(key)
                    search_dict[replace_key] = replace_val
            elif isinstance(value, dict):
                results = self.get_replace_recursively(value, field, replace_key, replace_val)
                for result in results:
                    fields_found.append(result)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        more_results = self.get_replace_recursively(item, field, replace_key,
                                                                    replace_val)
                        for another_result in more_results:
                            fields_found.append(another_result)

        return fields_found

    def update_deployment_yaml(self, pod_obj, pod_name, find_key, replace_key=None,
                               replace_val=None):
        """
        Function to find and replace key from deployment yaml file
        :param pod_obj: Object of pod
        :param pod_name: Name of the pod
        :param find_key: Key to be searched
        :param replace_key: Key with which older key to be replaced
        :param replace_val: Value with which older value to be replaced
        :return: bool, str, str (status, new path, backup path)
        """
        resp = pod_obj.get_deploy_replicaset(pod_name)
        deploy = resp[1]
        LOGGER.info("Deployment for pod %s is %s", pod_name, deploy)
        LOGGER.info("Taking deployment backup")
        resp = pod_obj.backup_deployment(deploy)
        yaml_path = resp[1]
        modified_yaml = os.path.join("/root", f"{pod_name}_modified.yaml")
        LOGGER.info("Copy deployment yaml file to local system")
        pod_obj.copy_file_to_local(remote_path=yaml_path, local_path=modified_yaml)
        resp = config_utils.read_yaml(modified_yaml)
        if not resp[0]:
            return resp
        data = resp[1]
        LOGGER.info("Update %s of deployment yaml with %s : %s", find_key, replace_key, replace_val)
        val = self.get_replace_recursively(data, find_key, replace_key, replace_val)
        if not val:
            return False, f"Failed to find key {find_key} in deployment yaml {yaml_path} of pod " \
                          f"{pod_name}"
        resp = config_utils.write_yaml(fpath=modified_yaml, write_data=data, backup=True,
                                       sort_keys=False)
        LOGGER.debug("Response: %s", resp)
        if not resp[0]:
            return resp
        LOGGER.info("Copying files %s to master node", modified_yaml)
        resp = pod_obj.copy_file_to_remote(local_path=modified_yaml, remote_path=modified_yaml)
        if not resp[0]:
            return resp

        system_utils.remove_file(modified_yaml)
        LOGGER.info("Successfully updated deployment yaml file for pod %s", pod_name)
        return True, modified_yaml, yaml_path

    @staticmethod
    def change_pod_node(pod_obj, pod_node):
        """
        Function to change the node of given pod list (NodeSelector)
        :param pod_obj: Object of the pod
        :param pod_node: Dict of the pod: failover_node (Node to which pod is to be failed over)
        :return: bool, str (status, response)
        """
        for pod, failover_node in pod_node.items():
            pod_prefix = '-'.join(pod.split("-")[:2])
            cur_node = pod_obj.get_pods_node_fqdn(pod_prefix).get(pod)
            LOGGER.info("Pod %s is hosted on %s", pod, cur_node)

            LOGGER.info("Failing over pod %s to node %s", pod, failover_node)
            deploy = pod_obj.get_deploy_replicaset(pod)[1]
            cmd = common_cmd.K8S_CHANGE_POD_NODE.format(deploy, failover_node)
            try:
                resp = pod_obj.execute_cmd(cmd=cmd, read_lines=True)
                LOGGER.debug("Response: %s", resp)
                LOGGER.info("Successfully failed over pod %s to node %s", pod, failover_node)
                return True, resp
            except IOError as error:
                LOGGER.exception("Failed to failover pod %s to %s due to error: %s", pod,
                                 failover_node, error)
                return False, error

    def mark_resource_failure(self, mnode_obj, pod_list: list, go_random: bool = True,
                              rsc_opt: str = "mark_node_failure", rsc: str = "node",
                              validate_set: bool = True):
        """
        Helper function to set resource status to Failed random if go_random
        :param pod_list: List of resource to be marked as failed
        :param go_random: If True, send mark failure signal to resource randomly
        :param mnode_obj: Master node object to fetch the resource ID
        :param rsc_opt: Operation to be performed on resource (e.g. mark_node_failure)
        :param rsc: resource type (e.g. node, cluster)
        :param validate_set: If set to TRUE, its validate SET failure for resource
        :return: bool, response
        """
        if rsc == 'node':
            pod_info = {}
            pod_data = {'id': None, 'status': 'offline'}
            for pod in pod_list:
                pod_info[pod] = pod_data.copy()
                pod_info[pod]['id'] = mnode_obj.get_machine_id_for_pod(pod)

            for pod in pod_list:
                set_fail = self.system_random.choice([True, False]) if go_random else True
                if set_fail:
                    LOGGER.info('Marking %s pod as failed', pod)
                    data_val = {"operation": rsc_opt,
                                "arguments": {"id": f"{pod_info[pod]['id']}"}}
                    resp = self.system_health.set_resource_signal(req_body=data_val, resource=rsc)
                    if not resp[0]:
                        return False, pod_info, f"Failed to set failure status for {pod}"
                    pod_info[pod]['status'] = 'failed'
                    LOGGER.info("Sleeping for %s sec.", HA_CFG["common_params"]["30sec_delay"])
                    time.sleep(HA_CFG["common_params"]["30sec_delay"])
            if validate_set:
                LOGGER.info("Validating nodes/pods status is SET as expected.")
                return self.get_validate_resource_status(rsc_info=pod_info)
            return True, pod_info, f"{pod_list} marked as failed"
        return False, f"Mark failure for {rsc} is not supported yet"

    # pylint: disable=W1624
    def get_validate_resource_status(self, rsc_info, exp_sts=None,
                                     mnode_obj=None, rsc: str = "node"):
        """
        Helper function to get and validate resource status
        :param exp_sts: Expected status of resource
        :param rsc_info: Required resource to get its status,
        dict with {pod1:{'id':, 'status':},..} or list of pods
        :param rsc: resource type (e.g. node, cluster)
        :param mnode_obj: Master node object to fetch the resource ID
        :return: bool, response
        """
        if rsc == "node":
            if not isinstance(rsc_info, dict):
                # Get the node ID and set expected status if only list of pods is passed
                LOGGER.info("Get the nodes ID for GET API.")
                pod_info = {}
                pod_data = {'id': None, 'status': "online"}
                for pod in rsc_info:
                    pod_info[pod] = pod_data.copy()
                    pod_info[pod]['id'] = mnode_obj.get_machine_id_for_pod(pod)
                    pod_info[pod]['status'] = exp_sts
            else:
                pod_info = rsc_info.copy()
            for pod in pod_info.keys():
                LOGGER.info("Get and verify pod %s status is as expected", pod)
                resp = self.poll_to_get_resource_status(exp_sts=pod_info[pod]['status'], rsc=rsc,
                                                        rsc_id=pod_info[pod]['id'])
                if not resp:
                    return False, f"Failed to get expected status for {pod}"
        elif rsc == "cluster":
            # Get the cluster ID and verify the cluster status to Expected
            LOGGER.info("Get the cluster ID for GET API and verify cluster status.")
            data = self.get_config_value(mnode_obj)
            if not data[0]:
                return False, "Failed to get cluster ID"
            if not exp_sts and isinstance(rsc_info, dict):
                exp_sts = "online"
                for pod in rsc_info.keys():
                    # If 1 node is offline, cluster will be in degraded
                    if rsc_info[pod]['status'] == "offline" or rsc_info[pod]['status'] == "failed":
                        exp_sts = "degraded"
                        break
            LOGGER.info("Get and verify cluster status is set to %s", exp_sts)
            resp = self.poll_to_get_resource_status(exp_sts=exp_sts, rsc=rsc,
                                                    rsc_id=data[1]["cluster"]["id"])
            if not resp:
                return False, "Failed to get expected status for Cluster"
        return True, f"Got expected status for {rsc}"

    def poll_to_get_resource_status(self, exp_sts, rsc, rsc_id,
                                    timeout=HA_CFG["common_params"]["90sec_delay"]):
        """
        Helper function to GET and Poll for expected resource status till timeout
        :param exp_sts: Expected status of resource
        :param rsc_id: Required resource ID to GET the resource status
        :param rsc: resource type (e.g. node, cluster)
        :param timeout: Poll for expected status till timeout
        :return: bool
        """
        resp = self.system_health.get_resource_status(resource_id=rsc_id, resource=rsc)
        if not resp[0]:
            return False
        status = resp[1]['status']
        poll = time.time() + timeout
        sleep_time = HA_CFG["common_params"]["2sec_delay"]
        while status != exp_sts and poll > time.time():
            LOGGER.info("Current %s status is %s. Sleeping for %s sec", rsc, status, sleep_time)
            time.sleep(sleep_time)
            resp = self.system_health.get_resource_status(resource_id=rsc_id, resource=rsc)
            if not resp[0]:
                return False
            status = resp[1]['status']
            # Gradually increase in time by multiple of 2 to get node/pod status
            sleep_time = sleep_time * 2
        # Verify we got the expected status within Polling time
        if status != exp_sts:
            return False
        return True

    @staticmethod
    def get_rc_node(node_obj):
        """
        To get the primary cortx node name (RC node)
        :param node_obj: object for master node
        :return: Primary(RC) node name in the cluster
        :rtype: str
        """
        data_pod = node_obj.get_pod_name(pod_prefix=common_const.POD_NAME_PREFIX)[1]
        cmd = " | awk -F ' '  '/(RC)/ { print $1 }'"
        rc_node = node_obj.send_k8s_cmd(operation="exec", pod=data_pod,
                                        namespace=common_const.NAMESPACE,
                                        command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                                        f"-- {common_cmd.MOTR_STATUS_CMD} {cmd}", decode=True)
        return rc_node

    def failover_pod(self, pod_obj, pod_yaml, failover_node):
        """
        Helper function to delete, recreate and failover pod
        :param pod_obj: Object of the pod
        :param pod_yaml: Dict containing pod name and yaml file to be used for recreation
        :param failover_node: Node FQDN to which pod is to be failed over
        :return: bool, tuple
        """
        for pod, yaml_f in pod_yaml.items():
            LOGGER.info("Deleting deployment for pod %s", pod)
            resp = pod_obj.delete_deployment(pod_name=pod)
            if resp[0]:
                return False, f"Failed to delete pod {pod} by deleting deployment"
            deploy = resp[2]
            LOGGER.info("Recreating deployment for pod %s using yaml file %s", pod, yaml_f)
            resp = pod_obj.recover_deployment_k8s(yaml_f, deploy)
            if not resp[0]:
                return resp
            new_pod = pod_obj.get_recent_pod_name(deployment_name=deploy)
            LOGGER.info("Changing host node of pod %s to %s", pod, failover_node)
            resp = self.change_pod_node(pod_obj, pod_node={new_pod: failover_node})
            if not resp[0]:
                return resp
            LOGGER.info("Check cluster status")
            resp = self.poll_cluster_status(pod_obj)
            if not resp[0]:
                return resp

        return True, f"Successfully failed over pods {list(pod_yaml.keys())}"

    def iam_bucket_cruds(self, event, s3_obj=None, user_crud=False, num_users=None, bkt_crud=False,
                         num_bkts=None, del_users_dict=None, output=None, **kwargs):
        """
        Function to perform iam user and bucket crud operations in loop (To be used for background)
        :param event: event to intimate thread about main thread operations
        :param s3_obj: s3 test lib object
        :param user_crud: Flag for performing iam user crud operations
        :param num_users: Number of iam users to be created and deleted
        :param bkt_crud: Flag for performing bucket crud operations
        :param num_bkts: Number of buckets to be created and deleted
        :param del_users_dict: Dict of users to be deleted
        :param output: Output queue in which results should be put
        :keyword header: Obtained header pass for IAM create/delete REST requests
        :return: Queue containing output lists
        """
        header = kwargs.get("header", False)
        exp_fail = list()
        failed = list()
        created_users = list()
        user_del_failed = list()
        user = None
        del_users = list(del_users_dict.keys()) if del_users_dict else list()
        if user_crud:
            LOGGER.info("Create and delete %s IAM users in loop", num_users)
            for i_i in range(num_users):
                try:
                    LOGGER.debug("Creating %s user", i_i)
                    user = None
                    if not header:
                        user = self.mgnt_ops.create_account_users(nusers=1)
                    else:
                        user = self.create_iam_user_with_header(header=header)
                    if user is None:
                        if event.is_set():
                            exp_fail.append(user)
                        else:
                            failed.append(user)
                    else:
                        created_users.append(user)
                except (CTException, req_exception.ConnectionError, req_exception.ConnectTimeout) \
                        as error:
                    LOGGER.exception("Error: %s", error)
                    if event.is_set():
                        exp_fail.append(user)
                    else:
                        failed.append(user)

                if len(del_users) > i_i:
                    LOGGER.debug("Deleting %s user", del_users[i_i])
                    user = del_users[i_i]
                    if not header:
                        resp = self.delete_s3_acc_buckets_objects({user: del_users_dict[user]})
                    else:
                        resp = self.delete_iam_user_with_header({user: del_users_dict[user]},
                                                                header)
                    if not resp[0]:
                        user_del_failed.append(user)
                        if event.is_set():
                            exp_fail.append(user)
                        else:
                            failed.append(user)

            result = (exp_fail, failed, user_del_failed, created_users)
            output.put(result)
        if bkt_crud:
            self.bucket_cruds(event, s3_obj, num_bkts=num_bkts, output=output)

    @staticmethod
    def bucket_cruds(event, s3_obj, num_bkts=None, output=None):
        """
        Function to perform iam user and bucket crud operations in loop (To be used for background)
        :param event: event to intimate thread about main thread operations
        :param s3_obj: s3 test lib object
        :param num_bkts: Number of buckets to be created and deleted
        :param output: Output queue in which results should be put
        :return: Queue containing output lists
        """
        LOGGER.info("Create and delete %s buckets in loop", num_bkts)
        exp_fail = list()
        failed = list()
        bucket_name = None
        for i_i in range(num_bkts):
            try:
                bucket_name = f"bkt-loop-{i_i}"
                res = s3_obj.create_bucket(bucket_name)
                if res[1] != bucket_name:
                    if event.is_set():
                        exp_fail.append(bucket_name)
                    else:
                        failed.append(bucket_name)
                    break
                s3_obj.delete_bucket(bucket_name=bucket_name, force=True)
                LOGGER.debug("Created and deleted %s bucket successfully", i_i)
            except CTException as error:
                LOGGER.exception("Error: %s", error)
                if event.is_set():
                    exp_fail.append(bucket_name)
                else:
                    failed.append(bucket_name)

        result = (exp_fail, failed)
        output.put(result)

    @staticmethod
    def object_download_jclient(s3_data, bucket_name, object_name, obj_download_path):
        """
        Function to download object using jclient tool
        :param s3_data: s3 account details
        :param bucket_name: Name of the bucket
        :param object_name: Name of the object
        :param obj_download_path: Path of the file to which object is to be downloaded
        :return: response
        """
        jclient_prop = S3_BLKBOX_CFG["jcloud_cfg"]["jclient_properties_path"]
        access_key = s3_data["s3_acc"]["accesskey"]
        secret_key = s3_data["s3_acc"]["secretkey"]
        java_cmd = S3_BLKBOX_CFG["jcloud_cfg"]["jclient_cmd"]
        get_cmd = f"{java_cmd} -c {jclient_prop} get s3://{bucket_name}/{object_name} " \
                  f"--access_key {access_key} --secret_key {secret_key} {obj_download_path}"
        LOGGER.info("Running command %s", get_cmd)
        resp = system_utils.execute_cmd(get_cmd)
        return resp

    def dnld_obj_verify_chcksm(self, s3_test_obj, bucket, obj, download_path, upload_checksum):
        """
        Function to download the object and verify its checksum
        :param s3_test_obj: Object of the s3 test lib
        :param bucket: Name of the bucket
        :param obj: Name of the object
        :param download_path: Path to which object is to be downloaded
        :param upload_checksum: Checksum of uploaded object
        :return: Tuple (bool, string)
        """
        LOGGER.info("Download object %s from bucket %s", obj, bucket)
        resp = s3_test_obj.object_download(bucket, obj, download_path)
        LOGGER.info("Download object response: %s", resp)
        if not resp[0]:
            return resp
        download_checksum = self.cal_compare_checksum(file_list=[download_path], compare=False)[0]
        if upload_checksum != download_checksum:
            LOGGER.info("Failed to match checksums. \nUpload checksum:%s Download checksum: %s",
                        upload_checksum, download_checksum)
            return False, download_checksum
        LOGGER.info("Successfully downloaded the object and verified the checksum")
        return True, download_checksum

    @staticmethod
    def form_endpoint_port(pod_obj, pod_list, port_name="rgw-https"):
        """
        Function to form endpoints using pod ip and port
        :param pod_obj: Object of master node
        :param pod_list: List of pods
        :param port_name: Name of the port, e.g. https, http, etc
        :return: dict
        """
        pod_ep_dict = dict()
        ports = pod_obj.get_pod_ports(pod_list, port_name)
        for pod in pod_list:
            pod_prefix = "-".join(pod.split("-")[:2])
            LOGGER.info("Getting internal IPs of %s pods", pod_prefix)
            pod_ip = pod_obj.get_all_pods_and_ips(pod_prefix)[pod]
            port = ports[pod]
            ip_port = f"{pod_ip}:{port}"
            pod_ep_dict[pod] = ip_port

        return pod_ep_dict

    def create_iam_user_with_header(self, num_users=1, header=None):
        """
        Function create IAM user with give header info.
        :param num_users: Int count for number of IAM user creation
        :param header: Existing header to use for IAM user creation post request
        :return: None if IAM user REST req fails or Dict response for IAM user successful creation
        """
        user = None
        payload = {}
        endpoint = CSM_REST_CFG["s3_iam_user_endpoint"]
        for i_d in range(num_users):
            name = f"ha_iam_{i_d}_{time.perf_counter_ns()}"
            payload.update({"uid": name})
            payload.update({"display_name": name})
            LOGGER.info("Creating IAM user request....")
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
        :param user: IAM user info dict to be deleted
        :param header: Existing header to use for IAM user delete request
        :return: Tuple
        """
        del_user = list(user.keys())
        failed_del = []
        try:
            for i_i in range(len(del_user)):
                user_del = del_user[i_i]
                endpoint = CSM_REST_CFG["s3_iam_user_endpoint"] + "/" + user_del
                LOGGER.info("Sending Delete %s request...", user_del)
                response = self.restapi.rest_call("delete", endpoint=endpoint, headers=header)
                if response.status_code != HTTPStatus.OK:
                    failed_del.append(user)
                    LOGGER.debug(response)
        except (req_exception.ConnectionError, req_exception.ConnectTimeout) as error:
            LOGGER.exception("Error: %s", error)
            failed_del.append(user)
        if failed_del:
            return False, failed_del
        return True, "User deleted successfully"
