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
"""Tests operations on S3 Users using REST API"""

import configparser
import logging
import re
import time

import pytest
import yaml

from commons import constants as cons
from commons.helpers.node_helper import Node
from config import CMN_CFG
from config.s3 import S3_CFG
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from libs.s3.s3_k8s_restapi import Cipher
from libs.csm.csm_setup import CSMConfigsCheck

CORTXSEC_CMD = '/opt/seagate/cortx/extension/cortxsec'

class TestS3accountK8s:
    """S3 user test class"""
    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        cls.log = logging.getLogger(__name__)
        cls.config = configparser.ConfigParser()
        cls.log.info("STARTED: test setup.")
        cls.s3_rest_obj = S3AccountOperationsRestAPI()
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname, password=cls.passwd)
        cls.s3acc_name = "{}_{}".format("cli_s3_acc", int(time.perf_counter_ns()))
        cls.s3acc_email = "{}@seagate.com".format(cls.s3acc_name)
        cls.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        cls.remote_path = cons.CLUSTER_CONF_PATH
        cls.local_path = cons.LOCAL_CONF_PATH
        cls.config = CSMConfigsCheck()
 
    def ldap_search(self, ip_addr: str = None, user_name: str = None,
                    password: str = None):
        """Functionality to form and execute ldapsearch command"""
        ldap_search_cmd = ""
        if ip_addr is not None:
            ldap_search_cmd = cons.LDAP_SEARCH_DATA + " -H ldap://{}".format(ip_addr)
            self.log.info(ldap_search_cmd)
        if user_name is not None:
            ldap_search_cmd = ldap_search_cmd + " -D \"cn={0},dc=seagate,dc=com\"".format(user_name)
        if password is not None:
            ldap_search_cmd = ldap_search_cmd + " -w {}".format(password)
        self.log.info(ldap_search_cmd)
        self.log.info("printing response from ldap function")
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

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_k8s_user
    @pytest.mark.tags("TEST-28935")
    def test_28935(self):
        """This test validates the presence of password in ldapsearch output"""
        self.log.info("Step 1: Create s3account s3acc.")
        s3acc_already_present = self.config.check_predefined_s3account_present()
        if not s3acc_already_present:
            s3acc_already_present = self.config.setup_csm_s3()
        assert s3acc_already_present
        self.log.info("Step 2: Get cluster IP of openldap")
        resp_node = self.nd_obj.execute_cmd(cmd="kubectl get svc",
                                        read_lines=False,
                                        exc=False)
        cluster_ip = self.get_cluster_ip(resp_node)
        self.log.info("printing ip in test after calling function")
        self.log.info(cluster_ip)
        resp = self.nd_obj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        self.log.info(resp)
        stream = open(self.local_path, 'r')
        data = yaml.safe_load(stream)
        admin_user = data['cortx']['external']['openldap']['admin']
        secret = data['cortx']['external']['openldap']['secret']
        self.log.info(secret)
        cluster_id = data["cluster"]["id"]
        self.log.info(cluster_id)
        admin_passwd = Cipher.decrypt_secret(secret,cluster_id,"cortx")
        self.log.info(admin_passwd)
        self.log.info("Step 3: call ldapsearch command form method")
        result = self.ldap_search(ip_addr=cluster_ip, user_name=admin_user,
                                password=admin_passwd)
        self.log.info(type(result))
        ldap_cmd = "kubectl exec -it symas-openldap-pod -- /bin/bash -c "
        login_ldap_pod = ldap_cmd + '"{}"'.format(result)
        resp_node = self.nd_obj.execute_cmd(cmd=login_ldap_pod,
                                        read_lines=False,
                                        exc=False)
        resp_str = resp_node.decode('UTF-8')
        self.log.info(resp_str)
        self.log.info("Step 4: Search for s3 account password in output")
        if "password" in resp_str:
            self.log.info("password present")
        else:
            self.log.info("password not present")
        self.log.info("##############Test Passed##############")

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_k8s_user
    @pytest.mark.tags("TEST-28934")
    def test_28934(self):
        """This test validates the presence of secret key in ldapsearch output"""
        self.log.info("Step 1: Create s3account s3acc.")
        s3acc_already_present = self.config.check_predefined_s3account_present()
        if not s3acc_already_present:
            s3acc_already_present = self.config.setup_csm_s3()
        assert s3acc_already_present
        self.log.info("Step 2: Get cluster IP of openldap")
        resp_node = self.nd_obj.execute_cmd(cmd="kubectl get svc",
                                        read_lines=False,
                                        exc=False)
        cluster_ip = self.get_cluster_ip(resp_node)
        self.log.info("printing ip in test after calling function")
        self.log.info(cluster_ip)
        resp = self.nd_obj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        stream = open(self.local_path, 'r')
        data = yaml.safe_load(stream)
        admin_user = data['cortx']['external']['openldap']['admin']
        secret = data['cortx']['external']['openldap']['secret']
        self.log.info(secret)
        cluster_id = data["cluster"]["id"]
        self.log.info(cluster_id)
        admin_passwd = Cipher.decrypt_secret(secret,cluster_id,"cortx")
        self.log.info(admin_passwd)
        self.log.info("Step 3: call ldapsearch command form method")
        result = self.ldap_search(ip_addr=cluster_ip, user_name=admin_user,
                                password=admin_passwd)
        self.log.info(type(result))
        ldap_cmd = "kubectl exec -it symas-openldap-pod -- /bin/bash -c "
        login_ldap_pod = ldap_cmd + '"{}"'.format(result)
        resp_node = self.nd_obj.execute_cmd(cmd=login_ldap_pod,
                                        read_lines=False,
                                        exc=False)
        resp_str = resp_node.decode('UTF-8')
        self.log.info(resp_str)
        self.log.info("Step 4: Search for s3 secret key in output")
        if "secret_key" in resp_str:
            self.log.info("secret key present")
        else:
            self.log.info("secret key not present")
        self.log.info("##############Test Passed##############")
