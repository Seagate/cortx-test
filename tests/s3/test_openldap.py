# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""OpenLDAP Test Module."""

import time
import logging
from datetime import datetime

import paramiko
import pytest

from config import CMN_CFG
from config.s3 import S3_LDAP_TST_CFG
from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.node_helper import Node
from commons.utils.config_utils import get_config
from commons.utils.system_utils import run_remote_cmd, remove_file, path_exists
from commons.utils.assert_utils import assert_false, assert_true
from commons.utils.assert_utils import assert_in, assert_equal, assert_not_equal
from libs.s3 import S3H_OBJ, LDAP_PASSWD


class TestOpenLdap:
    """Open LDAP Test Suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info(CMN_CFG["nodes"])
        cls.host = CMN_CFG["nodes"][0]["host"]
        cls.username = CMN_CFG["nodes"][0]['username']
        cls.pwd = CMN_CFG["nodes"][0]['password']
        cls.cm_ldap_cfg = S3_LDAP_TST_CFG["common_vars"]
        cls.openldap_path = cls.cm_ldap_cfg["openldap_path"]
        cls.slapd_dir = cls.cm_ldap_cfg["slapd_dir"]
        cls.slapd_service = cls.cm_ldap_cfg["slapd_service"]
        cls.datestamp = datetime.today().strftime(
            cls.cm_ldap_cfg["date_format"])
        cls.backup_path = cls.cm_ldap_cfg["backup_path"]
        cls.default_ldap_pw = True
        cls.host = CMN_CFG["nodes"][0]["host"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                            password=cls.passwd)

    def remote_execution(self, hostname, username, password, cmd):
        """running remote cmd."""
        self.log.info("Remote Execution")
        return run_remote_cmd(
            cmd=cmd,
            hostname=hostname,
            username=username,
            password=password,
            read_lines=True)

    def chown_dir(self, ch_owner_cmd, owner, chk_owner_cmd, ch_owner_dir):
        """
        Function will change the ownership of a directory to specified owner.

        :param str ch_owner_cmd: A change owner command to be executed.
        :param str owner: A new owner of a directory.
        :param str chk_owner_cmd: A check owner command.
        :param str ch_owner_dir: A directory for which owner to be changed.
        :return: None
        """
        self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            ch_owner_cmd)
        self.log.info(ch_owner_cmd)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            chk_owner_cmd)
        self.log.info(chk_owner_cmd)
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        dir_data = [_dir for _dir in resp if ch_owner_dir in _dir]
        new_owner = dir_data[0].split()[2]
        assert_equal(
            new_owner,
            owner,
            self.cm_ldap_cfg["ch_owner_err"].format(ch_owner_dir))

    def get_owner(self, dir_path, dir_name):
        """
        Function will retrieve the owner of specified directory.

        :param str dir_path: A parent directory path.
        :param str dir_name: Name of a directory whose owner to be retrieved.
        :return: An owner of a specified directory.
        :rtype: str
        """
        cmd = self.cm_ldap_cfg["chk_owner_cmd"].format(dir_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            cmd)
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        dir_data = [_dir for _dir in resp if dir_name in _dir]
        dir_owner = dir_data[0].split()[2]

        return dir_owner

    def backup_dir(self, bkp_cmd, backup_data, ls_cmd):
        """
        Function will execute the specified backup command.

        It will also verify if specified backup directory/file is created under
        given destination directory.
        :param str bkp_cmd: A backup command to be executed.
        :param str backup_data: Name of a backup directory/file.
        :param str ls_cmd: A ls command on destination directory where backup will be created.
        :return: None
        """
        self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            bkp_cmd)
        self.log.info(bkp_cmd)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            ls_cmd)
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        assert_in(
            backup_data,
            resp,
            self.cm_ldap_cfg["backup_dir_err"].format(
                backup_data,
                ls_cmd[3:]))

    def create_dir(self, cr_cmd, new_dir_name, ls_cmd):
        """
        Function will execute the given command to create a new directory.

        It also will check verify if new directory is created under specified destination directory.
        :param str cr_cmd: A command to be executed to create a new directory.
        :param str new_dir_name: Name of a new directory.
        :param str ls_cmd:ls command on a destination directory where new directory will be created.
        :return: None
        """
        self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            cr_cmd)
        self.log.info(cr_cmd)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            ls_cmd)
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        assert_in(
            new_dir_name,
            resp,
            self.cm_ldap_cfg["cr_dir_err"].format(
                new_dir_name,
                ls_cmd[3:]))

    def restore_dir(self, re_cmd, files_lst, ls_cmd):
        """
        Function will execute given command to restore openldap dirs.

        :param str re_cmd: A restore command to be executed.
        :param list files_lst: List of file/s to be checked after restoring.
        :param str ls_cmd: Destination directory where new directory will be restored.
        :return: None
        """
        self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            re_cmd)
        self.log.info(re_cmd)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            ls_cmd)
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        for file in files_lst:
            assert_in(
                file,
                resp,
                self.cm_ldap_cfg["restore_dir_err"].format(ls_cmd[3:]))

    def execute_shell_cmd(self, ch_pwd_cmd, cd_cmd, verify_statement):
        """
        Function executes interactive shell command server and returns it's output.

        :param str ch_pwd_cmd: A change password command to be executed.
        :param str cd_cmd: A change directory to be executed.
        :param str verify_statement: End statement expected once the command execution is complete.
        :return: Output of command executed
        :rtype: str
        """
        channel_data = str()
        hosts = list()
        for i in range(len(CMN_CFG["nodes"])):
            hosts.append(CMN_CFG["nodes"][i]["host"])
        self.log.info("Creating a shell session on channel...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        for host in hosts:
            ssh.connect(hostname=host, username=self.username, password=self.pwd)
            channel = ssh.invoke_shell()
            self.log.info("Created a shell session on channel")
            while True:
                time.sleep(self.cm_ldap_cfg["channel_time_pause"])
                if channel.recv_ready():
                    channel_data += channel.recv(
                        self.cm_ldap_cfg["output_bytes"]).decode(
                        self.cm_ldap_cfg["decode_format"])
                else:
                    continue
                if verify_statement in channel_data:
                    self.log.info("Command executed successfully")
                    break
                if channel_data.endswith(self.cm_ldap_cfg["root_prmpt"]):
                    time.sleep(self.cm_ldap_cfg["channel_time_pause"])
                    channel.send(
                        "".join([cd_cmd, self.cm_ldap_cfg["press_enter"]]))
                elif channel_data.endswith(self.cm_ldap_cfg["scr_dir_prmpt"]):
                    time.sleep(self.cm_ldap_cfg["channel_time_pause"])
                    self.log.info(
                        "Executing command: %s", ch_pwd_cmd)
                    time.sleep(self.cm_ldap_cfg["channel_time_pause"])
                    channel.send(
                        "".join([ch_pwd_cmd, self.cm_ldap_cfg["press_enter"]]))
                elif channel_data.endswith(self.cm_ldap_cfg["pwd_prompt_msg"]):
                    channel.send(
                        "".join([self.cm_ldap_cfg["root_pwd"], self.cm_ldap_cfg["press_enter"]]))
                else:
                    break
            # Closing the channel flushes the buffer data from the pipe
            ssh.close()

        return channel_data

    def setup_method(self):
        """
        Function will be invoked prior each test case.

        It will perform below operations:
            - Initialize few common variables.
            - Create backup directory named "backup" under "/root".
        """
        self.log.info("STARTED: Setup operations")
        self.log.info(
            "Creating a backup directory %s...",
            self.backup_path)
        self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.cm_ldap_cfg["mk_dir_cmd"].format(self.backup_path))
        self.log.info(
            "Created a backup directory %s", self.backup_path)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will perform below operations:
            - Restart slapd service.
            - Delete the backup directory created under "/root".
            - Change the owner of ldap config and data directory to "ldap".
        """
        self.log.info("STARTED: Teardown operations")
        ldap_cfg_path = f"{self.openldap_path}/{self.slapd_dir}"
        if self.get_owner(
                self.openldap_path,
                self.slapd_dir) != self.cm_ldap_cfg["ldap_owner"]:
            self.log.info(
                "Changing owner of openldap configuration directory to ldap...")
            ch_owner_cmd = self.cm_ldap_cfg["ch_owner_cmd"].format(
                ldap_cfg_path)
            chk_owner_cmd = self.cm_ldap_cfg["chk_owner_cmd"].format(
                self.openldap_path)
            self.chown_dir(
                ch_owner_cmd,
                self.cm_ldap_cfg["ldap_owner"],
                chk_owner_cmd,
                self.slapd_dir)
            self.log.info(
                "Changed owner of openldap configuration directory to ldap")
        data_path = f"{self.cm_ldap_cfg['ldap_data_path']}/{self.cm_ldap_cfg['ldap_data_dir']}"
        if self.get_owner(
                self.cm_ldap_cfg['ldap_data_path'],
                self.cm_ldap_cfg['ldap_data_dir']) != self.cm_ldap_cfg["ldap_owner"]:
            self.log.info(
                "Changing owner of openldap data directory to ldap...")
            ch_owner_cmd = self.cm_ldap_cfg["ch_owner_cmd"].format(data_path)
            chk_owner_cmd = self.cm_ldap_cfg["chk_owner_cmd"].format(
                self.cm_ldap_cfg["ldap_data_path"])
            self.chown_dir(
                ch_owner_cmd,
                self.cm_ldap_cfg["ldap_owner"],
                chk_owner_cmd,
                self.cm_ldap_cfg['ldap_data_dir'])
            self.log.info(
                "Changed owner of openldap data directory to ldap")
        if not self.default_ldap_pw:
            self.log.info("Step 2: Restoring openldap password")
            default_pw = LDAP_PASSWD
            ch_pwd_cmd = self.cm_ldap_cfg["ch_pwd_cmd"].format(
                const.AUTHSERVER_FILE, default_pw)
            resp = self.execute_shell_cmd(
                ch_pwd_cmd,
                const.SCRIPT_PATH,
                self.cm_ldap_cfg["output_str"])
            self.log.info("Response is : %s", resp)
            self.log.info(
                "Restarting %s service",
                self.slapd_service)
            resp = S3H_OBJ.restart_s3server_service(self.slapd_service)
            assert_true(resp[0], resp[1])
            self.log.info("Step 2: Restored openldap password")
        if not S3H_OBJ.get_s3server_service_status(self.slapd_service)[0]:
            self.log.info(
                "Starting %s service...",
                self.slapd_service)
            S3H_OBJ.start_s3server_service(self.slapd_service)
            resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
            assert_true(resp[0], resp[1])
            self.log.info("Started %s service", self.slapd_service)
        self.log.info("Deleting backup dir %s...", self.backup_path)
        self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.cm_ldap_cfg["rm_dir_cmd"].format(self.backup_path))
        self.log.info("Deleted backup dir %s", self.backup_path)
        if path_exists(self.cm_ldap_cfg["temp_path"]):
            remove_file(self.cm_ldap_cfg["temp_path"])
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-7948')
    @CTFailOn(error_handler)
    def test_5066(self):
        """Test to verify & check backup of openldap config directory is done successfully."""
        self.log.info(
            "STARTED: Test to verify and check backup of openldap "
            "configuration directory is done successfully")
        cfg_5066 = S3_LDAP_TST_CFG["test_5066"]
        backup_cfg_file = self.cm_ldap_cfg["cfg_backup_file"]
        slapd_err = self.cm_ldap_cfg["slapd_err"]
        self.log.info(
            "Step 1: Verifying if %s is present under %s",
            self.slapd_dir, self.openldap_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.cm_ldap_cfg["ls_cmd"])
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        assert_in(
            self.slapd_dir,
            resp,
            slapd_err.format(
                self.openldap_path))
        self.log.info(
            "Step 1: Verified %s is present under %s",
            self.slapd_dir, self.openldap_path)
        self.log.info(
            "Step 2: Taking a backup of %s directory", self.slapd_dir)
        slapcat_cmd = self.cm_ldap_cfg["slapcat_cmd"].format(
            cfg_5066["db_no"], self.backup_path, backup_cfg_file)
        self.backup_dir(
            slapcat_cmd,
            backup_cfg_file,
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s directory successfully",
            self.slapd_dir)
        self.log.info(
            "ENDED: Test to verify and check backup of openldap "
            "configuration directory is done successfully")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-7949')
    @CTFailOn(error_handler)
    def test_5067(self):
        """Test to verify and check backup of openldap Data Directories is done successfully."""
        self.log.info(
            "STARTED: Test to verify & check backup of "
            "openldap Data Directories is done successfully")
        cfg_5067 = S3_LDAP_TST_CFG["test_5067"]
        ldap_data_path = self.cm_ldap_cfg["ldap_data_path"]
        ldap_data_dir = self.cm_ldap_cfg["ldap_data_dir"]
        backup_data_file = self.cm_ldap_cfg["data_backup_file"]
        ldap_data_dir_err = cfg_5067["ldap_data_dir_err"]
        self.log.info(
            "Step 1: Verifying if ldap data directory named as %s is present under %s",
            ldap_data_dir,
            ldap_data_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.cm_ldap_cfg["ls_ldap_data_cmd"])
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        assert_in(
            ldap_data_dir,
            resp,
            ldap_data_dir_err.format(ldap_data_path))
        self.log.info(
            "Step 1: Verified ldap data directory %s is present under %s",
            ldap_data_dir, ldap_data_path)
        self.log.info("Step 2: Taking a backup of ldap data directory")
        slapcat_cmd = self.cm_ldap_cfg["slapcat_cmd"].format(
            cfg_5067["db_no"], self.backup_path, backup_data_file)
        self.backup_dir(
            slapcat_cmd,
            backup_data_file,
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of ldap data directory successfully")
        self.log.info(
            "ENDED: Test to verify & check backup of openldap Data Directory is done successfully")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-7950')
    @CTFailOn(error_handler)
    def test_5068(self):
        """Test to verify & check restore of openldap config directory is done successfully."""
        self.log.info(
            "STARTED: Test to verify and check restore of openldap configuration "
            "directory is done successfully")
        cfg_5068 = S3_LDAP_TST_CFG["test_5068"]
        slapd_err = self.cm_ldap_cfg["slapd_err"]
        bkp_config_dir = f"{self.slapd_dir}.{self.datestamp}"
        self.log.info(
            "Step 1: Verifying if openldap configuration directory is present under %s",
            self.openldap_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.cm_ldap_cfg["ls_cmd"])
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        assert_in(
            self.slapd_dir,
            resp,
            slapd_err.format(
                self.openldap_path))
        self.log.info(
            "Step 1: Verified openldap configuration directory is present under %s",
            self.openldap_path)
        self.log.info(
            "Step 2: Taking a backup of %s file ",
            self.cm_ldap_cfg["cfg_backup_file"])
        slapcat_cmd = self.cm_ldap_cfg["slapcat_cmd"].format(
            cfg_5068["db_no"], self.backup_path, self.cm_ldap_cfg["cfg_backup_file"])
        self.backup_dir(
            slapcat_cmd,
            self.cm_ldap_cfg["cfg_backup_file"],
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s file ",
            self.cm_ldap_cfg["cfg_backup_file"])
        self.log.info(
            "Step 3: Stopping %s service",
            self.slapd_service)
        S3H_OBJ.stop_s3server_service(self.slapd_service)
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_false(resp[0], resp[1])
        self.log.info(
            "Step 3: Stopped %s service",
            self.slapd_service)
        self.log.info(
            "Step 4: Taking a backup of openldap configuration directory")
        backup_cmd = self.cm_ldap_cfg["backup_slapd_dir_cmd"].format(bkp_config_dir)
        self.backup_dir(
            backup_cmd,
            bkp_config_dir,
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 4: Taken a backup of openldap configuration directory successfully")
        self.log.info(
            "Step 5: Creating a new %s directory under %s",
            self.slapd_dir, self.openldap_path)
        self.create_dir(
            self.cm_ldap_cfg["cr_slapd_dir_cmd"],
            self.slapd_dir,
            self.cm_ldap_cfg["ls_cmd"])
        self.log.info(
            "Step 5: Created a new %s directory under %s",
            self.slapd_dir, self.openldap_path)
        self.log.info("Step 6: Restoring openldap configuration directory")
        restore_cmd = self.cm_ldap_cfg["restore_slapd_cmd"].format(self.backup_path)
        self.restore_dir(
            restore_cmd,
            self.cm_ldap_cfg["ldap_config_files"],
            self.cm_ldap_cfg["ls_slapd_dir"])
        self.log.info(
            "Step 6: Restored openldap configuration directory successfully")
        self.log.info(
            "Step 7: Changing owner of ldap configuration directory to %s",
            self.cm_ldap_cfg["ldap_owner"])
        ldap_cfg_path = f"{self.openldap_path}/{self.slapd_dir}"
        ch_owner_cmd = self.cm_ldap_cfg["ch_owner_cmd"].format(ldap_cfg_path)
        chk_owner_cmd = self.cm_ldap_cfg["chk_owner_cmd"].format(
            self.openldap_path)
        self.chown_dir(
            ch_owner_cmd,
            self.cm_ldap_cfg["ldap_owner"],
            chk_owner_cmd,
            self.slapd_dir)
        self.log.info(
            "Step 7: Changed owner of ldap configuration directory to %s successfully",
            self.cm_ldap_cfg["ldap_owner"])
        self.log.info(
            "ENDED: Test to verify and check restore of openldap "
            "configuration directory is done successfully")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-7951')
    @CTFailOn(error_handler)
    def test_5069(self):
        """
        Test to verify and check.

        if ownership and permissions of the configuration directory
        is changed to what it was previously before restore.
        """
        self.log.info(
            "STARTED: Test to verify and check if ownership and "
            "permissions of the configuration directory "
            "is changed to what it was previously before restore.")
        cfg_5069 = S3_LDAP_TST_CFG["test_5069"]
        slapd_err = self.cm_ldap_cfg["slapd_err"]
        bkp_config_dir = f"{self.slapd_dir}.{self.datestamp}"
        self.log.info(
            "Step 1: Verifying if openldap configuration directory is present under %s",
            self.openldap_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.cm_ldap_cfg["ls_cmd"])
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        assert_in(
            self.slapd_dir,
            resp,
            slapd_err.format(
                self.openldap_path))
        self.log.info(
            "Step 1: Verified openldap configuration directory is present under %s",
            self.openldap_path)
        self.log.info(
            "Step 2: Taking a backup of %s file ",
            self.cm_ldap_cfg["cfg_backup_file"])
        slapcat_cmd = self.cm_ldap_cfg["slapcat_cmd"].format(
            cfg_5069["db_no"], self.backup_path, self.cm_ldap_cfg["cfg_backup_file"])
        self.backup_dir(
            slapcat_cmd,
            self.cm_ldap_cfg["cfg_backup_file"],
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s file ",
            self.cm_ldap_cfg["cfg_backup_file"])
        self.log.info(
            "Step 3: Stopping %s service",
            self.slapd_service)
        S3H_OBJ.stop_s3server_service(self.slapd_service)
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_false(resp[0], resp[1])
        self.log.info(
            "Step 3: Stopped %s service",
            self.slapd_service)
        self.log.info(
            "Step 4: Taking a backup of openldap configuration directory")
        backup_cmd = self.cm_ldap_cfg["backup_slapd_dir_cmd"].format(bkp_config_dir)
        self.backup_dir(
            backup_cmd,
            bkp_config_dir,
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 4: Taken a backup of openldap configuration directory successfully")
        self.log.info(
            "Step 5: Checking ownership of backup configuration directory")
        dir_owner = self.get_owner(self.backup_path, bkp_config_dir)
        assert_equal(dir_owner, self.cm_ldap_cfg["ldap_owner"], dir_owner)
        self.log.info(
            "Step 5: Checked owner of backup configuration directory is %s",
            self.cm_ldap_cfg["ldap_owner"])
        self.log.info(
            "Step 6: Creating a new %s directory under %s",
            self.slapd_dir, self.openldap_path)
        self.create_dir(
            self.cm_ldap_cfg["cr_slapd_dir_cmd"],
            self.slapd_dir,
            self.cm_ldap_cfg["ls_cmd"])
        self.log.info(
            "Step 6: Created a new %s directory under %s",
            self.slapd_dir, self.openldap_path)
        self.log.info("Step 7: Restoring openldap configuration directory")
        restore_cmd = self.cm_ldap_cfg["restore_slapd_cmd"].format(self.backup_path)
        self.restore_dir(
            restore_cmd,
            self.cm_ldap_cfg["ldap_config_files"],
            self.cm_ldap_cfg["ls_slapd_dir"])
        self.log.info(
            "Step 7: Restored openldap configuration directory successfully")
        self.log.info(
            "Step 8: Changing owner of ldap configuration directory to %s",
            self.cm_ldap_cfg["ldap_owner"])
        ldap_cfg_path = f"{self.openldap_path}/{self.slapd_dir}"
        ch_owner_cmd = self.cm_ldap_cfg["ch_owner_cmd"].format(ldap_cfg_path)
        chk_owner_cmd = self.cm_ldap_cfg["chk_owner_cmd"].format(
            self.openldap_path)
        self.chown_dir(
            ch_owner_cmd,
            self.cm_ldap_cfg["ldap_owner"],
            chk_owner_cmd,
            self.slapd_dir)
        self.log.info(
            "Step 8: Changed owner of ldap configuration directory to %s successfully",
            self.cm_ldap_cfg["ldap_owner"])
        self.log.info(
            "ENDED: Test to verify and check if ownership and "
            "permissions of the configuration directory is changed "
            "to what it was previously before restore.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-7952')
    @CTFailOn(error_handler)
    def test_5070(self):
        """Test to verify and check restore of openldap data directories is done successfully."""
        self.log.info(
            "STARTED: Test to verify and check restore of "
            "openldap data directories is done successfully")
        cfg_5070 = S3_LDAP_TST_CFG["test_5070"]
        ldap_data_path = self.cm_ldap_cfg["ldap_data_path"]
        ldap_data_dir = self.cm_ldap_cfg["ldap_data_dir"]
        ldap_data_err = self.cm_ldap_cfg["ldap_data_err"]
        bkp_ldap_data_dir = f"{ldap_data_dir}{self.datestamp}"
        self.log.info(
            "Step 1: Verifying that ldap data directory is present under %s",
            ldap_data_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.cm_ldap_cfg["ls_ldap_data_cmd"])
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        assert_in(
            ldap_data_dir,
            resp,
            ldap_data_err.format(ldap_data_path))
        self.log.info(
            "Step 1: Verified that ldap data directory is present under %s",
            ldap_data_path)
        self.log.info(
            "Step 2: Taking a backup of %s file ",
            self.cm_ldap_cfg["data_backup_file"])
        slapcat_cmd = self.cm_ldap_cfg["slapcat_cmd"].format(
            cfg_5070["db_no"], self.backup_path, self.cm_ldap_cfg["data_backup_file"])
        self.backup_dir(
            slapcat_cmd,
            self.cm_ldap_cfg["data_backup_file"],
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s file ",
            self.cm_ldap_cfg["data_backup_file"])
        self.log.info(
            "Step 3: Stopping %s service",
            self.slapd_service)
        S3H_OBJ.stop_s3server_service(self.slapd_service)
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_false(resp[0], resp[1])
        self.log.info(
            "Step 3: Stopped %s service",
            self.slapd_service)
        self.log.info("Step 4: Taking a backup of ldap data directory")
        backup_cmd = self.cm_ldap_cfg["backup_ldap_dir_cmd"].format(bkp_ldap_data_dir)
        self.backup_dir(
            backup_cmd,
            bkp_ldap_data_dir,
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 4: Taken a backup of ldap data directory successfully")
        self.log.info(
            "Step 5: Creating openldap data directory under %s",
            ldap_data_path)
        self.create_dir(
            self.cm_ldap_cfg["cr_ldap_dir_cmd"],
            ldap_data_dir,
            self.cm_ldap_cfg["ls_ldap_data_cmd"])
        self.log.info(
            "Step 5: Created openldap data directory under %s", ldap_data_path)
        self.log.info("Step 6: Restoring openldap data directory")
        restore_cmd = self.cm_ldap_cfg["restore_ldap_cmd"].format(self.backup_path)
        self.restore_dir(
            restore_cmd,
            self.cm_ldap_cfg["ldap_config_files"],
            self.cm_ldap_cfg["ls_slapd_dir"])
        self.log.info(
            "Step 6: Restored openldap data directory successfully")
        self.log.info(
            "Step 7: Changing owner of ldap configuration directory to %s",
            self.cm_ldap_cfg["ldap_owner"])
        data_path = f"{ldap_data_path}/{ldap_data_dir}"
        ch_owner_cmd = self.cm_ldap_cfg["ch_owner_cmd"].format(data_path)
        chk_owner_cmd = self.cm_ldap_cfg["chk_owner_cmd"].format(
            ldap_data_path)
        self.chown_dir(
            ch_owner_cmd,
            self.cm_ldap_cfg["ldap_owner"],
            chk_owner_cmd,
            ldap_data_dir)
        self.log.info(
            "Step 7: Changed owner of ldap configuration directory to %s successfully",
            self.cm_ldap_cfg["ldap_owner"])
        self.log.info(
            "ENDED: Test to verify and check restore of "
            "openldap data directories is done successfully")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-7953')
    @CTFailOn(error_handler)
    def test_5071(self):
        """
        Test to verify and check.

        Change if ownership and permissions of the data directory to what it was previously.
        """
        self.log.info(
            "STARTED: Test to verify and check change if ownership "
            "and permissions of the data directory to what it was previously")
        cfg_5071 = S3_LDAP_TST_CFG["test_5071"]
        ldap_data_path = self.cm_ldap_cfg["ldap_data_path"]
        ldap_data_dir = self.cm_ldap_cfg["ldap_data_dir"]
        ldap_data_err = self.cm_ldap_cfg["ldap_data_err"]
        bkp_ldap_data_dir = f"{ldap_data_dir}{self.datestamp}"
        self.log.info(
            "Step 1: Verifying that ldap data directory is present under %s",
            ldap_data_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.cm_ldap_cfg["ls_ldap_data_cmd"])
        assert status, resp
        resp = list(map(lambda s: s.strip(), resp))
        assert_in(
            ldap_data_dir,
            resp,
            ldap_data_err.format(ldap_data_path))
        self.log.info(
            "Step 1: Verified that ldap data directory is present under %s",
            ldap_data_path)
        self.log.info(
            "Step 2: Taking a backup of %s file ",
            self.cm_ldap_cfg["data_backup_file"])
        slapcat_cmd = self.cm_ldap_cfg["slapcat_cmd"].format(
            cfg_5071["db_no"], self.backup_path, self.cm_ldap_cfg["data_backup_file"])
        self.backup_dir(
            slapcat_cmd,
            self.cm_ldap_cfg["data_backup_file"],
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s file ",
            self.cm_ldap_cfg["data_backup_file"])
        self.log.info(
            "Step 3: Stopping %s service",
            self.slapd_service)
        S3H_OBJ.stop_s3server_service(self.slapd_service)
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_false(resp[0], resp[1])
        self.log.info(
            "Step 3: Stopped %s service",
            self.slapd_service)
        self.log.info("Step 4: Taking a backup of ldap data directory")
        backup_cmd = self.cm_ldap_cfg["backup_ldap_dir_cmd"].format(bkp_ldap_data_dir)
        self.backup_dir(
            backup_cmd,
            bkp_ldap_data_dir,
            self.cm_ldap_cfg["ls_backup_path"])
        self.log.info(
            "Step 4: Taken a backup of ldap data directory successfully")
        self.log.info("Step 5: Checking ownership of backup data directory")
        dir_owner = self.get_owner(self.backup_path, bkp_ldap_data_dir)
        assert_equal(dir_owner, self.cm_ldap_cfg["ldap_owner"], dir_owner)
        self.log.info(
            "Step 5: Checked owner of backup configuration directory is %s",
            self.cm_ldap_cfg["ldap_owner"])
        self.log.info(
            "Step 6: Creating openldap data directory under %s",
            ldap_data_path)
        self.create_dir(
            self.cm_ldap_cfg["cr_ldap_dir_cmd"],
            ldap_data_dir,
            self.cm_ldap_cfg["ls_ldap_data_cmd"])
        self.log.info(
            "Step 6: Created openldap data directory under %s", ldap_data_path)
        self.log.info("Step 7: Restoring openldap data directory")
        restore_cmd = self.cm_ldap_cfg["restore_ldap_cmd"].format(self.backup_path)
        self.restore_dir(
            restore_cmd,
            self.cm_ldap_cfg["ldap_config_files"],
            self.cm_ldap_cfg["ls_slapd_dir"])
        self.log.info(
            "Step 7: Restored openldap data directory successfully")
        self.log.info(
            "Step 8: Changing owner of ldap configuration directory to %s",
            self.cm_ldap_cfg["ldap_owner"])
        data_path = f"{ldap_data_path}/{ldap_data_dir}"
        ch_owner_cmd = self.cm_ldap_cfg["ch_owner_cmd"].format(data_path)
        chk_owner_cmd = self.cm_ldap_cfg["chk_owner_cmd"].format(
            ldap_data_path)
        self.chown_dir(
            ch_owner_cmd,
            self.cm_ldap_cfg["ldap_owner"],
            chk_owner_cmd,
            ldap_data_dir)
        self.log.info(
            "Step 8: Changed owner of ldap configuration directory to %s successfully",
            self.cm_ldap_cfg["ldap_owner"])
        self.log.info(
            "ENDED: Test to verify and check change if ownership and "
            "permissions of the data directory to what it was previously")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-8020')
    @CTFailOn(error_handler)
    def test_5073(self):
        """
        Test to verify and check.

        if password reset is done successfully using enc_ldap_passwd_in_cfg.sh script.
        """
        self.log.info(
            "STARTED: Test to verify and check if password reset is done successfully using "
            "enc_ldap_passwd_in_cfg.sh script.")
        cfg_5073 = S3_LDAP_TST_CFG["test_5073"]
        new_passwd = cfg_5073["new_pwd"]
        self.log.info("Step 1: Changing openldap password")
        ch_pwd_cmd = self.cm_ldap_cfg["ch_pwd_cmd"].format(
            const.AUTHSERVER_FILE, new_passwd)
        resp = self.execute_shell_cmd(
            ch_pwd_cmd,
            const.SCRIPT_PATH,
            self.cm_ldap_cfg["output_str"])
        assert_in(self.cm_ldap_cfg["output_msg"], resp, resp)
        self.log.info("Step 1: Changed openldap password successfully")
        self.log.info(
            "Step 2: Restarting %s service",
            self.slapd_service)
        resp = S3H_OBJ.restart_s3server_service(self.slapd_service)
        assert_true(resp[0], resp[1])
        time.sleep(self.cm_ldap_cfg["restart_serv_pause"])
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Restarted %s service",
            self.slapd_service)
        self.log.info(
            "ENDED: Test to verify and check if password reset is done successfully using "
            "enc_ldap_passwd_in_cfg.sh script.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-8021')
    @CTFailOn(error_handler)
    def test_5074(self):
        """Test to verify & check if authserver properties file is updated post pwd change/reset."""
        self.log.info(
            "STARTED: Test to verify and check if authserver.properties"
            "file is updated post password change/reset")
        cfg_5074 = S3_LDAP_TST_CFG["test_5074"]
        temp_file = self.cm_ldap_cfg["temp_path"]
        new_passwd = cfg_5074["new_pwd"]
        self.log.info("Step 1: Retrieving existing openldap password")
        self.node_obj.copy_file_to_local(const.AUTHSERVER_FILE, temp_file)
        old_pwd = get_config(
            temp_file, key=self.cm_ldap_cfg["login_pwd_section"])
        self.log.info("Password : %s", old_pwd)
        self.log.info("Step 1: Retrieved existing openldap password")
        self.log.info("Step 2: Changing openldap password")
        ch_pwd_cmd = self.cm_ldap_cfg["ch_pwd_cmd"].format(
            const.AUTHSERVER_FILE, new_passwd)
        resp = self.execute_shell_cmd(
            ch_pwd_cmd,
            const.SCRIPT_PATH,
            self.cm_ldap_cfg["output_str"])
        self.log.info("Response is : %s", resp)
        assert_in(self.cm_ldap_cfg["output_msg"], resp, resp)
        self.log.info("Step 2: Changed openldap password successfully")
        self.log.info(
            "Step 3: Restarting %s service",
            self.slapd_service)
        resp = S3H_OBJ.restart_s3server_service(self.slapd_service)
        assert_true(resp[0], resp[1])
        time.sleep(self.cm_ldap_cfg["restart_serv_pause"])
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Restarted %s service",
            self.slapd_service)
        self.log.info(
            "Step 4: Checking if new password is updated or not")
        self.node_obj.copy_file_to_local(const.AUTHSERVER_FILE, temp_file)
        updated_pwd = get_config(
            temp_file, key=self.cm_ldap_cfg["login_pwd_section"])
        self.log.info("Password : %s", updated_pwd)
        assert_not_equal(old_pwd, updated_pwd, self.cm_ldap_cfg["err_message"])
        self.log.info(
            "Step 4: New password is updated successfully")
        self.default_ldap_pw = False
        self.log.info(
            "ENDED: Test to verify and check if authserver.properties "
            "file is updated post password change/reset")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-8022')
    @CTFailOn(error_handler)
    def test_5075(self):
        """
        Test to verify and check.

        if password allows special characters with uppercase/lowercase characters.
        """
        self.log.info(
            "STARTED: Test to verify and check if password allows special characters"
            "with uppercase/lowercase characters")
        cfg_5075 = S3_LDAP_TST_CFG["test_5075"]
        temp_file = self.cm_ldap_cfg["temp_path"]
        new_passwd = cfg_5075["new_pwd"]
        self.log.info("Step 1: Retrieving existing openldap password")
        self.node_obj.copy_file_to_local(const.AUTHSERVER_FILE, temp_file)
        old_pwd = get_config(
            temp_file, key=self.cm_ldap_cfg["login_pwd_section"])
        self.log.info("Step 1: Retrieved existing openldap password")
        self.log.info("Step 2: Changing openldap password")
        ch_pwd_cmd = self.cm_ldap_cfg["ch_pwd_cmd"].format(
            const.AUTHSERVER_FILE, new_passwd)
        resp = self.execute_shell_cmd(
            ch_pwd_cmd,
            const.SCRIPT_PATH,
            self.cm_ldap_cfg["output_str"])
        self.log.info("Response is : %s", resp)
        assert_in(self.cm_ldap_cfg["output_msg"], resp, resp)
        self.log.info("Step 2: Changed openldap password successfully")
        self.log.info(
            "Step 3: Restarting %s service",
            self.slapd_service)
        resp = S3H_OBJ.restart_s3server_service(self.slapd_service)
        assert_true(resp[0], resp[1])
        time.sleep(self.cm_ldap_cfg["restart_serv_pause"])
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Restarted %s service",
            self.slapd_service)
        self.log.info(
            "Step 4: Checking if new password is updated or not")
        self.node_obj.copy_file_to_local(const.AUTHSERVER_FILE, temp_file)
        updated_pwd = get_config(
            temp_file, key=self.cm_ldap_cfg["login_pwd_section"])
        assert_not_equal(old_pwd, updated_pwd, self.cm_ldap_cfg["err_message"])
        self.log.info(
            "Step 4: New password is updated successfully")
        self.default_ldap_pw = False
        self.log.info(
            "ENDED: Test to verify and check if password allows special characters"
            " with uppercase/lowercase characters")

    @pytest.mark.s3_ops
    @pytest.mark.s3_openldap
    @pytest.mark.tags('TEST-8023')
    @CTFailOn(error_handler)
    def test_5076(self):
        """Test to verify & check if blank ldap password is accepted during passwd reset/change."""
        self.log.info(
            "STARTED: Test to verify and check if blank ldap password is "
            "accepted during password reset/change.")
        cfg_5076 = S3_LDAP_TST_CFG["test_5076"]
        new_passwd = cfg_5076["new_pwd"]
        self.log.info(
            "Step 1: Changing openldap password with blank password")
        ch_pwd_cmd = self.cm_ldap_cfg["ch_pwd_cmd"].format(
            const.AUTHSERVER_FILE, new_passwd)
        resp = self.execute_shell_cmd(
            ch_pwd_cmd,
            const.SCRIPT_PATH,
            cfg_5076["err_message"])
        assert_in(cfg_5076["err_message"], resp, resp)
        self.log.info(
            "Step 1: Changing openldap password with blank "
            "password failed with %s",
            cfg_5076["err_message"])
        self.log.info(
            "ENDED: Test to verify and check if blank ldap password is "
            "accepted during password reset/change.")
