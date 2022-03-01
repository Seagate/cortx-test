"""
Utility Class for target locking using DB
"""
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
# -*- coding: utf-8 -*-
import os
import json
from http import HTTPStatus
import requests
import logging
from core import runner
from commons import params
from commons import constants as common_cnst

LOGGER = logging.getLogger(__name__)


class LockingServer:
    """
    Locking Task for System managements.
    Its DB based locking mechanism
    """

    def __init__(self):
        self.db_username, self.db_password = runner.get_db_credential()
        self.host = params.REPORT_SRV
        self.db_collection = "systemdb/"
        self.headers = {
            'content-type': "application/json",
        }

    def lock_target(self, target_name, client, lock_type, convert_to_shared=False):
        """
           Take lock on given target
       """
        lock_acquired = False
        if lock_type == common_cnst.SHARED_LOCK:
            if convert_to_shared:
                payload = {
                    "query": {"is_setup_free": {"$eq": True},
                              "setupname": target_name,
                              "in_use_for_parallel": {"$eq": False}
                              }
                }
            else:
                payload = {
                    "query": {"is_setup_free": {"$eq": False},
                              "setupname": target_name,
                              "in_use_for_parallel": {"$eq": True}
                              }
                }
            payload.update(
                {"projection": {"setupname": True, "setup_in_useby": True,
                                "parallel_client_cnt": True}})

        else:
            payload = {
                "query": {"is_setup_free": {"$eq": True},
                          "setupname": target_name,
                          "setup_in_useby": ""
                          },
                "projection": {"setupname": True, "setup_in_useby": True}
            }
        payload.update(
            {"db_username": self.db_username,
             "db_password": self.db_password})
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
            if lock_type == common_cnst.SHARED_LOCK:
                if convert_to_shared:
                    payload = {
                        "filter": {"setupname": target_name},
                        "update": {"$set": {"is_setup_free": False, "setup_in_useby": client,
                                            "parallel_client_cnt": 1, "in_use_for_parallel": True}}
                    }
                else:
                    json_response = json.loads(response.text)
                    if len(json_response["result"]) > 0:
                        existing_clients = json_response["result"][0]["setup_in_useby"]
                        parallel_cnt = json_response["result"][0]["parallel_client_cnt"]
                        client_cnts = parallel_cnt + 1
                        clients = existing_clients + " " + client

                        payload = {
                            "filter": {"setupname": target_name},
                            "update": {"$set": {"is_setup_free": False, "setup_in_useby": clients,
                                                "parallel_client_cnt": client_cnts}}
                        }
            else:
                payload = {
                    "filter": {"setupname": target_name},
                    "update": {"$set": {"is_setup_free": False, "setup_in_useby": client}}
                }
            payload.update(
                {"db_username": self.db_username,
                 "db_password": self.db_password})
            try:
                response = requests.request("PATCH", self.host + self.db_collection + "update",
                                            headers=self.headers, data=json.dumps(payload))
                if response.status_code == HTTPStatus.OK:
                    lock_acquired = True
            except requests.exceptions.RequestException as fault:
                LOGGER.exception(str(fault))
                LOGGER.error("Failed to do patch request on db")

        return lock_acquired

    def is_target_locked(self, target_name, client, lock_type):
        """
            Confirm lock on given target
        """
        lock_confirmed = False
        if lock_type == common_cnst.SHARED_LOCK:
            payload = {
                "query": {"is_setup_free": {"$eq": False},
                          "setupname": target_name,
                          "in_use_for_parallel": {"$eq": True},
                          },
                "projection": {"setupname": True, "setup_in_useby": True,
                               "in_use_for_parallel": True,
                               "parallel_client_cnt": True}
            }
        else:
            payload = {
                "query": {"is_setup_free": {"$eq": False},
                          "setupname": target_name,
                          "setup_in_useby": client
                          },
                "projection": {"setupname": True, "setup_in_useby": True}
            }
        payload.update(
            {"db_username": self.db_username,
             "db_password": self.db_password})
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
            if lock_type == common_cnst.SHARED_LOCK:
                # Check if client entry is present in setup_in_useby
                # check if parallel_client_cnt > 0
                # If yes then lock confirmed to True
                json_response = json.loads(response.text)
                if len(json_response["result"]) > 0:
                    clients = json_response["result"][0]["setup_in_useby"]
                    parallel_cnt = json_response["result"][0]["parallel_client_cnt"]
                    if (client in clients) and (parallel_cnt > 0):
                        lock_confirmed = True
            else:
                lock_confirmed = True
        return lock_confirmed

    def find_free_target(self, target_list, lock_type):
        """
            Get free target from provided target list
        """
        available_target = ""
        for target_name in target_list:
            target_found = self.is_target_present_in_db(target_name)
            if target_found:
                if lock_type == common_cnst.SHARED_LOCK:
                    payload = {
                        "query": {"is_setup_free": {"$eq": False},
                                  "is_setup_healthy": {"$eq": True},
                                  "setupname": target_name,
                                  "in_use_for_parallel": {"$eq": True}}
                    }
                else:
                    payload = {
                        "query": {"is_setup_free": {"$eq": True},
                                  "is_setup_healthy": {"$eq": True},
                                  "setupname": target_name}
                    }
                payload.update(
                    {"projection": {"setupname": True, "setup_in_useby": True},
                     "db_username": self.db_username,
                     "db_password": self.db_password})
                try:
                    response = requests.request("GET", self.host + self.db_collection + "search",
                                                headers=self.headers, data=json.dumps(payload))
                    if response.status_code == HTTPStatus.OK:
                        LOGGER.info("available target found")
                        available_target = target_name
                        break
                except requests.exceptions.RequestException as fault:
                    LOGGER.exception(str(fault))
                    LOGGER.error("Failed to do get request on db")
            else:
                LOGGER.error("target {} is not present in db".format(target_name))

        return available_target

    def is_target_present_in_db(self, target_name):
        """
            Check if given target is already present in db or not
        """
        target_found = False
        payload = {
            "query": {"setupname": target_name},
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

    def unlock_target(self, target_name, client):
        """
            Release lock on given target
        """
        lock_released = False
        payload = {
            "query": {"is_setup_free": {"$eq": False},
                      "setupname": target_name,
                      },
            "projection": {"setupname": True, "setup_in_useby": True,
                           "in_use_for_parallel": True, "parallel_client_cnt": True},
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
            json_response = json.loads(response.text)
            if len(json_response["result"]) > 0:
                shared_lock = json_response["result"][0]["in_use_for_parallel"]
                if shared_lock:
                    parallel_cnt = json_response["result"][0]["parallel_client_cnt"]
                    if parallel_cnt == 1:
                        payload = {
                            "filter": {"setupname": target_name},
                            "update": {"$set": {"is_setup_free": True, "setup_in_useby": "",
                                                "in_use_for_parallel": False,
                                                "parallel_client_cnt": 0}}
                        }
                    else:
                        clients = json_response["result"][0]["setup_in_useby"]
                        new_clients = clients.replace(client, "")
                        new_clients = new_clients.strip()
                        new_parallel_cnt = parallel_cnt - 1
                        payload = {
                            "filter": {"setupname": target_name},
                            "update": {"$set": {"setup_in_useby": new_clients,
                                                "parallel_client_cnt": new_parallel_cnt}}
                        }
                else:
                    payload = {
                        "filter": {"setupname": target_name, "setup_in_useby": client},
                        "update": {"$set": {"is_setup_free": True, "setup_in_useby": ""}}
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
