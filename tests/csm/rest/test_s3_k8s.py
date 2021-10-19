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
#
"""Tests operations on S3 Users using REST API for K8s environment"""

import logging
import re

import pytest
import yaml

from commons import commands as comm
from commons import constants as cons
from commons.constants import Rest as const
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from config import CMN_CFG
from config import CSM_REST_CFG
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.s3.s3_k8s_restapi import Cipher

class TestS3accountK8s:
    """S3 user test class"""
    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        cls.log = logging.getLogger(__name__)
        cls.config = CSMConfigsCheck()
        cls.log.info("STARTED: test setup.")
        cls.s3user = RestS3user()
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname, password=cls.passwd)
        s3acc_already_present = cls.config.check_predefined_s3account_present()
        if not s3acc_already_present:
            s3acc_already_present = cls.config.setup_csm_s3()
        assert s3acc_already_present
        cls.remote_path = cons.CLUSTER_CONF_PATH
        cls.local_path = cons.LOCAL_CONF_PATH
 
    def ldap_search(self, ip_addr: str = None, user_name: str = None,
                    password: str = None):
        """Functionality to form and execute ldapsearch command"""
        ldap_search_cmd = ""
        if ip_addr is not None and user_name is not None and  password is not None:
           ldap_search_cmd = comm.LDAP_SEARCH_DATA.format(ip_addr, user_name, password)
        self.log.info("printing response from ldap function: %s", ldap_search_cmd)
        return ldap_search_cmd

    def get_cluster_ip(self, resp1):
        """Fetch openldap service ip"""
        self.log.info("extract cluster ip")
        data = str(resp1, 'UTF-8')
        data = data.split("\n")
        for line in data:
            if "openldap-svc" in line:
                line_found = line
                self.log.info(line_found)
                res = re.sub(' +', ' ', line_found)
                res = res.split()[2]
                self.log.info(res)
                return res

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-28934")
    def test_28934(self):
        """
        Test that all the secret keys are encrypted on openldap 
        and not available for direct use in IOs
        """
        self.log.info("Step 1: Create s3account s3acc.")
        response = self.s3user.create_s3_account(user_type="valid")
        response = response.json()
        if const.ACCESS_KEY not in response and const.SECRET_KEY not in response:
           self.log.debug("secret key and/or access key is not present")
           return False
        secret_key = response["secret_key"]
        self.log.info("Step 2: Get cluster IP of openldap")
        resp_node = self.nd_obj.execute_cmd(cmd=comm.K8S_SVC_CMD,
                                        read_lines=False,
                                        exc=False)
        cluster_ip = self.get_cluster_ip(resp_node)
        self.log.info("Openldap service ip is: %s",cluster_ip)
        resp = self.nd_obj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        assert_utils.assert_true(resp[0], resp)
        stream = open(self.local_path, 'r')
        data = yaml.safe_load(stream)
        admin_user = data['cortx']['external']['openldap']['admin']
        secret = data['cortx']['external']['openldap']['secret']
        cluster_id = data["cluster"]["id"]
        admin_passwd = Cipher.decrypt_secret(secret,cluster_id,"cortx")
        self.log.info("Step 3: call ldapsearch command form method")
        result = self.ldap_search(ip_addr=cluster_ip, user_name=admin_user,
                                password=admin_passwd)
        login_ldap_pod = comm.K8S_LDAP_CMD.format(result)
        resp_node = self.nd_obj.execute_cmd(cmd=login_ldap_pod,
                                        read_lines=False,
                                        exc=False)
        resp_str = resp_node.decode('UTF-8')
        self.log.info("Step 4: Search for s3 secret key in output")
        assert secret_key not in resp_str, "{} is not present in the openldap".format(secret_key)
        self.log.info("##############Test Completed##############")

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-28935")
    def test_28935(self):
        """
        Test S3 accounts passwords are encrypted on openldap 
        and available for direct use for creating buckets
        """
        self.log.info("Step 1: Fetch password for created s3 account.")
        s3_passwd = CSM_REST_CFG["s3account_user"]["password"]
        self.log.info("s3 password is: %s", s3_passwd)
        self.log.info("Step 2: Get cluster IP of openldap")
        resp_node = self.nd_obj.execute_cmd(cmd=comm.K8S_SVC_CMD,
                                        read_lines=False,
                                        exc=False)
        cluster_ip = self.get_cluster_ip(resp_node)
        self.log.info("Openldap service ip is: %s",cluster_ip)
        resp = self.nd_obj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        stream = open(self.local_path, 'r')
        data = yaml.safe_load(stream)
        admin_user = data['cortx']['external']['openldap']['admin']
        secret = data['cortx']['external']['openldap']['secret']
        cluster_id = data["cluster"]["id"]
        admin_passwd = Cipher.decrypt_secret(secret,cluster_id,"cortx")
        self.log.info("Step 3: Run ldapsearch command")
        result = self.ldap_search(ip_addr=cluster_ip, user_name=admin_user,
                                password=admin_passwd)
        login_ldap_pod = comm.K8S_LDAP_CMD.format(result)
        resp_node = self.nd_obj.execute_cmd(cmd=login_ldap_pod,
                                        read_lines=False,
                                        exc=False)
        resp_str = resp_node.decode('UTF-8')
        self.log.info("Step 4: Search for s3 account password in output")
        assert s3_passwd not in resp_str, "{} is not present in the openldap".format(s3_passwd)
        self.log.info("##############Test Completed##############")
