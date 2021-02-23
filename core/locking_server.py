"""
Utility Class for target locking using DB
"""
import os
import json
import requests
from http import HTTPStatus


class LockingServer:
    """
    Locking Task for System managements.
    Its DB based locking mechanism
    """
    def __init__(self):
        self.db_rd_username = os.environ['DB_RD_USERNAME']
        self.db_wr_username = os.environ['DB_WR_USERNAME']
        self.db_password = os.environ['DB_PASSWORD']
        self.host = "http://localhost:5000/"
        self.db_collection = "systemdb/"
        self.headers = {
            'content-type': "application/json",
        }

    def check_available_target(self, target_list):
        """
            Check which target is available for execution from given target list
        """
        available_target = ""
        for target_ip in target_list:
            target_found = self.is_target_present_in_db(target_ip)
            if target_found :
                payload = {
                    "query": {"isTargetFree": {"$in": ["Yes", "Y"]}, "priTargetIp": target_ip},
                    "projection": {"priTargetIp": True, "targetInUseBy": True},
                    "db_username": self.db_rd_username,
                    "db_password": self.db_password
                }
                response = requests.request("GET", self.host + self.db_collection + "search",
                                            headers=self.headers, data=json.dumps(payload))
                if response.status_code == HTTPStatus.OK:
                    print("available system found")
                    available_target = target_ip
                    break
            elif self.add_target_in_db(target_ip):
                available_target = target_ip
                break
        return available_target

    def is_target_present_in_db(self, target_ip):
        """
            Check if given target is already present in db or not
        """
        target_found = False
        payload = {
            "query": {"priTargetIp": target_ip},
            "projection": {"priTargetIp": True, "isTargetFree": True},
            "db_username": self.db_rd_username,
            "db_password": self.db_password
        }
        response = requests.request("GET", self.host + self.db_collection + "search",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK :
            target_found = True
        return target_found

    def add_target_in_db(self, target_ip):
        """
            Add given target in db
        """
        target_added = False
        payload = {
            "priTargetIp": target_ip,
            "isTargetFree": "Yes",
            "targetDetails": [],
            "targetInUseBy": "",
            "db_username": self.db_wr_username,
            "db_password": self.db_password
        }
        response = requests.request("POST", self.host + self.db_collection + "create",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK :
            target_added = True
        return target_added

    def take_target_lock(self, target_ip):
        """
            Take lock on given target
        """
        lock_acquired = False
        payload = {
            "query" : {"isTargetFree": {"$in" : ["Yes", "Y"]},
                       "priTargetIp": target_ip,
                       "targetInUseBy": ""
                       },
            "projection": {"priTargetIp": True, "targetInUseBy": True},
            "db_username": self.db_rd_username,
            "db_password": self.db_password
        }
        response = requests.request("GET", self.host + self.db_collection + "search",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK :
            payload = {
                "filter": {"priTargetIp": target_ip},
                "update": {"$set" : {"isTargetFree": "No", "targetInUseBy": target_ip}},
                "db_username": self.db_wr_username,
                "db_password": self.db_password
            }
            response = requests.request("PATCH", self.host + self.db_collection + "update",
                                        headers=self.headers, data=json.dumps(payload))
            if response.status_code == HTTPStatus.OK :
                lock_acquired = True
        return lock_acquired

    def release_target_lock(self, target_ip, target_use_by):
        """
            Release lock on given target
        """
        lock_released = False
        payload = {
            "filter": {"priTargetIp": target_ip, "targetInUseBy": target_use_by},
            "update": {"$set" : {"isTargetFree": "Yes", "targetInUseBy": ""}},
            "db_username": self.db_wr_username,
            "db_password": self.db_password
        }
        response = requests.request("PATCH", self.host + self.db_collection + "update",
                                    headers=self.headers, data=json.dumps(payload))
        if response.status_code == HTTPStatus.OK :
            lock_released = True
        return lock_released
