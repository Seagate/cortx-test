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

"""
Provisioner utiltiy methods
"""
import shutil
import logging
import time
import jenkins
import re
from commons import constants as common_cnst
from commons import commands as common_cmd
from commons import params as prm
from commons import pswdmanager
from commons.utils import config_utils


LOGGER = logging.getLogger(__name__)


class Provisioner:
    """This class contains utility methods for all the provisioning related operations"""

    @staticmethod
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
            while True:
                if jenkins_server_obj.get_job_info(job_name)['lastCompletedBuild']['number'] == \
                        jenkins_server_obj.get_job_info(job_name)['lastBuild']['number']:
                    break
            build_info = jenkins_server_obj.get_build_info(
                job_name, next_build_number)
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
        node1_obj.connect(shell=True)
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
            LOGGER.debug("pillar command output for {}'s {}: {}".format(chk, key, resp))
            data1 = ansi_escape.sub('', resp[1])
            out = data1.strip()
            LOGGER.info("{} for {} is {}".format(key, chk, out))
            cmd = common_cmd.CMD_CONFSTORE_TMPLT.format(out)
            resp1 = node_obj.execute_cmd(cmd, read_lines=True)
            LOGGER.debug("confstore template command output for {}'s {}: {}".format(chk, key, resp1))
            if resp1:
                return True, "Key from pillar and confstore match."
            else:
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
            cmd = common_cmd.CMD_SALT_SET_SYSTEM.format(time_server, timezone)
            resp = node_obj.execute_cmd(cmd, read_lines=True)
            if resp:
                return True, f"Executed {cmd}"
            else:
                return False, f"Failed {cmd}"
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.set_ntpsysconfg.__name__)
            return False, error

    @staticmethod
    def get_chrony(time_server: str):
        """
        Helper function to grap the server value from /etc/chrony.conf
        return: bool, Execution response
        """
        grap_chrony = common_cmd.GET_CHRONY.format(time_server)
        if time_server in grap_chrony:
            return True, grap_chrony
        else:
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
            cmd = common_cmd.CMD_SALT_GET_SYSTEM.format(chk)
            resp = node_obj.execute_cmd(cmd, read_lines=True)
            LOGGER.debug("pillar command output for {}'s system: {}\n".format(chk, resp))
            for ii in range(len(resp)):
                data1.append(ansi_escape.sub('', resp[ii]).strip())
            for key_val in key:
                ntp[key_val] = data1[data1.index(key_val) + 1]
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                Provisioner.get_ntpsysconfg.__name__)
            return False, error
        return True, ntp

    def sysconfg_verification(self, key: list, node_obj, node_id: int, exp_t_srv=str, exp_t_zone=str):
        """
        Helper function to verify the system NTP configuration
        param: key: NTP keys to be verified
        param: node_obj: node object for remote execution
        param: node_id: srvnode number
        param: exp_t_srv: Expected time_server value
        param: exp_t_zone: Expected time_zone value
        return: bool, Execution response
        """
        resp = self.get_ntpsysconfg(key, node_obj, node_id)
        if resp[0]:
            if resp[1][key[0]] == exp_t_srv and resp[1][key[1]] == exp_t_zone:
                return True, resp[1]
            else:
                return False, f"NTP Configuration Verification Failed for srvnode-{node_id}"
        else:
            return resp
