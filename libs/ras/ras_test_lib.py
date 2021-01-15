#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This test helper lib implements the base fuctions of ras_lib by inheriting the
class
"""
import logging
import os
import time
from typing import Tuple, Any, Union
from libs.ras.ras_core_lib import RASCoreLib
from commons.utils.config_utils import read_yaml, get_config
from commons import constants as cmn_cons
from commons import commands as common_commands
from commons import errorcodes as err
from commons.exceptions import CTException

# Global Constants
RAS_VAL = read_yaml(cmn_cons.RAS_CFG)[1]
COMMON_CFG = read_yaml("config/common_config.yaml")[1]
BYTES_TO_READ = cmn_cons.BYTES_TO_READ
LOGGER = logging.getLogger(__name__)


class RASTestLib(RASCoreLib):
    """
    Test lib calls for RAS test-cases
    """

    def __init__(
            self,
            host: str = COMMON_CFG["host"],
            username: str = COMMON_CFG["username"],
            password: str = COMMON_CFG["password"]):
        """
        This method initializes members of RASTestLib and its parent class
        :param str host: host
        :param str username: username
        :param str password: password
        """
        self.host = host
        self.username = username
        self.pwd = password
        self.common_cfg = COMMON_CFG
        self.sspl_pass = COMMON_CFG["sspl_pass"]
        super().__init__(host, username, password)

    def start_rabbitmq_reader_cmd(self, sspl_exchange: str, sspl_key: str, **kwargs) -> bool:
        """
        This function will check for the disk space alert for sspl.
        :param str sspl_exchange: sspl exchange string
        :param str sspl_key: sspl key string
        :keyword sspl_pass: sspl_pass
        :return: Command response along with status(True/False)
        :rtype: bool
        """
        sspl_pass = kwargs.get("sspl_pass")if kwargs.get("sspl_pass") else self.sspl_pass
        try:
            LOGGER.info(f"Start rabbitmq chanel on node {self.host}")
            cmd_output = super().start_rabbitmq_reader_cmd(sspl_exchange, sspl_key, sspl_pass)
            LOGGER.debug(cmd_output)
            return cmd_output
        except BaseException as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.start_rabbitmq_reader_cmd.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

    def check_sspl_event_generated(self) -> Tuple[bool, Any]:
        """
        Check for relevant events are generated on RabbitMQ Channel for the
        specific volumes inside disk group.
        :return: (Boolean, response)
        :rtype: (bool, str)
        """
        cmd = common_commands.SSPL_SERVICE_CMD
        LOGGER.debug(cmd)
        try:
            LOGGER.info("Check ssp events are generated")
            res = self.node_utils.execute_cmd(
                cmd=cmd, read_nbytes=BYTES_TO_READ, shell=False)
            LOGGER.info(res)
        except BaseException as error:
            LOGGER.error(
                f"{cmn_cons.EXCEPTION_ERROR} "
                f"{RASTestLib.check_sspl_event_generated.__name__}: {error}")
            raise CTException(err.RAS_ERROR, error.args[0])

        return res

    def check_status_file(self) -> Tuple[bool, Any]:
        """
        This function checks the state.txt file of sspl service and sets the
        status=active.
        :return: (Boolean, response)
        :rtype: (bool, resp)
        """
        try:
            LOGGER.info(f"Check sspl status file")
            response = super().check_status_file()
        except BaseException as error:
            LOGGER.error(
                f"{cmn_cons.EXCEPTION_ERROR} "
                f"{RASCoreLib.check_status_file.__name__}: {error}")
            raise CTException(err.RAS_ERROR, error.args[0])

        return response

    def put_kv_store(self, username: str, pwd: str, field: str) -> bool:
        """
        This function updates the values in KV store as per the values in
        storage_enclosure.sls.
        :param str username: Username of the enclosure
        :param str pwd: password for the enclosure user
        :param str field: Field in K store to be updated
        :return: Boolean
        :rtype: bool
        """
        try:
            LOGGER.info(f"Put expected value of {field} in KV store")
            response = super().put_kv_store(username, pwd, field)
        except BaseException as error:
            LOGGER.error(
                f"{cmn_cons.EXCEPTION_ERROR} {RASCoreLib.put_kv_store.__name__}: {error}")
            raise CTException(err.RAS_ERROR, error.args[0])

        return response

    def retain_config(self, filename: str, restore: bool) -> bool:
        """
        This function renames the sspl.cong file to sspl_original.cong to retain
        the original config
        :param str filename: Name of the file to be renamed
        :param bool restore: boolean value to specify te operation
        :return: Boolean
        :rtype: bool
        """
        path = RAS_VAL["ras_sspl_alert"]["file"]["sspl_conf_filename"]
        backup_path = filename

        if restore:
            res = self.node_utils.is_s3_server_path_exists(path=backup_path,
                                                           shell=False)
            if res[0]:
                LOGGER.info("Restoring the sspl.conf file")
                self.node_utils.rename_file(old_filename=backup_path, new_filename=path)
                LOGGER.info(f"Removing {backup_path} file")
                self.node_utils.remove_file(filename=backup_path)
            else:
                LOGGER.info("Removing sspl.conf file")
                self.node_utils.remove_file(filename=path)
        else:
            res = self.node_utils.is_s3_server_path_exists(path=path,
                                                           shell=False)
            if res[0]:
                LOGGER.info(f"Retaining the {path} file")
                self.cp_file(path, backup_path)
                return True

    def validate_alert_log(self, filename: str, string: str) -> bool:
        """
        This function validates if the specific alerts are generated
        :param filename: Name of the log file in which alerts are stored
        :param string: String of the alert message
        :return: Boolean
        :rtype: bool
        """
        resp = self.node_utils.is_string_in_remote_file(string=string, file_path=filename)
        if resp[0]:
            LOGGER.info(f"Alert {string} generated successfully on node")
        else:
            LOGGER.info(f"{string} Alert is not generated")

        return resp

    def kill_remote_process(self, process_name: str) -> Tuple[bool, str]:
        """
        This function kills the process running on remote server with process
        name (Be careful while using this function as it kills all the processes
        having specified name)
        :param process_name: Name of the process to be killed
        :returns: Response in tuple
        """
        cmd = common_commands.KILL_PROCESS_CMD.format(process_name)
        return self.node_utils.remote_machine_cmd(cmd=cmd, nbytes=BYTES_TO_READ, shell=False)

    def update_threshold_values(self, kv_store_path: str, field: str, value,
                                update: bool = True) -> bool:
        """
        This function updates the values in KV store as per the values.
        :param kv_store_path: Path of the field in kv-store
        :param field: Field in KV store to be updated
        :param value: Threshold value to be updated
        :param update: Flag for updating the consul value or not
        :return: True/False
        :rtype: bool
        """
        try:
            LOGGER.info("Updating the consul value {}".format(field))
            response = super().update_threshold_values(kv_store_path, field,
                                                       value, update=update)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.update_threshold_values.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return True

    def reset_log_file(self, file_path: str) -> bool:
        """
        This function takes the backup of the log file and then empties the file
        :param str file_path: path of the remote file
        :return: True/False
        :rtype: bool
        """
        try:
            # Copy existing log to another file
            LOGGER.info("Creating backup log file")
            remote_dir = "/".join(file_path.split("/")[:-1])
            bck_file_path = "{}/{}".format(remote_dir, "bck.log")
            res = self.cp_file(file_path, bck_file_path)
            LOGGER.info("Copy file resp : {}".format(res))
            res = self.truncate_file(file_path)
            LOGGER.info("Reset file resp : {}".format(res))
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.reset_log_file.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return True

    def get_sspl_state(self, host: str = None,
                       username: str = None,
                       password: str = None) -> Tuple[bool, str]:
        """
        This function reads the sspl text file to get the state of
        sspl on master node
        :param str host: host
        :param str username: username
        :param str password: password
        :return: Boolean and response
        :rtype: (bool, str)
        """
        hostname = host if host else self.host
        user = username if username else self.username
        pwd = password if password else self.pwd
        try:
            LOGGER.info("Getting the SSPL state")
            response = super().get_sspl_state(host=hostname, username=user,
                                              password=pwd)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.get_sspl_state.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return response

    def generate_disk_full_alert(
            self,
            du_val: int,
            fault: bool = True,
            fault_resolved: bool = False) -> Tuple[bool, float]:
        """
        Function to verify the sspl disk space alert, both positive and negative
        based on the disk usage
        :param int du_val: Value to be added to current disk usage to form new disk_usage_threshold
        :param bool fault: True to generate disk full fault alert, default True
        :param bool fault_resolved: True to generate disk full fault_resolved alert, default False
        :return: status, current disk usage(bool,int|float)
        """
        try:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            status = False
            LOGGER.info("Retrieve original value of disk_usage_threshold")
            self.node_utils.copy_file_to_local(
                common_cfg["file"]["sspl_conf_filename"],
                common_cfg["file"]["sspl_cfg_temp"])
            default_disk_threshold = get_config(
                common_cfg["file"]["sspl_cfg_temp"],
                common_cfg["sspl_config"]["sspl_section"],
                common_cfg["sspl_config"]["sspl_du_key"])
            LOGGER.info(
                "Original value of {} :{}".format(
                    common_cfg["sspl_config"]["sspl_du_key"],
                    default_disk_threshold))

            resp = self.node_utils.disk_usage_python_interpreter_cmd(
                dir_path=common_cfg["sspl_config"]["server_du_path"],
                field_val=0,
                host=self.host,
                user=self.username,
                pwd=self.pwd)
            total_disk_size = int(resp[1][0])
            file_name = common_cfg["file"]["disk_usage_temp_file"]
            file_size = int((total_disk_size * du_val) / (1024 * 1024 * 100)) * 2

            LOGGER.info("Fetching server disk usage")
            resp = self.node_utils.disk_usage_python_interpreter_cmd(
                dir_path=common_cfg["sspl_config"]["server_du_path"],
                host=self.host,
                user=self.username,
                pwd=self.pwd)
            current_disk_usage = float(resp[1][0])
            LOGGER.info("Current disk usage of EES server :{}"
                        .format(current_disk_usage))
            new_disk_threshold = current_disk_usage + du_val

            LOGGER.info(
                "Setting value of disk_usage_threshold to {}".format(new_disk_threshold))
            res = self.update_threshold_values(
                cmn_cons.KV_STORE_DISK_USAGE,
                common_cfg["sspl_config"]["sspl_du_key"],
                new_disk_threshold)
            LOGGER.info("Updated server disk_usage_threshold value")

            LOGGER.info("Restarting sspl services and waiting some time")
            self.node_utils.restart_s3server_service(
                common_cfg["service"]["sspl_service"],
                host=self.host,
                user=self.username,
                pwd=self.pwd,
                shell=False)
            time.sleep(common_cfg["sleep_val"])
            LOGGER.info(res)

            if fault:
                if self.node_utils.path_exists(file_name):
                    LOGGER.info("Remove temp disk usage file")
                    self.node_utils.remove_file(filename=file_name)
                LOGGER.info(
                    "Creating file {} on host {} to increase the disk usage".format(
                        file_name, self.host))
                resp = self.node_utils.create_file(
                    file_name, file_size)
                LOGGER.info(resp)
                time.sleep(common_cfg["one_min_delay"])
                LOGGER.info("Fetching server disk usage")
                resp = self.node_utils.disk_usage_python_interpreter_cmd(
                    dir_path=common_cfg["sspl_config"]["server_du_path"])
                current_disk_usage = float(resp[1][0])
                LOGGER.info("Current disk usage of EES server :{}"
                            .format(current_disk_usage))
                status = current_disk_usage >= new_disk_threshold
                LOGGER.info("Disk fault generation status: {}".format(status))

            if fault_resolved:
                LOGGER.info(
                    "Removing file {} to reduce the disk usage on host {}".format(
                        file_name, self.host))
                self.node_utils.remove_file(file_name)
                time.sleep(common_cfg["one_min_delay"])
                LOGGER.info("Fetching server disk usage")
                resp = self.node_utils.disk_usage_python_interpreter_cmd(
                    dir_path=common_cfg["sspl_config"]["server_du_path"])
                current_disk_usage = float(resp[1][0])
                LOGGER.info("Current disk usage of EES server :{}"
                            .format(current_disk_usage))
                status = current_disk_usage < new_disk_threshold
                LOGGER.info("Disk fault generation status: {}".format(status))
                time.sleep(common_cfg["one_min_delay"])

        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.generate_disk_full_alert.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return status, current_disk_usage

    def list_alert_validation(self, string_list: list) -> Tuple[bool, Any]:
        """
        Function to verify the alerts generated on specific events
        :param list string_list: List of expected strings in alert response having
        format [resource_type, alert_type, ...]
        :return: response in tuple{bool, resp)
        :rtype: (bool, str)
        """
        common_cfg = RAS_VAL["ras_sspl_alert"]
        try:
            LOGGER.info("Checking status of sspl and rabbitmq services")
            resp = self.node_utils.get_s3server_service_status(
                common_cfg["service"]["sspl_service"], shell=False)
            if not resp[0]:
                return resp
            resp = self.node_utils.get_s3server_service_status(
                common_cfg["service"]["rabitmq_service"], shell=False)
            if not resp[0]:
                return resp
            LOGGER.info(
                "Verified sspl and rabitmq services are in running state")
            time.sleep(common_cfg["sleep_val"])

            LOGGER.info("Fetching sspl alert response")
            response = self.cp_file(common_cfg["file"]["screen_log"],
                                    common_cfg["file"]["alert_log_file"])
            if not response[0]:
                return response
            LOGGER.info("Successfully fetched the alert response")

            LOGGER.debug("Reading the alert log file")
            read_resp = self.node_utils.read_file(
                common_cfg["file"]["alert_log_file"], "/tmp/rabbitmq_alert.log")
            LOGGER.debug(
                "======================================================")
            LOGGER.debug(read_resp)
            LOGGER.debug(
                "======================================================")

            LOGGER.info(
                "Checking if alerts are generated on rabbitmq channel")
            cmd = common_commands.EXTRACT_LOG_CMD.format(
                common_cfg["file"]["alert_log_file"], string_list[0])
            response = self.node_utils.execute_cmd(cmd=cmd,
                                                   nbytes=BYTES_TO_READ,
                                                   shell=False)
            if not response[0]:
                return response

            resp = self.node_utils.validate_alert_msg(
                common_cfg["file"]["extracted_alert_file"], string_list, shell=False)

            LOGGER.info(resp)
            return resp
        except BaseException as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.list_alert_validation.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])
        finally:
            LOGGER.info("Removing alert log file from the Node")
            self.node_utils.remove_file(
                filename=common_cfg["file"]["alert_log_file"])
            self.node_utils.remove_file(
                filename=common_cfg["file"]["extracted_alert_file"])
            self.node_utils.remove_file(
                filename=common_cfg["file"]["screen_log"])

    def generate_cpu_usage_alert(
            self,
            delta_cpu_usage: str,
            host: str = None,
            username: str = None,
            password: str = None) -> bool:
        """
        Function to generate cpu usage alert, both positive and negative
        based on the delta_cpu_usage value
        :param host: host machine ip
        :param username: host machine username
        :param password: host machine password
        :param delta_cpu_usage: Value to be added or subtracted from current cpu usage as per requirement
        :return: True/False
        :rtype: bool
        """
        try:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            hostname = host if host else self.host
            username = username if username else self.username
            password = password if password else self.pwd
            LOGGER.info("Fetching cpu usage from server node {}".format(host))
            resp = self.node_utils.get_system_cpu_usage(
                host=hostname, username=username, password=password)

            current_cpu_usage = resp[1]
            LOGGER.info(
                "Current cpu usage of server node {} is {}".format(
                    host, current_cpu_usage))
            new_threshold_cpu_usage = float(
                "{:.1f}".format(sum([resp[1], delta_cpu_usage])))
            LOGGER.info(
                "Setting new value of cpu_usage_threshold to {} on node {}".format(
                    new_threshold_cpu_usage, host))

            resp = self.update_threshold_values(
                cmn_cons.KV_STORE_DISK_USAGE,
                cmn_cons.CPU_USAGE_KEY,
                new_threshold_cpu_usage)

            LOGGER.info("Updated server cpu_usage_threshold to {}".format(
                new_threshold_cpu_usage))

            LOGGER.info("Restarting sspl service on node {}".format(host))
            self.node_utils.restart_s3server_service(
                common_cfg["service"]["sspl_service"],
                host=hostname,
                user=username,
                pwd=password, shell=False)
            LOGGER.info(
                "Sleeping for {} seconds after restarting sspl service".format(
                    common_cfg["sleep_val"]))
            time.sleep(common_cfg["sleep_val"])

        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.generate_cpu_usage_alert.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return resp

    def generate_memory_usage_alert(
            self,
            delta_mem_usage: str,
            host: str = None) -> bool:
        """
        Function to generate memory usage alert, both positive and negative
        based on the delta_mem_usage value
        :param host: host machine ip
        :param delta_mem_usage: Value to be added or subtracted from current memory usage as per requirement
        :return: True/False
        :rtype: bool
        """
        try:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            host = host if host else self.host
            LOGGER.info(
                "Fetching memory usage from server node {}".format(host))
            resp = self.node_utils.get_system_memory_usage(
                host=host, username=self.username, password=self.pwd)

            current_mem_usage = resp[1]
            LOGGER.info(
                "Current memory usage of server node {} is {}".format(
                    host, current_mem_usage))
            new_threshold_mem_usage = float(
                "{:.1f}".format(sum([resp[1], delta_mem_usage])))
            LOGGER.info(
                "Setting new value of host_memory_usage_threshold to {} on node {}".format(
                    new_threshold_mem_usage, host))

            resp = self.update_threshold_values(
                cmn_cons.KV_STORE_DISK_USAGE,
                cmn_cons.MEM_USAGE_KEY,
                new_threshold_mem_usage)

            LOGGER.info("Updated server host_memory_usage_threshold to {}".format(
                new_threshold_mem_usage))

            LOGGER.info("Restarting sspl service on node {}".format(host))
            self.node_utils.restart_s3server_service(
                common_cfg["service"]["sspl_service"],
                host=host,
                user=self.username,
                pwd=self.pwd, shell=False)
            LOGGER.info(
                "Sleeping for {} seconds after restarting sspl service".format(
                    common_cfg["sleep_val"]))
            time.sleep(common_cfg["sleep_val"])

        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.generate_cpu_usage_alert.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return resp

    def update_mdadm_config(self) -> str:
        """
        This method updates the current MDRAID devices details into mdadm config
        :return: content of mdadm config
        :rtype: str
        """
        LOGGER.info(
            "Updating the mdadm config {}".format(
                RAS_VAL["mdadm_conf_path"]))
        try:
            update_conf_arg = common_commands.MDADM_UPDATE_CONFIG
            mdadm_conf_path = RAS_VAL["mdadm_conf_path"]
            local_path = RAS_VAL["mdadm_conf_local_path"]
            mdadm_args = [update_conf_arg, mdadm_conf_path]
            super().run_mdadm_cmd(mdadm_args)
            self.node_utils.write_remote_file_to_local_file(
                mdadm_conf_path,
                local_path)
            with open(local_path, "r") as fp:
                mdadm_conf = fp.read()
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.update_mdadm_config.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return mdadm_conf

    def create_mdraid_disk_array(
            self,
            md_device: str,
            *disks: Any) -> Tuple[bool, Union[str, dict]]:
        """
        This method creates a MDRAID array device with the given list of disks
        :param str md_device: MDRAID device to be created
        :param disks: Disks to be added in the MDRAID array
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info(
            "Creating a MDRAID device {} with disks {} on the host {}".format(
                md_device, disks, self.host))
        if not md_device:
            return False, "Please provide RAID device name e.g., /dev/md?"
        if not disks:
            return False, "Please provide disk from RAID device e.g., /dev/sd??"
        try:
            create_mdraid_cmd = common_commands.MDADM_CREATE_ARRAY.format(
                md_device, len(disks))
            mdadm_args = [create_mdraid_cmd]
            for disk in disks:
                mdadm_args.append(disk)
            super().run_mdadm_cmd(mdadm_args)
            mdadm_conf = self.update_mdadm_config()
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(
                    md_device) in md_stat["devices"] and md_device in mdadm_conf:
                md_stat_disks = md_stat["devices"][os.path.basename(
                    md_device)]["disks"]
                disk_flag = [True for disk in disks if os.path.basename(disk) in md_stat_disks]
                if all(disk_flag):
                    return True, md_stat
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.create_mdraid_disk_array.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return False, md_stat

    def assemble_mdraid_device(self, md_device: str) -> Tuple[bool, Union[str, dict]]:
        """
        This method re-assembles/restarts the given MDRAID device on the given host
        :param str md_device: MDRAID device to be assemble
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info(
            "Assembling the MDRAID device {} on the host {}".format(
                md_device, self.host))
        try:
            assemble_arg = common_commands.MDADM_ASSEMBLE
            mdadm_args = [assemble_arg, md_device]
            super().run_mdadm_cmd(mdadm_args)
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(md_device) in md_stat["devices"]:
                return True, md_stat
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.assemble_mdraid_device.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return False, md_stat

    def stop_mdraid_device(
            self,
            md_device: str) -> Tuple[bool, Union[str, dict]]:
        """
        This method stops the given MDRAID device on the given host
        :param str md_device: MDRAID device to be stopped
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info(
            "Stopping the MDRAID device {} on the host {}".format(
                md_device, self.host))
        try:
            stop_arg = common_commands.MDADM_STOP
            mdadm_args = [stop_arg, md_device]
            super().run_mdadm_cmd(mdadm_args)
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(md_device) in md_stat["devices"]:
                return False, md_stat
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.stop_mdraid_device.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return True, md_stat

    def fail_disk_mdraid(
            self,
            md_device: str,
            disk: str) -> Tuple[bool, Union[str, dict]]:
        """
        This method simulates disk failure from a given MRAID device
        :param str md_device: MDRAID device
        :param str disk: Disk from MDRAID device which is to be declare as faulty
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info(
            "Declaring Disk {} from RAID device {} as faulty".format(
                disk, md_device))
        try:
            manage_arg = common_commands.MDADM_MANAGE
            fail_arg = common_commands.MDADM_FAIL
            mdadm_args = [manage_arg, md_device, fail_arg, disk]
            super().run_mdadm_cmd(mdadm_args)
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if md_stat["devices"][os.path.basename(
                    md_device)]["disks"][os.path.basename(disk)]["faulty"]:
                return True, md_stat
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.fail_disk_mdraid.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return False, md_stat

    def remove_faulty_disk(
            self,
            md_device: str,
            disk: str) -> Tuple[bool, Union[str, dict]]:
        """
        This method removes given faulty disk from the given MRAID device
        :param str md_device: MDRAID device
        :param str disk: Faulty Disk which is to be removed from MDRAID device
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info(
            "Removing Disk {} from RAID device {}".format(
                disk, md_device))
        try:
            manage_arg = common_commands.MDADM_MANAGE
            remove_arg = common_commands.MDADM_REMOVE
            mdadm_args = [manage_arg, md_device, remove_arg, disk]
            super().run_mdadm_cmd(mdadm_args)
            self.update_mdadm_config()
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(
                    disk) in md_stat["devices"][os.path.basename(md_device)]["disks"]:
                return False, md_stat
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.remove_faulty_disk.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return True, md_stat

    def add_disk_mdraid(
            self,
            md_device: str,
            disk: str) -> Tuple[bool, dict]:
        """
        This method adds new disk to the given MRAID device
        :param str md_device: MDRAID device
        :param str disk: Disk to be added to MDRAID device
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info(
            "Adding Disk {} to the RAID device {}".format(
                disk, md_device))
        try:
            manage_arg = common_commands.MDADM_MANAGE
            add_arg = common_commands.MDADM_ADD
            mdadm_args = [manage_arg, md_device, add_arg, disk]
            super().run_mdadm_cmd(mdadm_args)
            self.update_mdadm_config()
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(
                    disk) in md_stat["devices"][os.path.basename(md_device)]["disks"]:
                return True, md_stat
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.add_disk_mdraid.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return False, md_stat

    def remove_mdraid_disk_array(self, md_device: str) -> Tuple[bool, Union[str, dict]]:
        """
        This method removes given MDRAID array device anc cleanup all the disks from array
        :param str md_device: MDRAID device to be created
        :return: True/False and content of mdadm config
        :rtype: bool, str
        """
        if not md_device:
            return False, "Please provide RAID device name e.g., /dev/md?"
        try:
            md_stat = self.node_utils.get_mdstat()
            if os.path.basename(md_device) not in md_stat["devices"]:
                return False, "{} device not found: {}".format(md_device, md_stat)

            disks = md_stat["devices"][os.path.basename(md_device)]["disks"].keys()
            LOGGER.info(
                "Removing MDRAID array device {} with disks {} on the host {}".format(
                    md_device, disks, self.host))
            stop_device = self.stop_mdraid_device(md_device)
            if not stop_device[0]:
                return stop_device
            mdadm_conf = self.update_mdadm_config()

            LOGGER.info(
                "Performing cleanup and deleting superblock from disks {} on the host {}".format(
                    disks, self.host))
            for disk in disks:
                disk_path = "/dev/{}".format(disk)
                LOGGER.info("Deleting superblock from disk {}".format(disk_path))
                zero_superblock_arg = common_commands.MDADM_ZERO_SUPERBLOCK
                mdadm_args = [zero_superblock_arg, disk_path]
                super().run_mdadm_cmd(mdadm_args)

                LOGGER.info("Performing cleanup on disk {}".format(disk_path))
                wipe_disk_cmd = common_commands.WIPE_DISK_CMD.format(disk_path)
                self.node_utils.execute_cmd(
                    cmd=wipe_disk_cmd, read_nbytes=BYTES_TO_READ, shell=False)
                time.sleep(RAS_VAL["ras_sspl_alert"]["disk_clean_time"])
                self.node_utils.kill_remote_process(common_commands.KILL_WIPE_DISK_PROCESS)
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.remove_mdraid_disk_array.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return True, mdadm_conf

    def get_sspl_state_pcs(self) -> dict:
        """
        This function reads the sspl text file to get the state of
        sspl on master node
        :return: Boolean and response
        :rtype: dict
        """
        try:
            LOGGER.info("Getting the SSPL state")
            response = super().get_sspl_state_pcs()
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("{0} {1}: {2}".format(
                cmn_cons.EXCEPTION_ERROR,
                RASTestLib.get_sspl_state.__name__,
                error))
            raise CTException(err.RAS_ERROR, error.args[0])

        return response
