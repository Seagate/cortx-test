"""
Utility Class for target locking using DB
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
from core import runner

LOGGER = logging.getLogger(__name__)


class LockingServer:
    """
    Locking Task for System managements.
    Its DB based locking mechanism
    """

    def __init__(self):
        self.db_username, self.db_password = runner.get_db_credential()
        self.host = "http://cftic2.pun.seagate.com:5000/"
        self.db_collection = "systemdb/"
        self.headers = {
            'content-type':"application/json",
        }

    def check_available_shared_target(self, target_list):
        """
            Check for shared target first, if its not available then check for free target.
        """
        available_target = ""
        for target_name in target_list:
            target_found = self.is_target_present_in_db(target_name)
            if target_found:
                payload = {
                    "query":{"is_setup_free":{"$eq":False}, "setupname":target_name,
                             "in_use_for_parallel":{"$eq":True}},
                    "projection":{"setupname":True, "setup_in_useby":True},
                    "db_username":self.db_username,
                    "db_password":self.db_password
                }
                response = requests.request("GET", self.host + self.db_collection + "search",
                                            headers=self.headers, data=json.dumps(payload))
                if response.status_code == HTTPStatus.OK:
                    LOGGER.info("available system found")
                    available_target = target_name
                    break
            else:
                LOGGER.info("target {} is not present in db".format(target_name))

        return available_target

    def check_available_target(self, target_list):
        """
            Check which target is available for execution from given target list
        """
        available_target = ""
        for target_name in target_list:
            target_found = self.is_target_present_in_db(target_name)
            if target_found:
                payload = {
                    "query":{"is_setup_free":{"$eq":True}, "setupname":target_name},
                    "projection":{"setupname":True, "setup_in_useby":True},
                    "db_username":self.db_username,
                    "db_password":self.db_password
                }
                response = requests.request("GET", self.host + self.db_collection + "search",
                                            headers=self.headers, data=json.dumps(payload))
                if response.status_code == HTTPStatus.OK:
                    LOGGER.info("available system found")
                    available_target = target_name
                    break
            else:
                LOGGER.info("target {} is not present in db".format(target_name))

        return available_target

    def is_target_present_in_db(self, target_name):
        """
            Check if given target is already present in db or not
        """
        target_found = False
        payload = {
            "query":{"setupname":target_name},
            "projection":{"setupname":True, "is_setup_free":True},
            "db_username":self.db_username,
            "db_password":self.db_password
        }
        response = requests.request("GET", self.host + self.db_collection + "search",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK:
            target_found = True
        return target_found

    def confirm_shared_target_lock(self, target_name, client):
        """
            Confirm lock on given target
        """
        lock_confirmed = False
        payload = {
            "query":{"is_setup_free":{"$eq":False},
                     "setupname":target_name,
                     "in_use_for_parallel":{"$eq":True},
                     },
            "projection":{"setupname":True, "setup_in_useby":True, "in_use_for_parallel":True,
                          "parallel_client_cnt":True},
            "db_username":self.db_username,
            "db_password":self.db_password
        }
        response = requests.request("GET", self.host + self.db_collection + "search",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK:
            # Check if client entry is present in setup_in_useby
            # check if parallel_client_cnt > 0
            # If yes then lock confirmed to True
            json_response = json.loads(response.text)
            if len(json_response["result"]) > 0:
                clients = json_response["result"][0]["setup_in_useby"]
                parallel_cnt = json_response["result"][0]["parallel_client_cnt"]
                if (client in clients) and (parallel_cnt > 0):
                    lock_confirmed = True
        return lock_confirmed

    def confirm_target_lock(self, target_name, client):
        """
            Confirm lock on given target
        """
        lock_confirmed = False
        payload = {
            "query":{"is_setup_free":{"$eq":False},
                     "setupname":target_name,
                     "setup_in_useby":client
                     },
            "projection":{"setupname":True, "setup_in_useby":True},
            "db_username":self.db_username,
            "db_password":self.db_password
        }
        response = requests.request("GET", self.host + self.db_collection + "search",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK:
            lock_confirmed = True
        return lock_confirmed

    def take_new_shared_target_lock(self, target_name, client):
        """
            Take lock on given target
        """
        lock_acquired = False
        payload = {
            "query":{"is_setup_free":{"$eq":True},
                     "setupname":target_name,
                     "in_use_for_parallel":{"$eq":False}
                     },
            "projection":{"setupname":True, "setup_in_useby":True, "parallel_client_cnt":True},
            "db_username":self.db_username,
            "db_password":self.db_password
        }
        response = requests.request("GET", self.host + self.db_collection + "search",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK:
            payload = {
                "filter":{"setupname":target_name},
                "update":{"$set":{"is_setup_free":False, "setup_in_useby":client,
                                  "parallel_client_cnt":1, "in_use_for_parallel":True}},
                "db_username":self.db_username,
                "db_password":self.db_password
            }
            response = requests.request("PATCH", self.host + self.db_collection + "update",
                                        headers=self.headers, data=json.dumps(payload))
            if response.status_code == HTTPStatus.OK:
                lock_acquired = True
        return lock_acquired

    def take_shared_target_lock(self, target_name, client):
        """
            Take lock on given target
        """
        lock_acquired = False
        payload = {
            "query":{"is_setup_free":{"$eq":False},
                     "setupname":target_name,
                     "in_use_for_parallel":{"$eq":True}
                     },
            "projection":{"setupname":True, "setup_in_useby":True, "parallel_client_cnt":True},
            "db_username":self.db_username,
            "db_password":self.db_password
        }
        response = requests.request("GET", self.host + self.db_collection + "search",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK:
            # get setup_in_useby and parallel_client_cnt
            # increase parallel_client_cnt by 1
            # append client entry into setup_in_useby
            json_response = json.loads(response.text)
            if len(json_response["result"]) > 0:
                existing_clients = json_response["result"][0]["setup_in_useby"]
                parallel_cnt = json_response["result"][0]["parallel_client_cnt"]
                client_cnts = parallel_cnt + 1
                clients = existing_clients + " " + client

                payload = {
                    "filter":{"setupname":target_name},
                    "update":{"$set":{"is_setup_free":False, "setup_in_useby":clients,
                                      "parallel_client_cnt":client_cnts}},
                    "db_username":self.db_username,
                    "db_password":self.db_password
                }
                response = requests.request("PATCH", self.host + self.db_collection + "update",
                                            headers=self.headers, data=json.dumps(payload))
                if response.status_code == HTTPStatus.OK:
                    lock_acquired = True
        return lock_acquired

    def take_target_lock(self, target_name, client):
        """
            Take lock on given target
        """
        lock_acquired = False
        payload = {
            "query":{"is_setup_free":{"$eq":True},
                     "setupname":target_name,
                     "setup_in_useby":""
                     },
            "projection":{"setupname":True, "setup_in_useby":True},
            "db_username":self.db_username,
            "db_password":self.db_password
        }
        response = requests.request("GET", self.host + self.db_collection + "search",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK:
            payload = {
                "filter":{"setupname":target_name},
                "update":{"$set":{"is_setup_free":False, "setup_in_useby":client}},
                "db_username":self.db_username,
                "db_password":self.db_password
            }
            response = requests.request("PATCH", self.host + self.db_collection + "update",
                                        headers=self.headers, data=json.dumps(payload))
            if response.status_code == HTTPStatus.OK:
                lock_acquired = True
        return lock_acquired

    def release_target_lock(self, target_name, client):
        """
            Release lock on given target
        """
        lock_released = False
        payload = {
            "query":{"is_setup_free":{"$eq":False},
                     "setupname":target_name,
                     },
            "projection":{"setupname":True, "setup_in_useby":True,
                          "in_use_for_parallel":True, "parallel_client_cnt":True},
            "db_username":self.db_username,
            "db_password":self.db_password
        }
        response = requests.request("GET", self.host + self.db_collection + "search",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            if len(json_response["result"]) > 0:
                shared_lock = json_response["result"][0]["in_use_for_parallel"]
                if shared_lock:
                    parallel_cnt = json_response["result"][0]["parallel_client_cnt"]
                    if parallel_cnt == 1:
                        payload = {
                            "filter":{"setupname":target_name},
                            "update":{"$set":{"is_setup_free":True, "setup_in_useby":"",
                                              "in_use_for_parallel":False,
                                              "parallel_client_cnt":0}},
                            "db_username":self.db_username,
                            "db_password":self.db_password
                        }
                        response = requests.request("PATCH",
                                                    self.host + self.db_collection + "update",
                                                    headers=self.headers, data=json.dumps(payload))
                        if response.status_code == HTTPStatus.OK:
                            lock_released = True
                    else:
                        clients = json_response["result"][0]["setup_in_useby"]
                        new_clients = clients.replace(client, "")
                        new_clients = new_clients.strip()
                        new_parallel_cnt = parallel_cnt - 1
                        payload = {
                            "filter":{"setupname":target_name},
                            "update":{"$set":{"setup_in_useby":new_clients,
                                              "parallel_client_cnt":new_parallel_cnt}},
                            "db_username":self.db_username,
                            "db_password":self.db_password
                        }
                        response = requests.request("PATCH",
                                                    self.host + self.db_collection + "update",
                                                    headers=self.headers, data=json.dumps(payload))
                        if response.status_code == HTTPStatus.OK:
                            lock_released = True
                else:
                    payload = {
                        "filter":{"setupname":target_name, "setup_in_useby":client},
                        "update":{"$set":{"is_setup_free":True, "setup_in_useby":""}},
                        "db_username":self.db_username,
                        "db_password":self.db_password
                    }
                    response = requests.request("PATCH", self.host + self.db_collection + "update",
                                                headers=self.headers, data=json.dumps(payload))
                    if response.status_code == HTTPStatus.OK:
                        lock_released = True
            return lock_released
