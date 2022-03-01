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
#
""" Report Server client to update test results to Mongo DB"""
import threading
import requests
from commons import errorcodes
from commons.exceptions import CTException
from commons.utils import web_utils

REPORT_SRV = "http://cftic2.pun.seagate.com:5000/"  # todo discover report server
REPORT_SRV_CREATE = REPORT_SRV + "reportsdb/create"
REPORT_SRV_UPDATE = REPORT_SRV + "reportsdb/update"


class SingletonMixin:
    """ Singleton helper """
    __instance_lock = threading.Lock()
    __instance = None

    @classmethod
    def get_instance(cls):
        """class method to get an derived class instance."""
        if not cls.__instance:
            raise CTException(errorcodes.CT_SINGLETON_NOT_INITIALIZED)
        return cls.__instance

    @classmethod
    def init_instance(cls, *args, **kwargs):
        """Init class instance"""
        if cls.__instance:
            return
        with cls.__instance_lock:
            if cls.__instance:
                return
            else:
                cls.__instance = cls(*args, **kwargs)

    @classmethod
    def reinit_instance(cls, *args, **kwargs):
        """Only use when created instance is lost"""
        with cls.__instance_lock:
            if not cls.__instance:
                raise CTException(errorcodes.CT_SINGLETON_NOT_INITIALIZED)
            else:
                cls.__instance = cls(*args, **kwargs)

    @classmethod
    def clear_instance(cls):
        """Clean up method"""
        with cls.__instance_lock:
            if not cls.__instance:
                raise CTException(errorcodes.CT_SINGLETON_NOT_INITIALIZED)
            else:
                cls.__instance = None


class ReportClient(SingletonMixin):
    """Singleton Report client."""

    def __init__(self, db_user=None, db_passwd=None):
        self.session = requests.session()
        self.db_user = 'datawrite' if not db_user else db_user
        self.db_pass = 'seagate@123' if not db_passwd else db_passwd

    def create_db_entry(self, **data_kwargs):
        """
        Create a DB entry corresponding to a passing test case in execution.
        Updates all required fields and set default in case missing.
        This function has to be used in pytest reporting hook.
        :param data_kwargs: All parameters needed to update in DB
        :return: Response status.

        {
            "OSVersion": "CentOS",
            "buildNo": "0003",
            "buildType": "Release",
            "clientHostname": "iu10-r18.pun.seagate.com",
            "executionType": "Automated",
            "healthCheckResult": "Fail",
            "isRegression": false,
            "issueIDs": ["EOS-000"],
            "issueType": "Dev",
            "logCollectionDone": true,
            "logPath": "DemoPath",
            "noOfNodes": 4,
            "nodesHostname": [
                "sm7-r18.pun.seagate.com",
                "sm8-r18.pun.seagate.com"
            ],
            "testPlanLabel": "S3",
            "testExecutionLabel": "CFT",
            "testExecutionID": "TEST-0000",
            "testExecutionTime": 0,
            "testID": "TEST-0000",
            "testIDLabels": [
                "Demo",
                "Labels"
            ],
            "testName": "Demo test",
            "testPlanID": "TEST-0000",
            "testResult": "Pass",
            "testStartTime": "2021-01-02T09:01:38+00:00",
            "testTags": [
                "Demo",
                "Tags"
            ],
            "testTeam": "CFT",
            "testType": "Pytest",
            "latest": true,
            "feature": "Test",
            "db_username": "",
            "db_password": ""
        }
       """
        payload = {"OSVersion": data_kwargs.get('os', "CentOS"),
                   "buildNo": data_kwargs.get('build'),
                   "buildType": data_kwargs.get('build_type', "stable"),
                   "clientHostname": data_kwargs.get('client_hostname', "autoclient"),
                   "executionType": data_kwargs.get('execution_type', "R2Automated"),
                   "healthCheckResult": data_kwargs.get('health_chk_res', "Pass"),
                   "logCollectionDone": data_kwargs.get('are_logs_collected', True),
                   "logPath": data_kwargs.get('log_path', "DemoPath"),
                   "noOfNodes": data_kwargs.get('nodes', 1),  # CMN_CFG defaults 1
                   "nodesHostname": data_kwargs.get('nodes_hostnames', []),  # CMN_CFG
                   "testPlanLabel": data_kwargs['testPlanLabel'],  # get from TP
                   "testExecutionLabel": data_kwargs['testExecutionLabel'],
                   "testExecutionID": data_kwargs['test_exec_id'],
                   "testExecutionTime": data_kwargs.get('test_exec_time', 0),
                   "testID": data_kwargs['test_id'],
                   "testIDLabels": data_kwargs['test_id_labels'],
                   "testName": data_kwargs['test_name'],
                   "testPlanID": data_kwargs['test_plan_id'],
                   "testResult": data_kwargs['test_result'],
                   "testStartTime": data_kwargs['start_time'],
                   "testTags": data_kwargs.get('tags', []),
                   # te component first element
                   "testTeam": data_kwargs.get('test_team', "Automation"),
                   "testType": data_kwargs.get('test_type', "Pytest"),  # use pytest default
                   "feature": data_kwargs['feature'],
                   "latest": data_kwargs['latest'],
                   "db_username": data_kwargs.get("db_username"),
                   "db_password": data_kwargs.get("db_password"),
                   "drID": data_kwargs['dr_id'],
                   "featureID": data_kwargs['feature_id'],
                   "platformType": data_kwargs['platform_type'],
                   "serverType": data_kwargs['server_type'],
                   "enclosureType": data_kwargs['enclosure_type'],
                   "failureString": data_kwargs.get('failure_string'),
                   }

        headers = {
            'Content-Type': 'application/json'
        }
        response = web_utils.http_post_request(REPORT_SRV_CREATE, payload, headers, verify=False)
        print(response.text.encode('utf8'))
        return response.status_code

    def update_db_entry(self, **data_kwargs):
        """
        Update reports db entry at the end of execution.
        It should be called to invalidate an existing failing entry.
        New entry will be created either by retest of failed test by
        test execution framework or manually by QA Engineer.
        :param data_kwargs:
        :return:
        """
        # build, tp, te , tid
        new_build_type = data_kwargs.get('update_build_type')
        payload = {"filter": {"buildType": data_kwargs.get('build_type', "stable")},
                   "update": {"$set": {"buildType": new_build_type,
                                       "OSVersion": data_kwargs.get('os')}},
                   "db_username": self.db_user,
                   "db_password": self.db_pass
                   }
        headers = {
            'Content-Type': 'application/json'
        }
        response = web_utils.http_patch_request(REPORT_SRV_UPDATE, payload, headers, verify=False)
        print(response.text.encode('utf8'))
        return response.status_code

    def lookup_and_invalidate(self, **data_kwargs):
        """
        Lookup and set latest field on old failing entries.
        :param data_kwargs:
        :return:
        """
        # build, tp, te , tid

        query_payload = {
            "query": {
                "buildNo": data_kwargs.get('build'),
                "testExecutionID": data_kwargs.get('test_exec_id'),
                "testID": data_kwargs.get('test_id'),
                "latest": True
            },
        }

        # Update latest key in entry as false
        patch_payload = {
            "filter": query_payload["query"],
            "update": {
                "$set": {"latest": False}
            }
        }

        payload = patch_payload.update({"db_username": self.db_user,
                                        "db_password": self.db_pass
                                        })
        headers = {'Content-Type': 'application/json'}
        response = web_utils.http_patch_request(REPORT_SRV_UPDATE, payload, headers, verify=False)
        print(response.text.encode('utf8'))
        return response.status_code


def init_report_client():
    ReportClient.init_instance(init_params=None)


def report_client(server):
    return ReportClient.get_instance()
