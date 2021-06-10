"""
Utility Class for VM management using DB
"""
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
# -*- coding: utf-8 -*-
import os
import json
from http import HTTPStatus
import requests
import logging
from core import runner
from commons import params


LOGGER = logging.getLogger(__name__)


class VmStateManagement:
    """
    Locking Task for System managements.
    Its DB based locking mechanism
    """

    def __init__(self, collection):
        self.db_username, self.db_password = runner.get_db_credential()
        self.host = params.REPORT_SRV
        self.db_collection = collection + "/"
        self.headers = {
            'content-type': "application/json",
        }

    def get_available_system(self, nodes):
        """
           Get available VMs
       """
        lock_acquired = False
        is_ok_response = False
        setup_info = dict()
        payload = {
            "query": {"is_setup_free": {"$eq": "yes"},
                      "nodes": nodes
                      }
        }

        payload.update({"projection": {"hostnames": True, "client": True, "setup_name": True}})

        payload.update(
            {"db_username": self.db_username,
             "db_password": self.db_password})
        try:
            response = requests.request("GET", self.host + self.db_collection + "search",
                                        headers=self.headers, data=json.dumps(payload))
            if response.status_code == HTTPStatus.OK:
                is_ok_response = True
        except requests.exceptions.RequestException as fault:
            LOGGER.exception(str(fault))
            LOGGER.error("Failed to do get request on db")

        if is_ok_response:
            json_response = json.loads(response.text)
            if len(json_response["result"]) > 0:
                setup_name = json_response["result"][0]["setupname"]
                hostnames = json_response["result"][0]["hostnames"]
                client = json_response["result"][0]["client"]
                payload = {
                        "filter": {"setupname": setup_name},
                        "update": {"$set": {"is_setup_free": "no", "setup_in_useby": "auto"}}
                    }
                payload.update(
                    {"db_username": self.db_username,
                     "db_password": self.db_password})
                try:
                    response = requests.request("PATCH", self.host + self.db_collection + "update",
                                                headers=self.headers, data=json.dumps(payload))
                    if response.status_code == HTTPStatus.OK:
                        lock_acquired = True
                        setup_info["setup_name"] = setup_name
                        setup_info["hostnames"] = hostnames
                        setup_info["client"] = client
                except requests.exceptions.RequestException as fault:
                    LOGGER.exception(str(fault))
                    LOGGER.error("Failed to do patch request on db")

        return lock_acquired, setup_info

    def add_systems(self, nodes, setupname, hostnames, client):
        """
            Confirm lock on given target
        """
        is_ok_response = False
        payload = {
            "query": {"setupname": setupname,
                      "nodes": nodes,
                      "hostnames": hostnames,
                      "client": client
                      }
        }

        payload.update(
            {"db_username": self.db_username,
             "db_password": self.db_password})

        try:
            response = requests.request("POST", self.host + self.db_collection + "create",
                                        headers=self.headers, data=json.dumps(payload))
            if response.status_code == HTTPStatus.OK:
                is_ok_response = True
        except requests.exceptions.RequestException as fault:
            LOGGER.exception(str(fault))
            LOGGER.error("Failed to do get request on db")
        return is_ok_response

    def is_system_present_in_db(self, setupname):
        """
            Check if given target is already present in db or not
        """
        target_found = False
        payload = {
            "query": {"setupname": setupname},
            "projection": {"setupname": True, "is_setup_free": True},
            "db_username": self.db_username,
            "db_password": self.db_password
        }
        try:
            response = requests.request("GET", self.host + self.db_collection + "search",
                                        headers=self.headers, data=json.dumps(payload))
            if response.status_code == HTTPStatus.OK:
                target_found = True
        except requests.exceptions.RequestException as fault:
            LOGGER.exception(str(fault))
            LOGGER.error("Failed to do get request on db")
        return target_found

    def unlock_system(self, setupname):
        """
            Release lock on given target
        """
        lock_released = False
        payload = {
            "query": {"is_setup_free": {"$eq": False},
                      "setupname": setupname,
                      },
            "projection": {"setupname": True},
            "db_username": self.db_username,
            "db_password": self.db_password
        }
        is_ok_response = False
        try:
            response = requests.request("GET", self.host + self.db_collection + "search",
                                        headers=self.headers, data=json.dumps(payload))
            if response.status_code == HTTPStatus.OK:
                is_ok_response = True
        except requests.exceptions.RequestException as fault:
            LOGGER.exception(str(fault))
            LOGGER.error("Failed to do get request on db")

        if is_ok_response:
            payload = {
                "filter": {"setupname": setupname},
                "update": {"$set": {"is_setup_free": "yes", "setup_in_useby": ""}}
            }

            payload.update(
                {"db_username": self.db_username,
                 "db_password": self.db_password})
            try:
                response = requests.request("PATCH", self.host + self.db_collection
                                            + "update", headers=self.headers,
                                            data=json.dumps(payload))
                if response.status_code == HTTPStatus.OK:
                    lock_released = True
            except requests.exceptions.RequestException as fault:
                LOGGER.exception(str(fault))
                LOGGER.error("Failed to do patch request on db")
            return lock_released
