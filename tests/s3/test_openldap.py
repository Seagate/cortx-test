# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""Account User Management Test Module."""

import time
import logging
from datetime import datetime

import paramiko
import pytest
from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils.config_utils import read_yaml, get_config
from commons.utils.system_utils import run_remote_cmd, remove_file
from commons.utils.assert_utils import assert_false, assert_true, assert_in, assert_equal, assert_not_equal
from libs.s3 import S3H_OBJ, CM_CFG, LDAP_PASSWD


LDAP_CFG = read_yaml("config/s3/test_openldap.yaml")[1]


class TestOpenLdap:
    """Open LDAP Test Suite."""

    CM_LDAP_CFG = LDAP_CFG["common_vars"]

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.openldap_path = cls.CM_LDAP_CFG["openldap_path"]
        cls.slapd_dir = cls.CM_LDAP_CFG["slapd_dir"]
        cls.slapd_service = cls.CM_LDAP_CFG["slapd_service"]
        cls.datestamp = datetime.today().strftime(
            cls.CM_LDAP_CFG["date_format"])
        cls.backup_path = cls.CM_LDAP_CFG["backup_path"]
        cls.default_ldap_pw = True
        cls.host = CM_CFG["nodes"][0]["host"]
        cls.username = CM_CFG["nodes"][0]["username"],
        cls.pwd = CM_CFG["nodes"][0]["password"],

    def remote_execution(self, hostname, username, password, cmd):
        """running remote cmd."""
        self.log.info("Remote Execution")
        return run_remote_cmd(
            cmd,
            hostname,
            username,
            password,
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
            self.CM_LDAP_CFG["ch_owner_err"].format(ch_owner_dir))

    def get_owner(self, dir_path, dir_name):
        """
        Function will retrieve the owner of specified directory.

        :param str dir_path: A parent directory path.
        :param str dir_name: Name of a directory whose owner to be retrieved.
        :return: An owner of a specified directory.
        :rtype: str
        """
        cmd = self.CM_LDAP_CFG["chk_owner_cmd"].format(dir_path)
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
            self.CM_LDAP_CFG["backup_dir_err"].format(
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
            self.CM_LDAP_CFG["cr_dir_err"].format(
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
                self.CM_LDAP_CFG["restore_dir_err"].format(ls_cmd[3:]))

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
        hosts.append(self.host)
        hosts.append(CM_CFG["nodes"][1]["host"])
        self.log.info("Creating a shell session on channel...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        for host in hosts:
            ssh.connect(
                host,
                username=self.username,
                password=self.pwd)
            channel = ssh.invoke_shell()
            self.log.info("Created a shell session on channel")
            while True:
                time.sleep(self.CM_LDAP_CFG["channel_time_pause"])
                if channel.recv_ready():
                    channel_data += channel.recv(
                        self.CM_LDAP_CFG["output_bytes"]).decode(
                        self.CM_LDAP_CFG["decode_format"])
                else:
                    continue
                if verify_statement in channel_data:
                    self.log.info("Command executed successfully")
                    break
                if channel_data.endswith(self.CM_LDAP_CFG["root_prmpt"]):
                    time.sleep(self.CM_LDAP_CFG["channel_time_pause"])
                    channel.send(
                        "".join([cd_cmd, self.CM_LDAP_CFG["press_enter"]]))
                elif channel_data.endswith(self.CM_LDAP_CFG["scr_dir_prmpt"]):
                    time.sleep(self.CM_LDAP_CFG["channel_time_pause"])
                    self.log.info(
                        "Executing command: %s", ch_pwd_cmd)
                    time.sleep(self.CM_LDAP_CFG["channel_time_pause"])
                    channel.send(
                        "".join([ch_pwd_cmd, self.CM_LDAP_CFG["press_enter"]]))
                elif channel_data.endswith(self.CM_LDAP_CFG["pwd_prompt_msg"]):
                    channel.send(
                        "".join([self.CM_LDAP_CFG["root_pwd"], self.CM_LDAP_CFG["press_enter"]]))
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
            self.CM_LDAP_CFG["mk_dir_cmd"].format(self.backup_path))
        self.log.info(
            "Created a backup directory %s",
            self.backup_path)
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
                self.slapd_dir) != self.CM_LDAP_CFG["ldap_owner"]:
            self.log.info(
                "Changing owner of openldap configuration directory to ldap...")
            ch_owner_cmd = self.CM_LDAP_CFG["ch_owner_cmd"].format(
                ldap_cfg_path)
            chk_owner_cmd = self.CM_LDAP_CFG["chk_owner_cmd"].format(
                self.openldap_path)
            self.chown_dir(
                ch_owner_cmd,
                self.CM_LDAP_CFG["ldap_owner"],
                chk_owner_cmd,
                self.slapd_dir)
            self.log.info(
                "Changed owner of openldap configuration directory to ldap")
        data_path = f"{self.CM_LDAP_CFG['ldap_data_path']}/{self.CM_LDAP_CFG['ldap_data_dir']}"
        if self.get_owner(
                self.CM_LDAP_CFG['ldap_data_path'],
                self.CM_LDAP_CFG['ldap_data_dir']) != self.CM_LDAP_CFG["ldap_owner"]:
            self.log.info(
                "Changing owner of openldap data directory to ldap...")
            ch_owner_cmd = self.CM_LDAP_CFG["ch_owner_cmd"].format(data_path)
            chk_owner_cmd = self.CM_LDAP_CFG["chk_owner_cmd"].format(
                self.CM_LDAP_CFG["ldap_data_path"])
            self.chown_dir(
                ch_owner_cmd,
                self.CM_LDAP_CFG["ldap_owner"],
                chk_owner_cmd,
                self.CM_LDAP_CFG['ldap_data_dir'])
            self.log.info(
                "Changed owner of openldap data directory to ldap")
        if not self.default_ldap_pw:
            self.log.info("Step 2: Restoring openldap password")
            default_pw = LDAP_PASSWD
            ch_pwd_cmd = self.CM_LDAP_CFG["ch_pwd_cmd"].format(
                const.AUTHSERVER_FILE, default_pw)
            resp = self.execute_shell_cmd(
                ch_pwd_cmd,
                const.SCRIPT_PATH,
                self.CM_LDAP_CFG["output_str"])
            self.log.info("Response is : %s", resp)
            self.log.info(
                "Restarting %s service",
                self.slapd_service)
            S3H_OBJ.restart_s3server_service(self.slapd_service)
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
            self.CM_LDAP_CFG["rm_dir_cmd"].format(self.backup_path))
        self.log.info("Deleted backup dir %s", self.backup_path)
        remove_file(self.CM_LDAP_CFG["temp_path"])
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_5066(self):
        """Test to verify & check backup of openldap config directory is done successfully."""
        self.log.info(
            "STARTED: Test to verify and check backup of openldap "
            "configuration directory is done successfully")
        cfg_5066 = LDAP_CFG["test_5066"]
        backup_cfg_file = self.CM_LDAP_CFG["cfg_backup_file"]
        slapd_err = cfg_5066["slapd_err"]
        self.log.info(
            "Step 1: Verifying if %s is present under %s",
            self.slapd_dir, self.openldap_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.CM_LDAP_CFG["ls_cmd"])
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
        slapcat_cmd = self.CM_LDAP_CFG["slapcat_cmd"].format(
            cfg_5066["db_no"], self.backup_path, backup_cfg_file)
        self.backup_dir(
            slapcat_cmd,
            backup_cfg_file,
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s directory successfully",
            self.slapd_dir)
        self.log.info(
            "ENDED: Test to verify and check backup of openldap "
            "configuration directory is done successfully")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_5067(self):
        """Test to verify and check backup of openldap Data Directories is done successfully."""
        self.log.info(
            "STARTED: Test to verify & check backup of "
            "openldap Data Directories is done successfully")
        cfg_5067 = LDAP_CFG["test_5067"]
        ldap_data_path = self.CM_LDAP_CFG["ldap_data_path"]
        ldap_data_dir = self.CM_LDAP_CFG["ldap_data_dir"]
        backup_data_file = self.CM_LDAP_CFG["data_backup_file"]
        ldap_data_dir_err = cfg_5067["ldap_data_dir_err"]
        self.log.info(
            "Step 1: Verifying if ldap data directory named as %s is present under %s",
            ldap_data_dir,
            ldap_data_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            cfg_5067["ls_ldap_data_dir_cmd"])
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
        slapcat_cmd = self.CM_LDAP_CFG["slapcat_cmd"].format(
            cfg_5067["db_no"], self.backup_path, backup_data_file)
        self.backup_dir(
            slapcat_cmd,
            backup_data_file,
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of ldap data directory successfully")
        self.log.info(
            "ENDED: Test to verify & check backup of openldap Data Directory is done successfully")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_5068(self):
        """Test to verify & check restore of openldap config directory is done successfully."""
        self.log.info(
            "STARTED: Test to verify and check restore of openldap configuration "
            "directory is done successfully")
        cfg_5068 = LDAP_CFG["test_5068"]
        slapd_err = self.CM_LDAP_CFG["slapd_err"]
        bkp_config_dir = f"{self.slapd_dir}.{self.datestamp}"
        self.log.info(
            "Step 1: Verifying if openldap configuration directory is present under %s",
            self.openldap_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.CM_LDAP_CFG["ls_cmd"])
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
            self.CM_LDAP_CFG["cfg_backup_file"])
        slapcat_cmd = self.CM_LDAP_CFG["slapcat_cmd"].format(
            cfg_5068["db_no"], self.backup_path, self.CM_LDAP_CFG["cfg_backup_file"])
        self.backup_dir(
            slapcat_cmd,
            self.CM_LDAP_CFG["cfg_backup_file"],
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s file ",
            self.CM_LDAP_CFG["cfg_backup_file"])
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
        backup_cmd = cfg_5068["backup_dir_cmd"].format(bkp_config_dir)
        self.backup_dir(
            backup_cmd,
            bkp_config_dir,
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 4: Taken a backup of openldap configuration directory successfully")
        self.log.info(
            "Step 5: Creating a new %s directory under %s",
            self.slapd_dir, self.openldap_path)
        self.create_dir(
            cfg_5068["cr_dir_cmd"],
            self.slapd_dir,
            self.CM_LDAP_CFG["ls_cmd"])
        self.log.info(
            "Step 5: Created a new %s directory under %s",
            self.slapd_dir, self.openldap_path)
        self.log.info("Step 6: Restoring openldap configuration directory")
        restore_cmd = cfg_5068["restore_cmd"].format(self.backup_path)
        self.restore_dir(
            restore_cmd,
            cfg_5068["ldap_config_files"],
            cfg_5068["ls_slapd_dir"])
        self.log.info(
            "Step 6: Restored openldap configuration directory successfully")
        self.log.info(
            "Step 7: Changing owner of ldap configuration directory to %s",
            self.CM_LDAP_CFG["ldap_owner"])
        ldap_cfg_path = f"{self.openldap_path}/{self.slapd_dir}"
        ch_owner_cmd = self.CM_LDAP_CFG["ch_owner_cmd"].format(ldap_cfg_path)
        chk_owner_cmd = self.CM_LDAP_CFG["chk_owner_cmd"].format(
            self.openldap_path)
        self.chown_dir(
            ch_owner_cmd,
            self.CM_LDAP_CFG["ldap_owner"],
            chk_owner_cmd,
            self.slapd_dir)
        self.log.info(
            "Step 7: Changed owner of ldap configuration directory to %s successfully",
            self.CM_LDAP_CFG["ldap_owner"])
        self.log.info(
            "ENDED: Test to verify and check restore of openldap "
            "configuration directory is done successfully")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
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
        cfg_5069 = LDAP_CFG["test_5069"]
        slapd_err = self.CM_LDAP_CFG["slapd_err"]
        bkp_config_dir = f"{self.slapd_dir}.{self.datestamp}"
        self.log.info(
            "Step 1: Verifying if openldap configuration directory is present under %s",
            self.openldap_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            self.CM_LDAP_CFG["ls_cmd"])
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
            self.CM_LDAP_CFG["cfg_backup_file"])
        slapcat_cmd = self.CM_LDAP_CFG["slapcat_cmd"].format(
            cfg_5069["db_no"], self.backup_path, self.CM_LDAP_CFG["cfg_backup_file"])
        self.backup_dir(
            slapcat_cmd,
            self.CM_LDAP_CFG["cfg_backup_file"],
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s file ",
            self.CM_LDAP_CFG["cfg_backup_file"])
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
        backup_cmd = cfg_5069["backup_dir_cmd"].format(bkp_config_dir)
        self.backup_dir(
            backup_cmd,
            bkp_config_dir,
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 4: Taken a backup of openldap configuration directory successfully")
        self.log.info(
            "Step 5: Checking ownership of backup configuration directory")
        dir_owner = self.get_owner(self.backup_path, bkp_config_dir)
        assert_equal(dir_owner, self.CM_LDAP_CFG["ldap_owner"], dir_owner)
        self.log.info(
            "Step 5: Checked owner of backup configuration directory is %s",
            self.CM_LDAP_CFG["ldap_owner"])
        self.log.info(
            "Step 6: Creating a new %s directory under %s",
            self.slapd_dir, self.openldap_path)
        self.create_dir(
            cfg_5069["cr_dir_cmd"],
            self.slapd_dir,
            self.CM_LDAP_CFG["ls_cmd"])
        self.log.info(
            "Step 6: Created a new %s directory under %s",
            self.slapd_dir, self.openldap_path)
        self.log.info("Step 7: Restoring openldap configuration directory")
        restore_cmd = cfg_5069["restore_cmd"].format(self.backup_path)
        self.restore_dir(
            restore_cmd,
            cfg_5069["ldap_config_files"],
            cfg_5069["ls_slapd_dir"])
        self.log.info(
            "Step 7: Restored openldap configuration directory successfully")
        self.log.info(
            "Step 8: Changing owner of ldap configuration directory to %s",
            self.CM_LDAP_CFG["ldap_owner"])
        ldap_cfg_path = f"{self.openldap_path}/{self.slapd_dir}"
        ch_owner_cmd = self.CM_LDAP_CFG["ch_owner_cmd"].format(ldap_cfg_path)
        chk_owner_cmd = self.CM_LDAP_CFG["chk_owner_cmd"].format(
            self.openldap_path)
        self.chown_dir(
            ch_owner_cmd,
            self.CM_LDAP_CFG["ldap_owner"],
            chk_owner_cmd,
            self.slapd_dir)
        self.log.info(
            "Step 8: Changed owner of ldap configuration directory to %s successfully",
            self.CM_LDAP_CFG["ldap_owner"])
        self.log.info(
            "ENDED: Test to verify and check if ownership and "
            "permissions of the configuration directory is changed "
            "to what it was previously before restore.")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_5070(self):
        """Test to verify and check restore of openldap data directories is done successfully."""
        self.log.info(
            "STARTED: Test to verify and check restore of "
            "openldap data directories is done successfully")
        cfg_5070 = LDAP_CFG["test_5070"]
        ldap_data_path = self.CM_LDAP_CFG["ldap_data_path"]
        ldap_data_dir = self.CM_LDAP_CFG["ldap_data_dir"]
        ldap_data_err = cfg_5070["ldap_data_err"]
        bkp_ldap_data_dir = f"{ldap_data_dir}{self.datestamp}"
        self.log.info(
            "Step 1: Verifying that ldap data directory is present under %s",
            ldap_data_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            cfg_5070["ls_ldap_data_cmd"])
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
            self.CM_LDAP_CFG["data_backup_file"])
        slapcat_cmd = self.CM_LDAP_CFG["slapcat_cmd"].format(
            cfg_5070["db_no"], self.backup_path, self.CM_LDAP_CFG["data_backup_file"])
        self.backup_dir(
            slapcat_cmd,
            self.CM_LDAP_CFG["data_backup_file"],
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s file ",
            self.CM_LDAP_CFG["data_backup_file"])
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
        backup_cmd = cfg_5070["backup_dir_cmd"].format(bkp_ldap_data_dir)
        self.backup_dir(
            backup_cmd,
            bkp_ldap_data_dir,
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 4: Taken a backup of ldap data directory successfully")
        self.log.info(
            "Step 5: Creating openldap data directory under %s",
            ldap_data_path)
        self.create_dir(
            cfg_5070["cr_dir_cmd"],
            ldap_data_dir,
            cfg_5070["ls_ldap_data_cmd"])
        self.log.info(
            "Step 5: Created openldap data directory under %s", ldap_data_path)
        self.log.info("Step 6: Restoring openldap data directory")
        restore_cmd = cfg_5070["restore_cmd"].format(self.backup_path)
        self.restore_dir(
            restore_cmd,
            cfg_5070["ldap_config_files"],
            cfg_5070["ls_slapd_dir"])
        self.log.info(
            "Step 6: Restored openldap data directory successfully")
        self.log.info(
            "Step 7: Changing owner of ldap configuration directory to %s",
            self.CM_LDAP_CFG["ldap_owner"])
        data_path = f"{ldap_data_path}/{ldap_data_dir}"
        ch_owner_cmd = self.CM_LDAP_CFG["ch_owner_cmd"].format(data_path)
        chk_owner_cmd = self.CM_LDAP_CFG["chk_owner_cmd"].format(
            ldap_data_path)
        self.chown_dir(
            ch_owner_cmd,
            self.CM_LDAP_CFG["ldap_owner"],
            chk_owner_cmd,
            ldap_data_dir)
        self.log.info(
            "Step 7: Changed owner of ldap configuration directory to %s successfully",
            self.CM_LDAP_CFG["ldap_owner"])
        self.log.info(
            "ENDED: Test to verify and check restore of "
            "openldap data directories is done successfully")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_5071(self):
        """
        Test to verify and check.

        Change if ownership and permissions of the data directory to what it was previously.
        """
        self.log.info(
            "STARTED: Test to verify and check change if ownership "
            "and permissions of the data directory to what it was previously")
        cfg_5071 = LDAP_CFG["test_5071"]
        ldap_data_path = self.CM_LDAP_CFG["ldap_data_path"]
        ldap_data_dir = self.CM_LDAP_CFG["ldap_data_dir"]
        ldap_data_err = cfg_5071["ldap_data_err"]
        bkp_ldap_data_dir = f"{ldap_data_dir}{self.datestamp}"
        self.log.info(
            "Step 1: Verifying that ldap data directory is present under %s",
            ldap_data_path)
        status, resp = self.remote_execution(
            self.host,
            self.username,
            self.pwd,
            cfg_5071["ls_ldap_data_cmd"])
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
            self.CM_LDAP_CFG["data_backup_file"])
        slapcat_cmd = self.CM_LDAP_CFG["slapcat_cmd"].format(
            cfg_5071["db_no"], self.backup_path, self.CM_LDAP_CFG["data_backup_file"])
        self.backup_dir(
            slapcat_cmd,
            self.CM_LDAP_CFG["data_backup_file"],
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 2: Taken a backup of %s file ",
            self.CM_LDAP_CFG["data_backup_file"])
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
        backup_cmd = cfg_5071["backup_dir_cmd"].format(bkp_ldap_data_dir)
        self.backup_dir(
            backup_cmd,
            bkp_ldap_data_dir,
            self.CM_LDAP_CFG["ls_backup_path"])
        self.log.info(
            "Step 4: Taken a backup of ldap data directory successfully")
        self.log.info("Step 5: Checking ownership of backup data directory")
        dir_owner = self.get_owner(self.backup_path, bkp_ldap_data_dir)
        assert_equal(dir_owner, self.CM_LDAP_CFG["ldap_owner"], dir_owner)
        self.log.info(
            "Step 5: Checked owner of backup configuration directory is %s",
            self.CM_LDAP_CFG["ldap_owner"])
        self.log.info(
            "Step 6: Creating openldap data directory under %s",
            ldap_data_path)
        self.create_dir(
            cfg_5071["cr_dir_cmd"],
            ldap_data_dir,
            cfg_5071["ls_ldap_data_cmd"])
        self.log.info(
            "Step 6: Created openldap data directory under %s", ldap_data_path)
        self.log.info("Step 7: Restoring openldap data directory")
        restore_cmd = cfg_5071["restore_cmd"].format(self.backup_path)
        self.restore_dir(
            restore_cmd,
            cfg_5071["ldap_config_files"],
            cfg_5071["ls_slapd_dir"])
        self.log.info(
            "Step 7: Restored openldap data directory successfully")
        self.log.info(
            "Step 8: Changing owner of ldap configuration directory to %s",
            self.CM_LDAP_CFG["ldap_owner"])
        data_path = f"{ldap_data_path}/{ldap_data_dir}"
        ch_owner_cmd = self.CM_LDAP_CFG["ch_owner_cmd"].format(data_path)
        chk_owner_cmd = self.CM_LDAP_CFG["chk_owner_cmd"].format(
            ldap_data_path)
        self.chown_dir(
            ch_owner_cmd,
            self.CM_LDAP_CFG["ldap_owner"],
            chk_owner_cmd,
            ldap_data_dir)
        self.log.info(
            "Step 8: Changed owner of ldap configuration directory to %s successfully",
            self.CM_LDAP_CFG["ldap_owner"])
        self.log.info(
            "ENDED: Test to verify and check change if ownership and "
            "permissions of the data directory to what it was previously")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_5073(self):
        """
        Test to verify and check.

        if password reset is done successfully using enc_ldap_passwd_in_cfg.sh script.
        """
        self.log.info(
            "STARTED: Test to verify and check if password reset is done successfully using "
            "enc_ldap_passwd_in_cfg.sh script.")
        cfg_5073 = LDAP_CFG["test_5073"]
        new_passwd = cfg_5073["new_pwd"]
        self.log.info("Step 1: Changing openldap password")
        ch_pwd_cmd = cfg_5073["ch_pwd_cmd"].format(
            const.AUTHSERVER_FILE, new_passwd)
        resp = self.execute_shell_cmd(
            ch_pwd_cmd,
            const.SCRIPT_PATH,
            cfg_5073["output_str"])
        assert_in(cfg_5073["output_msg"], resp, resp)
        self.log.info("Step 1: Changed openldap password successfully")
        self.log.info(
            "Step 2: Restarting %s service",
            self.slapd_service)
        S3H_OBJ.restart_s3server_service(self.slapd_service)
        time.sleep(self.CM_LDAP_CFG["restart_serv_pause"])
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Restarted %s service",
            self.slapd_service)
        self.log.info(
            "ENDED: Test to verify and check if password reset is done successfully using "
            "enc_ldap_passwd_in_cfg.sh script.")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_5074(self):
        """Test to verify & check if authserver properties file is updated post pwd change/reset."""
        self.log.info(
            "STARTED: Test to verify and check if authserver.properties"
            "file is updated post password change/reset")
        cfg_5074 = LDAP_CFG["test_5074"]
        temp_file = cfg_5074["temp_path"]
        new_passwd = cfg_5074["new_pwd"]
        self.log.info("Step 1: Retrieving existing openldap password")
        S3H_OBJ.copy_s3server_file(const.AUTHSERVER_FILE, temp_file)
        old_pwd = get_config(
            temp_file, key=cfg_5074["login_pwd_section"])
        self.log.info("Password : %s", old_pwd)
        self.log.info("Step 1: Retrieved existing openldap password")
        self.log.info("Step 2: Changing openldap password")
        ch_pwd_cmd = cfg_5074["ch_pwd_cmd"].format(
            const.AUTHSERVER_FILE, new_passwd)
        resp = self.execute_shell_cmd(
            ch_pwd_cmd,
            const.SCRIPT_PATH,
            cfg_5074["output_str"])
        self.log.info("Response is : %s", resp)
        assert_in(cfg_5074["output_msg"], resp, resp)
        self.log.info("Step 2: Changed openldap password successfully")
        self.log.info(
            "Step 3: Restarting %s service",
            self.slapd_service)
        S3H_OBJ.restart_s3server_service(self.slapd_service)
        time.sleep(self.CM_LDAP_CFG["restart_serv_pause"])
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Restarted %s service",
            self.slapd_service)
        self.log.info(
            "Step 4: Checking if new password is updated or not")
        S3H_OBJ.copy_s3server_file(const.AUTHSERVER_FILE, temp_file)
        updated_pwd = get_config(
            temp_file, key=cfg_5074["login_pwd_section"])
        self.log.info("Password : %s", updated_pwd)
        assert_not_equal(old_pwd, updated_pwd, cfg_5074["err_message"])
        self.log.info(
            "Step 4: New password is updated successfully")
        self.default_ldap_pw = False
        self.log.info(
            "ENDED: Test to verify and check if authserver.properties "
            "file is updated post password change/reset")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_5075(self):
        """
        Test to verify and check.

        if password allows special characters with uppercase/lowercase characters.
        """
        self.log.info(
            "STARTED: Test to verify and check if password allows special characters"
            "with uppercase/lowercase characters")
        cfg_5075 = LDAP_CFG["test_5075"]
        temp_file = cfg_5075["temp_path"]
        new_passwd = cfg_5075["new_pwd"]
        self.log.info("Step 1: Retrieving existing openldap password")
        S3H_OBJ.copy_s3server_file(const.AUTHSERVER_FILE, temp_file)
        old_pwd = get_config(
            temp_file, key=cfg_5075["login_pwd_section"])
        self.log.info("Step 1: Retrieved existing openldap password")
        self.log.info("Step 2: Changing openldap password")
        ch_pwd_cmd = cfg_5075["ch_pwd_cmd"].format(
            const.AUTHSERVER_FILE, new_passwd)
        resp = self.execute_shell_cmd(
            ch_pwd_cmd,
            const.SCRIPT_PATH,
            cfg_5075["output_str"])
        self.log.info("Response is : %s", resp)
        assert_in(cfg_5075["output_msg"], resp, resp)
        self.log.info("Step 2: Changed openldap password successfully")
        self.log.info(
            "Step 3: Restarting %s service",
            self.slapd_service)
        S3H_OBJ.restart_s3server_service(self.slapd_service)
        time.sleep(self.CM_LDAP_CFG["restart_serv_pause"])
        resp = S3H_OBJ.get_s3server_service_status(self.slapd_service)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Restarted %s service",
            self.slapd_service)
        self.log.info(
            "Step 4: Checking if new password is updated or not")
        S3H_OBJ.copy_s3server_file(const.AUTHSERVER_FILE, temp_file)
        updated_pwd = get_config(
            temp_file, key=cfg_5075["login_pwd_section"])
        assert_not_equal(old_pwd, updated_pwd, cfg_5075["err_message"])
        self.log.info(
            "Step 4: New password is updated successfully")
        self.default_ldap_pw = False
        self.log.info(
            "ENDED: Test to verify and check if password allows special characters"
            " with uppercase/lowercase characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_5076(self):
        """Test to verify & check if blank ldap password is accepted during passwd reset/change."""
        self.log.info(
            "STARTED: Test to verify and check if blank ldap password is "
            "accepted during password reset/change.")
        cfg_5076 = LDAP_CFG["test_5076"]
        new_passwd = cfg_5076["new_pwd"]
        self.log.info(
            "Step 1: Changing openldap password with blank password")
        ch_pwd_cmd = cfg_5076["ch_pwd_cmd"].format(
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
