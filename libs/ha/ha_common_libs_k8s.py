#!/usr/bin/python  # pylint: disable=C0302
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
import logging
import os
import random
import sys
import time
import copy
from multiprocessing import Process
from time import perf_counter_ns
import yaml
import json
from ast import literal_eval

from commons import commands as common_cmd
from commons import constants as common_const
from commons import pswdmanager
from commons.constants import Rest as Const
from commons.exceptions import CTException
from commons.helpers.pods_helper import LogicalNode
from commons.utils import system_utils
from commons.utils.system_utils import run_local_cmd
from config import CMN_CFG, HA_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.di.di_mgmt_ops import ManagementOPs
from libs.di.di_run_man import RunDataCheckManager
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench
from config.s3 import S3_BLKBOX_CFG

LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
# pylint: disable=R0904
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
        self.dir_path = common_const.K8S_SCRIPTS_PATH

    def polling_host(self,
                     max_timeout: int,
                     host: str,
                     exp_resp: bool,
                     bmc_obj=None):
        """
        Helper function to poll for host ping response.
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
                    LOGGER.info(f"Unable to get VM power status for {vm_name}")
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

    def status_pods_online(self, no_pods: int):
        """
        Helper function to check that all Pods are shown online in cortx REST
        :param no_pods: Number of pods in the cluster
        :return: boolean
        """
        # Future: Right now system health api is not available but will be implemented after M0
        check_rem_pod = ["online" for _ in range(no_pods)]
        rest_resp = self.system_health.verify_node_health_status_rest(exp_status=check_rem_pod)
        LOGGER.info("REST response for pods health status. %s", rest_resp[1])
        return rest_resp

    def status_cluster_resource_online(self):
        """
        Check cluster/rack/site/pods are shown online in Cortx REST
        :return: boolean
        """
        LOGGER.info("Check cluster/rack/site/pods health status.")
        resp = self.check_csrn_status(csr_sts="online", pod_sts="online", pod_id=0)
        LOGGER.info("Health status response : %s", resp[1])
        if resp[0]:
            LOGGER.info("cluster/rack/site/pods health status is online in REST")
        return resp

    def check_csrn_status(self, csr_sts: str, pod_sts: str, pod_id: int):
        """
        Check cluster/rack/site/pod status with expected status using REST
        :param csr_sts: cluster/rack/site's expected status
        :param pod_sts: Pod's expected status
        :param pod_id: Pod ID to check for expected status
        :return: (bool, response)
        """
        check_rem_pod = [
            pod_sts if num == pod_id else "online" for num in range(self.num_pods)]
        LOGGER.info("Checking pod-%s status is %s via REST", pod_id+1, pod_sts)
        resp = self.system_health.verify_node_health_status_rest(
            check_rem_pod)
        if not resp[0]:
            return resp
        LOGGER.info("Checking Cluster/Site/Rack status is %s via REST", csr_sts)
        resp = self.system_health.check_csr_health_status_rest(csr_sts)
        if not resp[0]:
            return resp

        return True, f"cluster/rack/site status is {csr_sts} and \
        pod-{pod_id+1} is {pod_sts} in Cortx REST"

    def delete_s3_acc_buckets_objects(self, s3_data: dict):
        """
        This function deletes all s3 buckets objects for the s3 account
        and all s3 accounts
        :param s3_data: Dictionary for s3 operation info
        :return: (bool, response)
        """
        try:
            for details in s3_data.values():
                s3_del = S3TestLib(endpoint_url=S3_CFG["s3_url"],
                                   access_key=details['accesskey'],
                                   secret_key=details['secretkey'])
                response = s3_del.delete_all_buckets()
                if not response[0]:
                    return response
                response = self.s3_rest_obj.delete_s3_account(details['user_name'])
                if not response[0]:
                    return response
            return True, "Successfully performed S3 operation clean up"
        except (ValueError, KeyError, CTException) as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HAK8s.delete_s3_acc_buckets_objects.__name__,
                         error)
            return False, error

    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-locals
    def perform_ios_ops(
            self,
            prefix_data: str = None,
            nusers: int = 2,
            nbuckets: int = 2,
            files_count: int = 10,
            di_data: tuple = None,
            is_di: bool = False):
        """
        This function creates s3 acc, buckets and performs IO.
        This will perform DI check if is_di True and once done,
        deletes all the buckets and s3 accounts created.
        :param prefix_data: Prefix data for IO Operation
        :param nusers: Number of s3 user
        :param nbuckets: Number of buckets per s3 user
        :param files_count: NUmber of files to be uploaded per bucket
        :param di_data: Data for DI check operation
        :param is_di: To perform DI check operation
        :return: (bool, response)
        """
        try:
            if not is_di:
                LOGGER.info("create s3 acc, buckets and upload objects.")
                users = self.mgnt_ops.create_account_users(nusers=nusers)
                io_data = self.mgnt_ops.create_buckets(nbuckets=nbuckets, users=users)
                run_data_chk_obj = RunDataCheckManager(users=io_data)
                pref_dir = {"prefix_dir": prefix_data}
                star_res = run_data_chk_obj.start_io(users=io_data, buckets=None, prefs=pref_dir,
                                                     files_count=files_count)
                if not star_res:
                    return False, star_res
                return True, run_data_chk_obj, io_data
            LOGGER.info("Checking DI for IOs run.")
            stop_res = di_data[0].stop_io(users=di_data[1], di_check=is_di)
            if not stop_res[0]:
                return stop_res
            del_resp = self.delete_s3_acc_buckets_objects(di_data[1])
            if not del_resp[0]:
                return del_resp
            return True, "Di check for IOs passed successfully"
        except ValueError as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         HAK8s.perform_ios_ops.__name__,
                         error)
            return False, error

    def perform_io_read_parallel(self, di_data, is_di=True, start_read=True):
        """
        This function runs parallel async stop_io function until called again with
        start_read with False.
        :param di_data: Tuple of RunDataCheckManager obj and User-bucket info from
        WRITEs call
        :param is_di: IF DI check is required on READ objects
        :param start_read: If True, function will start the parallel READs
        and if False function will Stop the parallel READs
        :return: bool/Process object or stop process status
        """
        if start_read:
            self.parallel_ios = Process(
                target=di_data[0].stop_io, args=(di_data[1], is_di))
            self.parallel_ios.start()
            return_val = (True, self.parallel_ios)
        else:
            if self.parallel_ios.is_alive():
                self.parallel_ios.join()
            LOGGER.info(
                "Parallel IOs stopped: %s",
                not self.parallel_ios.is_alive())
            return_val = (not self.parallel_ios.is_alive(), "Failed to stop parallel READ IOs.")
        return return_val

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
            large_workload: bool = False):
        """
        This function creates s3 acc, buckets and performs WRITEs/READs/DELETEs
        operations on VM/HW.
        :param log_prefix: Test number prefix for log file
        :param s3userinfo: S3 user info
        :param skipread: Skip reading objects created in this run if True
        :param skipwrite: Skip writing objects created in this run if True
        :param skipcleanup: Skip deleting objects created in this run if True
        :param nsamples: Number of samples of object
        :param nclients: Number of clients/workers
        :param large_workload: Flag to start large workload IOs
        :return: bool/operation response
        """
        workloads = copy.deepcopy(HA_CFG["s3_bench_workloads"])
        if self.setup_type == "HW" or large_workload:
            workloads.extend(HA_CFG["s3_bench_large_workloads"])

        resp = s3bench.setup_s3bench()
        if not resp:
            return resp, "Couldn't setup s3bench on client machine."
        for workload in workloads:
            resp = s3bench.s3bench(
                s3userinfo['accesskey'], s3userinfo['secretkey'],
                bucket=f"bucket-{workload.lower()}-{log_prefix}",
                num_clients=nclients, num_sample=nsamples, obj_name_pref=f"ha_{log_prefix}",
                obj_size=workload, skip_write=skipwrite, skip_read=skipread,
                skip_cleanup=skipcleanup, log_file_prefix=f"log_{log_prefix}",
                end_point=S3_CFG["s3_url"], validate_certs=S3_CFG["validate_certs"])
            resp = system_utils.validate_s3bench_parallel_execution(log_path=resp[1])
            if not resp[0]:
                return False, f"s3bench operation failed: {resp[1]}"
        return True, "Successfully completed s3bench operation"

    def cortx_start_cluster(self, pod_obj):
        """
        This function starts the cluster
        :param pod_obj : Pod object from which the command should be triggered
        :return: Boolean, response
        """
        LOGGER.info("Start the cluster")
        resp = pod_obj.execute_cmd(common_cmd.CLSTR_START_CMD.format(self.dir_path),
                                   read_lines=True, exc=False)
        LOGGER.info("Cluster start response: {}".format(resp))
        if resp[0]:
            return True, resp
        return False, resp

    def cortx_stop_cluster(self, pod_obj):
        """
        This function stops the cluster
        :param pod_obj : Pod object from which the command should be triggered
        :return: Boolean, response
        """
        LOGGER.info("Stop the cluster")
        resp = pod_obj.execute_cmd(common_cmd.CLSTR_STOP_CMD.format(self.dir_path),
                                   read_lines=True, exc=False)
        LOGGER.info("Cluster stop response: %s", resp)
        if resp[0]:
            return True, resp
        return False, resp

    def restart_cluster(self, pod_obj, sync=False):
        """
        Restart the cluster and check all nodes health.
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

    def create_bucket_to_complete_mpu(self, s3_data, bucket_name, object_name, file_size,
                                      total_parts, multipart_obj_path):
        """
        Helper function to complete multipart upload.
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
        Helper function to do partial multipart upload.
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
        except BaseException as error:
            LOGGER.error("Error in %s: %s", HAK8s.partial_multipart_upload.__name__, error)
            return False, error

    @staticmethod
    def create_multiple_data_parts(multipart_obj_path, multipart_obj_size, total_parts):
        """
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
                LOGGER.info("Response: %s", response)
                copy_etag = response['CopyObjectResult']['ETag']
                if put_etag == copy_etag:
                    LOGGER.info("Object %s copied to bucket %s with object name %s successfully",
                                object_name, bkt_name, obj_name)
                else:
                    LOGGER.error("Etags don't match for copy object %s to bucket %s with object "
                                 "name %s", object_name, bkt_name, obj_name)
            except CTException as error:
                LOGGER.error("Error: %s", error)
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
        except (Exception, CTException) as error:
            LOGGER.error("Failed mpu due to error %s. Exiting from background process.", error)
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
            except BaseException as error:
                LOGGER.error("Error: %s", error)
                if event.is_set():
                    exp_failed_parts.append(i)
                else:
                    failed_parts.append(i)
                LOGGER.info("Failed to upload part %s", i)

        res = (exp_failed_parts, failed_parts, parts_etag, mpu_id)
        output.put(res)

    def check_cluster_status(self, pod_obj, pod_list=None):
        """
        :param pod_obj: Object for master node
        :param pod_list: Data pod name list to get the hctl status
        :return: boolean, response
        """
        LOGGER.info("Check the overall K8s cluster status.")
        try:
            resp = pod_obj.execute_cmd(common_cmd.CLSTR_STATUS_CMD.format(self.dir_path))
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
        else:
            return all(md5_list[0] == x for x in md5_list)

    def poll_cluster_status(self, pod_obj, timeout=1200):         # default 20mins timeout
        """
        Helper function to poll the cluster status
        :param pod_obj: Object for master nodes
        :param timeout: Timeout value
        :return: bool, response
        """
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

    @staticmethod
    def restore_pod(pod_obj, restore_method, restore_params: dict = None):
        """
        Helper function to restore pod based on way_to_restore
        :param pod_obj: Object of master node
        :param restore_method: Restore method to be used depending on shutdown method
        ("scale_replicas", "k8s", "helm")
        :param restore_params: Dict which has parameters required to restore pods
        :return: Bool, response
        """
        deployment_name = restore_params["deployment_name"]
        deployment_backup = restore_params.get("deployment_backup", None)

        if restore_method == common_const.RESTORE_SCALE_REPLICAS:
            resp = pod_obj.create_pod_replicas(num_replica=1, deploy=deployment_name)
        elif restore_method == common_const.RESTORE_DEPLOYMENT_K8S:
            resp = pod_obj.recover_deployment_k8s(deployment_name=deployment_name,
                                                  backup_path=deployment_backup)
        elif restore_method == common_const.RESTORE_DEPLOYMENT_HELM:
            resp = pod_obj.recover_deployment_helm(deployment_name=deployment_name)

        return resp

    def event_s3_operation(self, event, log_prefix=None, s3userinfo=None, skipread=False,
                           skipwrite=False, skipcleanup=False, nsamples=10, nclients=10,
                           output=None):
        """
        This function executes s3 bench operation on VM/HW.(can be used for parallel execution)
        :param event: Thread event to be sent in case of parallel IOs
        :param log_prefix: Test number prefix for log file
        :param s3userinfo: S3 user info
        :param skipread: Skip reading objects created in this run if True
        :param skipwrite: Skip writing objects created in this run if True
        :param skipcleanup: Skip deleting objects created in this run if True
        :param nsamples: Number of samples of object
        :param nclients: Number of clients/workers
        :param output: Queue to fill results
        :return: None
        """
        pass_res = []
        fail_res = []
        results = dict()
        workloads = HA_CFG["s3_bench_workloads"]
        if self.setup_type == "HW":
            workloads.extend(HA_CFG["s3_bench_large_workloads"])
        # Flag to store next workload status after/while event gets clear from test function
        event_clear_flg = False
        resp = s3bench.setup_s3bench()
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
                end_point=S3_CFG["s3_url"], validate_certs=S3_CFG["validate_certs"])
            if event.is_set():
                fail_res.append(resp)
                event_clear_flg = True
            else:
                if event_clear_flg:
                    fail_res.append(resp)
                    event_clear_flg = False
                    continue
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
        Helper function to put, get and delete objects.
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
                    LOGGER.error("Error in %s: %s", HAK8s.put_get_delete.__name__, error)
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
                    LOGGER.error("Error in %s: %s", HAK8s.put_get_delete.__name__, error)
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
                        LOGGER.error("Error in %s: %s", HAK8s.put_get_delete.__name__, error)
                        if event.is_set():
                            event_del_bkt.append(bucket_list[0])
                        else:
                            fail_del_bkt.append(bucket_list[0])
                    bucket_list.remove(bucket_list[0])
                    count += 1
                    if count >= bkts_to_del:
                        break
                    elif not bkt_list and not bucket_list:
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
        as that of HA or control pod.
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
        and check if its not pinging.
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
                else:
                    return True, node_ip, node_iface, new_worker_obj

    @staticmethod
    def create_bucket_chunk_upload(s3_data, bucket_name, file_size, chunk_obj_path, output,
                                   bkt_op=True):
        """
        Helper function to do chunk upload.
        :param s3_data: s3 account details
        :param bucket_name: Name of the bucket
        :param file_size: Size of the file to be created to upload
        :param chunk_obj_path: Path of the file to be uploaded
        :param output: Queue used to fill output
        :param bkt_op: Flag to create bucket and object
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
                output.put(False)
                sys.exit(1)
            LOGGER.info("Created a bucket with name : %s", bucket_name)

            LOGGER.info("Creating object file of 5GB")
            resp = system_utils.create_file(chunk_obj_path, file_size)
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                output.put(False)
                sys.exit(1)

        java_cmd = S3_BLKBOX_CFG["jcloud_cfg"]["jclient_cmd"]
        put_cmd = f"{java_cmd} -c {jclient_prop} put {chunk_obj_path} s3://{bucket_name} " \
                  f"--access_key {access_key} --secret_key {secret_key}"
        LOGGER.info("Running command %s", put_cmd)
        resp = system_utils.execute_cmd(put_cmd)
        if not resp:
            output.put(False)
            sys.exit(1)

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
            LOGGER.error("Error: Not able to get cluster config file")
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
        conf_fd = open(local_conf, 'r')
        data = yaml.safe_load(conf_fd)

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
            LOGGER.error("Failed to copy %s inside ha pod %s due to error: %s",
                         common_const.MOCK_MONITOR_LOCAL_PATH, ha_pod, error)
            return False
        return True

    def simulate_disk_cvg_failure(self, node_obj, source, resource_status, resource_type,
                                  node_type='data', resource_cnt=1, node_cnt=1, delay=None):
        """
        :param node_obj: Object for node
        :param source: Source of the event, monitor, ha, hare, etc.
        :param resource_status: recovering, online, failed, unknown, degraded, repairing,
        repaired, rebalancing, offline, etc.
        :param resource_type: node, cvg, disk, etc.
        :param node_type: Type of the node (data, server)
        :param resource_cnt: Count of the resources
        :param node_cnt: Count of the nodes on which failure to be simulated
        :param delay: Delay between two events (Optional)
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
                # Repeat the dictionary above with specific values if multiple events to be sent.
            },
        "delay": xxxx # If present this will add delay of specified seconds between the events.
        }
        :return: Bool, config_dict/error
        """
        config_json_file = "config.json"
        config_dict = dict()
        config_dict["events"] = {}
        node_id_list = self.get_node_resource_ids(node_obj=node_obj, r_type='node',
                                                  n_type=node_type)
        if len(node_id_list) < node_cnt:
            LOGGER.error("Please provide correct count for nodes")
            return False, node_id_list
        count = 0
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
                config_dict["events"][f"{count}"]["node_id"] = node_id_list[n_cnt]
                config_dict["events"][f"{count}"]["resource_id"] = resource_id_list[d_cnt]

        if delay:
            config_dict["delay"] = delay

        with open(config_json_file, "w") as outfile:
            json.dump(config_dict, outfile)

        LOGGER.info("Publishing mock events: %s", config_dict)
        LOGGER.info("Get HA pod name for publishing event")
        ha_pod = node_obj.get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)[0]
        LOGGER.info("Publishing event %s for %s resource type through ha pod %s", resource_status,
                    resource_type, ha_pod)
        cmd = common_cmd.PUBLISH_CMD.format(common_const.MOCK_MONITOR_REMOTE_PATH, config_json_file)
        try:
            node_obj.send_k8s_cmd(operation="exec", pod=ha_pod,
                                  namespace=common_const.NAMESPACE + " -- ", command_suffix=cmd,
                                  decode=True)
        except IOError as error:
            LOGGER.error("Failed to publish the event due to error: %s", error)
            return False, error

        return True, config_dict

    @staticmethod
    def get_node_resource_ids(node_obj, r_type, n_type=None, node_id=None):
        """
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
            LOGGER.error("Error in %s: %s", HAK8s.get_node_resource_ids.__name__, error)
            raise error

        LOGGER.info("Resource IDs for %s are: %s", r_type, resp)
        return resp
