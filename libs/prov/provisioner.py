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
Provisioner utiltiy methods
"""
import shutil
import logging
import time
from string import Template
import re
import jenkins
import numpy as np
from commons import constants as common_cnst
from commons import commands as common_cmd
from commons import params as prm
from commons import pswdmanager
from commons.utils import config_utils

LOGGER = logging.getLogger(__name__)


class Provisioner:
    """This class contains utility methods for all the provisioning related operations"""

    @staticmethod
    # pylint: disable-msg=too-many-locals
    def build_job(
            job_name: str,
            parameters: dict = None,
            token: str = None,
            jen_url: str = prm.JENKINS_URL) -> dict:
        """
        Helper function to start the jenkins job.
        :param job_name: Name of the jenkins job
        :param parameters: Dict of different parameters to be passed
        :param token: Authentication Token for jenkins job
        :param jen_url: Jenkins url
        :return: build info dict
        """
        username = pswdmanager.decrypt(common_cnst.JENKINS_USERNAME)
        password = pswdmanager.decrypt(common_cnst.JENKINS_PASSWORD)
        try:
            LOGGER.debug("JENKINS URL %s", jen_url)
            jenkins_server_obj = jenkins.Jenkins(
                jen_url, username=username, password=password)
            LOGGER.debug("Jenkins_server obj: %s", jenkins_server_obj)
            completed_build_number = jenkins_server_obj.get_job_info(
                job_name)['lastCompletedBuild']['number']
            next_build_number = jenkins_server_obj.get_job_info(job_name)[
                'nextBuildNumber']
            LOGGER.info(
                "Last Completed build number: %d and  Next build number: %d",
                completed_build_number,
                next_build_number)
            jenkins_server_obj.build_job(
                job_name, parameters=parameters, token=token)
            time.sleep(10)
            LOGGER.info("Running the deployment job")
            # poll job status waiting for a result
            timeout = 7200  # sec
            interval = 10
            start_epoch = int(time.time())
            while True:
                build_info = jenkins_server_obj.get_build_info(
                    job_name, next_build_number)
                result = build_info['result']
                expected_result = ['SUCCESS', 'FAILURE', 'ABORTED', 'UNSTABLE']
                LOGGER.debug("result is %s::", result)
                if result in expected_result:
                    break
                cur_epoch = int(time.time())
                if (cur_epoch - start_epoch) > timeout:
                    LOGGER.error("No status before timeout of %s secs", timeout)
                    break
                time.sleep(interval)
            console_output = jenkins_server_obj.get_build_console_output(
                job_name, next_build_number)
            LOGGER.debug("console output:\n %s", console_output)

            return build_info
        except jenkins.TimeoutException as error:
            LOGGER.error("Timeout Connecting Jenkins Server: %s", error)

            return error

    @staticmethod
    def install_pre_requisites(node_obj: object, build_url: str) -> tuple:
        """
        This method will setup and install all the pre-requisites required to start CORTX deployment
        :param node_obj: Host object of the node to perform pre-requisites on
        :param build_url: URL to CORTX stack release repo
        :return: provisioner version
        """
        try:
            LOGGER.info("Adding Cortx and 3rd party repos")
            node_obj.execute_cmd(cmd=common_cmd.CMD_YUM_UTILS, read_lines=True)
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_ADD_REPO_3RDPARTY.format(build_url),
                read_lines=True)
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_ADD_REPO_CORTXISO.format(build_url),
                read_lines=True)

            LOGGER.info("Setting pip.conf file")
            config = "[global]\n" "timeout: 60\n" "index-url: {0}\n" "trusted-host: {1}".format(
                "".join([build_url, "/python_deps/"]), build_url.split("/")[2])
            node_obj.write_file(fpath=common_cnst.PIP_CONFIG, content=config)

            LOGGER.info("Installing Cortx Pre-requisites")
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_INSTALL_JAVA,
                read_lines=True)
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_INSTALL_CORTX_PRE_REQ,
                read_lines=True)
            LOGGER.info("Installing Provisioner Pre-requisites")
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_INSTALL_PRVSNR_PRE_REQ,
                read_lines=True)
            LOGGER.info("Installing Provisioner API")
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_INSTALL_PRVSNR_API,
                read_lines=True)

            LOGGER.info("Cleanup temporary repos")
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_RM_3RD_PARTY_REPO,
                read_lines=True)
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_RM_CORTXISO_REPO,
                read_lines=True)
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_YUM_CLEAN_ALL,
                read_lines=True)
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_RM_YUM_CACHE,
                read_lines=True)
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_RM_PIP_CONF,
                read_lines=True)

            LOGGER.info("Checking Provisioner version")
            prvsnr_version = node_obj.execute_cmd(
                cmd=common_cmd.CMD_PRVSNR_VER, read_lines=True)[0]
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.install_pre_requisites.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error

        return True, prvsnr_version

    @staticmethod
    def create_deployment_config(
            cfg_template: str,
            node_obj_list: list,
            **kwargs) -> tuple:
        """
        This method will create config.ini for CORTX deployment
        :param cfg_template: Local Path for config.ini template
        :param node_obj_list: List of Host object of all the nodes in a cluster
        :keyword mgmt_vip: mgmt_vip mandatory in case of multinode deployment
        :return: True/False and path of created config
        """
        mgmt_vip = kwargs.get("mgmt_vip", None)
        config_file = "deployment_config.ini"
        shutil.copyfile(cfg_template, config_file)
        try:
            if mgmt_vip:
                config_utils.update_config_ini(
                    config_file,
                    section="cluster",
                    key="mgmt_vip",
                    value=mgmt_vip,
                    add_section=False)
            elif not mgmt_vip and len(node_obj_list) > 1:
                return False, "mgmt_vip is required for multinode deployment"

            for node_count, node_obj in enumerate(node_obj_list, start=1):
                node = "srvnode-{}".format(node_count)
                hostname = node_obj.hostname
                device_list = node_obj.execute_cmd(
                    cmd=common_cmd.CMD_LIST_DEVICES,
                    read_lines=True)[0].split(",")
                metadata_devices = device_list[0]
                data_devices = ",".join(device_list[1:])
                config_utils.update_config_ini(
                    config_file, node, key="hostname", value=hostname, add_section=False)
                config_utils.update_config_ini(
                    config_file,
                    node,
                    key="storage.cvg.0.data_devices",
                    value=data_devices,
                    add_section=False)
                config_utils.update_config_ini(
                    config_file,
                    node,
                    key="storage.cvg.0.metadata_devices",
                    value=metadata_devices,
                    add_section=False)
        # pylint: disable=broad-except
        except Exception as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.create_deployment_config.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error

        return True, config_file

    @staticmethod
    def bootstrap_cortx(
            config_path: str,
            build_url: str,
            node_obj_list: list,
            timeout: int = 1800) -> tuple:
        """
        This method runs provisioner setup_provisioner command on the primary node
        :param config_path: Path of config.ini on primary node
        :param build_url: URL to CORTX stack release repo
        :param node_obj_list: List of Host objects of all the nodes in a cluster
        :param timeout: Max Time for bootstrap command should take to complete
        :return: True/False and output of bootstrap command
        """
        bootstrap_cmd = common_cmd.CMD_SETUP_PRVSNR.format(
            config_path, build_url)
        if len(node_obj_list) > 1:
            bootstrap_cmd = "{0} {1} ".format(bootstrap_cmd, "--ha")
        for node_count, node_obj in enumerate(node_obj_list, start=1):
            node = "srvnode-{}".format(node_count)
            hostname = node_obj.hostname
            bootstrap_cmd = "{0} {1}:{2}".format(bootstrap_cmd, node, hostname)
        LOGGER.info("Running Bootstrap command %s", bootstrap_cmd)
        node1_obj = node_obj_list[0]
        node1_obj.connect(shell=True)  #nosec
        channel = node1_obj.shell_obj
        output = ""
        current_output = ""
        start_time = time.time()
        channel.send("".join([bootstrap_cmd, "\n"]))
        passwd_counter = 0
        while (time.time() - start_time) < timeout:
            time.sleep(30)
            if channel.recv_ready():
                current_output = channel.recv(9999).decode("utf-8")
                output = output + current_output
                LOGGER.info(current_output)
            elif "Password:" in current_output and passwd_counter < len(node_obj_list):
                channel.send(
                    "".join([node_obj_list[passwd_counter].password, "\n"]))
                passwd_counter += 1
            elif "PROVISIONER FAILED" in output or "INFO - Done" in output:
                LOGGER.error(current_output)
                break
        else:
            return False, "Bootstap Timeout"

        if "PROVISIONER FAILED" in output:
            return False, output

        return True, output

    @staticmethod
    def prepare_pillar_data(
            node_obj: object,
            config_path: str,
            node_count: int) -> tuple:
        """
        This method updates data from config.ini into Salt pillar and
        exports pillar data to provisioner_cluster.json
        :param node_obj: Host object of the primary node
        :param config_path: Config.ini path on primary node
        :param node_count: Number of nodes in cluster
        :return: True/False and Response of confstore export
        """
        try:
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_CONFIGURE_SETUP.format(
                    config_path, node_count), read_lines=True)
            node_obj.execute_cmd(
                cmd=common_cmd.CMD_SALT_PILLAR_ENCRYPT,
                read_lines=True)
            resp = node_obj.execute_cmd(
                cmd=common_cmd.CMD_CONFSTORE_EXPORT, read_lines=True)
        # pylint: disable=broad-except
        except Exception as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.prepare_pillar_data.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])

            return False, error

        return True, resp

    @staticmethod
    def bootstrap_validation(node_obj: object) -> bool:
        """
        This method validates if Cortx bootstrap is successful on given node
        :param node_obj: Host object of the primary node
        :return: True/False
        """
        command_list = [common_cmd.CMD_SALT_PING,
                        common_cmd.CMD_SALT_STOP_PUPPET,
                        common_cmd.CMD_SALT_DISABLE_PUPPET,
                        common_cmd.CMD_SALT_GET_RELEASE,
                        common_cmd.CMD_SALT_GET_NODE_ID,
                        common_cmd.CMD_SALT_GET_CLUSTER_ID,
                        common_cmd.CMD_SALT_GET_ROLES
                        ]
        try:
            for command in command_list:
                command = " ".join([command, "--no-color"])
                resp = node_obj.execute_cmd(cmd=command, read_lines=True)
                LOGGER.debug(resp)
        # pylint: disable=broad-except
        except Exception as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.bootstrap_validation.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False

        return True

    @staticmethod
    def deploy_vm(node_obj: object, setup_type: str) -> tuple:
        """
        This method deploys cortx and 3rd party software components on given VM setup
        :param node_obj: Host object of the primary node
        :param setup_type: Type of setup e.g., single, 3_node etc
        :return: True/False and deployment status
        """
        components = [
            "system",
            "prereq",
            "utils",
            "iopath",
            "controlpath",
            "ha"]
        for comp in components:
            LOGGER.info("Deploying %s component", comp)
            try:
                node_obj.execute_cmd(
                    cmd=common_cmd.CMD_DEPLOY_VM.format(
                        setup_type, comp), read_lines=True)
            # pylint: disable=broad-except
            except Exception as error:
                LOGGER.error(
                    "An error occurred in %s:",
                    Provisioner.deploy_vm.__name__)
                if isinstance(error.args[0], list):
                    LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
                else:
                    LOGGER.error(error.args[0])
                return False, error

        return True, "Deployment Completed"

    @staticmethod
    def verify_services_ports(
            health_obj: object,
            services_ports: dict) -> tuple:
        """
        :param health_obj: Health object of the node to verify services on
        :param services_ports: Dictonary containing services names with expected running ports
        :return: True/False and list of inactive ports if any
        """
        try:
            inactive_ports = list()
            for service in services_ports:
                LOGGER.info("Fetching ports for service: %s", service)
                active_ports = health_obj.get_ports_for_firewall_cmd(service)
                LOGGER.debug(active_ports)
                for port in services_ports[service]:
                    if port not in active_ports:
                        LOGGER.error(
                            "%s is not running on port %s", service, port)
                        inactive_ports.append(port)
            if inactive_ports:
                return False, inactive_ports

            return True, active_ports
        # pylint: disable=broad-except
        except Exception as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.verify_services_ports.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])

            return False, error

    @staticmethod
    def confstore_verification(key: str, node_obj, node_id: int):
        """
        Helper function to verify the confstore key
        param: key: key to be verified
        param: node_obj: node object for remote execution
        param: node_id: srvnode number
        return: boolean
        """
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        try:
            chk = "srvnode-{}".format(node_id)
            cmd = common_cmd.CMD_PILLAR_DATA.format(chk, key)
            resp = node_obj.execute_cmd(cmd, read_lines=True)
            LOGGER.debug("pillar command output for %s's %s: %s", chk, key, resp)
            data1 = ansi_escape.sub('', resp[1])
            out = data1.strip()
            LOGGER.info("%s for %s is %s", key, chk, out)
            cmd = common_cmd.CMD_CONFSTORE_TMPLT.format(out)
            resp1 = node_obj.execute_cmd(cmd, read_lines=True)
            LOGGER.debug("confstore template command output for %s's %s: %s", chk, key, resp1)
            if resp1:
                return True, "Key from pillar and confstore match."
            return False, "Key doesn't match."
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.confstore_verification.__name__)
            return False, error

    @staticmethod
    def set_ntpsysconfg(node_obj, time_server: str, timezone: str):
        """
        Helper function to set the system NTP configuration
        param: node_obj: node object for remote execution
        param: time_server: Value to be set for time_server
        param: timezone:  Value to be set for time_zone
        return: bool, Execution response
        """
        try:
            cmd = common_cmd.CMD_SET_SYSTEM_NTP.format(time_server, timezone)
            resp = node_obj.execute_cmd(cmd, read_lines=True)
            if resp:
                return True, f"Executed {cmd}"
            return False, f"Failed {cmd}"
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.set_ntpsysconfg.__name__)
            return False, error

    @staticmethod
    def get_chrony(node_obj, time_server: str):
        """
        Helper function to grep the server value from /etc/chrony.conf
        param: node_obj: node object for remote execution
        param: time_server: Time server value to be grep
        return: bool, Execution response
        """
        cmd = common_cmd.GET_CHRONY.format(time_server)
        grep_chrony = node_obj.execute_cmd(cmd, read_lines=True)
        if time_server in grep_chrony[0]:
            return True, grep_chrony

        return False, f"{time_server} is not in /etc/chrony.conf"

    @staticmethod
    def get_ntpsysconfg(key: list, node_obj, node_id: int):
        """
        Helper function to get the system NTP configuration
        param: key: NTP keys to be verified
        param: node_obj: node object for remote execution
        param: node_id: srvnode number
        return: bool, Execution response
        """
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        data1 = []
        ntp = {}
        try:
            chk = "srvnode-{}".format(node_id)
            cmd = common_cmd.CMD_GET_SYSTEM_NTP.format(chk)
            resp = node_obj.execute_cmd(cmd, read_lines=True)
            LOGGER.debug("pillar command output for %s's system: %s\n", chk, resp)
            for value in resp:
                data1.append(ansi_escape.sub('', value).strip())
            for key_val in key:
                ntp[key_val] = data1[data1.index(key_val) + 1]
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.get_ntpsysconfg.__name__)
            return False, error
        return True, ntp

    def sysconfg_verification(
            self,
            key: list,
            node_obj,
            node_id: int,
            **kwargs):
        """
        Helper function to verify the system NTP configuration
        param: key: NTP keys to be verified
        param: node_obj: node object for remote execution
        param: node_id: srvnode number
        param: exp_t_srv: Expected time_server value
        param: exp_t_zone: Expected time_zone value
        return: bool, Execution response
        """
        exp_t_srv = kwargs.get("exp_t_srv")
        exp_t_zone = kwargs.get("exp_t_zone")
        resp = self.get_ntpsysconfg(key, node_obj, node_id)
        if resp[0]:
            if resp[1][key[0]] == exp_t_srv and resp[1][key[1]] == exp_t_zone:
                return True, resp[1]
            return False, ("NTP Configuration Verification Failed for srvnode-%s", node_id)
        return resp

    # pylint:disable=too-many-locals,too-many-statements,too-many-branches
    @staticmethod
    def create_deployment_config_universal(
            cfg_template: str,
            node_obj_list: list,
            **kwargs) -> tuple:
        """
        This method will create config.ini for CORTX deployment
        :param cfg_template: Local Path for config.ini template
        :param node_obj_list: List of Host object of all the nodes in a cluster
        :keyword mgmt_vip: mgmt_vip mandatory in case of multinode deployment
        :keyword data_disk: No. of data disk per cvg to be created on all nodes in a cluster
        :keyword cvg: No. of cvg to be created on all the nodes in a cluster
        :keyword sns_data: data units value for data pool
        :keyword sns_parity: parity units value for data pool
        :keyword sns_spare: spare units value for data pool
        :keyword dix_data: data units value for metadata pool
        :keyword dix_parity: parity units value for metadata pool
        :keyword dix_spare: spare units value for metadata pool
        :keyword skip_disk_count_check: Skip the validation for N+K+S < data disks
        :return: True/False and path of created config
        """
        mgmt_vip = kwargs.get("mgmt_vip", None)
        cvg_cnt = kwargs.get("cvg_count_per_node", "2")
        data_disk = kwargs.get("data_disk_per_cvg", "0")
        sns_data = kwargs.get("sns_data", "4")
        sns_parity = kwargs.get("sns_parity", "2")
        sns_spare = kwargs.get("sns_spare", "0")
        dix_data = kwargs.get("dix_data", "1")
        dix_parity = kwargs.get("dix_parity", "2")
        dix_spare = kwargs.get("dix_spare", "0")
        skip_disk_count_check = kwargs.get("skip_disk_count_check", False)
        config_file = "deployment_config.ini"
        shutil.copyfile(cfg_template, config_file)
        data_disk_per_cvg = int(data_disk)
        cvg_count = int(cvg_cnt)

        try:
            if mgmt_vip:
                config_utils.update_config_ini(
                    config_file,
                    section="cluster",
                    key="mgmt_vip",
                    value=mgmt_vip,
                    add_section=False)
            elif not mgmt_vip and len(node_obj_list) > 1:
                return False, "mgmt_vip is required for multinode deployment"
            valid_disk_count = int(sns_data) + int(sns_parity) + int(sns_spare)
            sns = {"data": sns_data, "parity": sns_parity, "spare": sns_spare}
            dix = {"data": dix_data, "parity": dix_parity, "spare": dix_spare}
            for node_count, node_obj in enumerate(node_obj_list, start=1):
                LOGGER.info("Configuring CVG for %s", node_obj.hostname)
                node = Template("srvnode-$serial").substitute(serial=node_count)
                hostname = node_obj.hostname
                device_list = node_obj.execute_cmd(cmd=common_cmd.CMD_LIST_DEVICES,
                                                   read_lines=True)[0].split(",")
                metadata_devices = device_list[0:cvg_count]
                device_list_len = len(device_list)
                new_device_lst_len = (device_list_len - cvg_count)
                count = cvg_count
                data_devices = list()
                if data_disk == "0":
                    data_disk_per_cvg = len(device_list[cvg_count:])
                if not skip_disk_count_check and valid_disk_count > \
                        (data_disk_per_cvg * cvg_count * len(node_obj_list)):
                    return False, "The sum of data disks per cvg " \
                                  "is less than N+K+S count"
                if (data_disk_per_cvg * cvg_count) < new_device_lst_len and data_disk != "0":
                    count_end = int(data_disk_per_cvg + cvg_count)
                    data_devices.append(",".join(device_list[cvg_count:count_end]))
                    while count:
                        count = count - 1
                        new_end = int(count_end + data_disk_per_cvg)
                        if new_end > new_device_lst_len:
                            break
                        data_devices_ad = ",".join(device_list[count_end:new_end])
                        count_end = int(count_end + data_disk_per_cvg)
                        data_devices.append(data_devices_ad)
                else:
                    last_element = device_list.pop()
                    last_element = last_element.replace("\n", "")
                    device_list.append(last_element)
                    data_devices_f = np.array_split(device_list[cvg_count:], cvg_count)
                    for count in range(0, count):
                        data_devices.append(",".join(data_devices_f[count]))

                resp = Provisioner.update_conf_file(config_file, node, hostname=hostname,
                                                    data_devices=data_devices,
                                                    metadata_devices=metadata_devices,
                                                    cvg_count=cvg_count, sns=sns,
                                                    dix=dix)
                if resp[0]:
                    LOGGER.info("Updated the config ini file %s", resp[1])
        # pylint: disable=broad-except
        except Exception as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.create_deployment_config_universal.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, config_file

    @staticmethod
    def change_field_user_password(node_obj,
                                   new_password: str) -> tuple:
        """
        Change the field user password during first time login.
        :param node_obj: node object for remote execution.
        :param new_password: Password to set for user.
        :return: True/False and message
        """
        try:
            node_obj.connect(shell=True)  #nosec
            output = ''
            time.sleep(1)
            output += node_obj.shell_obj.recv(2048).decode("utf-8")
            output = output.split('\n')[-1]
            if output.strip() == '(current) UNIX password:':
                node_obj.shell_obj.send(node_obj.password + '\n')
                LOGGER.debug("Old password when prompted was entered successfully")

            output = ''
            time.sleep(1)
            output += node_obj.shell_obj.recv(2048).decode("utf-8")
            if output.strip() == 'New password:':
                node_obj.shell_obj.send(new_password + '\n')
                LOGGER.debug("New password when prompted was entered successfully")

            output = ''
            time.sleep(1)
            output += node_obj.shell_obj.recv(2048).decode("utf-8")
            if output.strip() == 'Retype new password:':
                node_obj.shell_obj.send(new_password + '\n')
                LOGGER.debug("Re-enter new password when prompted was entered successfully")

            output = ''
            time.sleep(1)
            output += node_obj.shell_obj.recv(2048).decode("utf-8")
            if output:
                LOGGER.debug("Confirmation after setting new password is - %s", output)
        # pylint: disable=broad-except
        except Exception as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.change_field_user_password.__name__)
            LOGGER.error("Unable to set new password due to - %s", (str(error)))
            return False, error
        return True, "Password change Successful!!"

    @staticmethod
    def update_conf_file(config_file, node, **kwargs):
        """
        This method is to update the file with CVG details
        Params: config_file: ini file used for deployment
        node: Host object of all the nodes in a cluster
        hostname: server hostname
        cvg_count: No. of cvg to be created on all the nodes in a cluster
        metadata_devices: metadata devices used for CVG
        data_devices data devices used for CVG
        returns True and config file path
        """
        hostname = kwargs.get("hostname")
        cvg_count = kwargs.get("cvg_count")
        metadata_devices = kwargs.get("metadata_devices")
        data_devices = kwargs.get("data_devices")
        sns = kwargs.get("sns")
        dix = kwargs.get("dix")

        LOGGER.info("Configuring SNS pool : %s", sns)
        for key, value in sns.items():
            config_utils.update_config_ini(
                config_file,
                section="srvnode_default",
                key=Template("storage.durability.sns.$sns").substitute(sns=key),
                value=value,
                add_section=False)
        LOGGER.info("Configuring DIX pool  : %s", dix)
        for key, value in dix.items():
            config_utils.update_config_ini(
                config_file,
                section="srvnode_default",
                key=Template("storage.durability.dix.$dix").substitute(dix=key),
                value=value,
                add_section=False)
        config_utils.update_config_ini(config_file, node,
                                       key="hostname",
                                       value=hostname,
                                       add_section=False)
        for cvg in range(0, cvg_count):
            LOGGER.info("CVG : %s", cvg)
            LOGGER.info("Updating Data Devices: %s", data_devices[cvg])
            config_utils.update_config_ini(
                config_file,
                node,
                key=Template("storage.cvg.$num.data_devices").substitute(num=cvg),
                value=data_devices[cvg],
                add_section=False)
            LOGGER.info("Updating Metadata Devices: %s", metadata_devices[cvg])
            config_utils.update_config_ini(
                config_file,
                node,
                key=Template("storage.cvg.$num.metadata_devices").substitute(num=cvg),
                value=metadata_devices[cvg],
                add_section=False)
        return True, config_file
