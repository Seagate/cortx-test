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
#
"""Serves as S3 client data manager. It will be able to remember object
versions and their meta data data(checksum and seeds) after interleaved executions.
This will help to recreate exactly same data and it can be uploaded to S3 server
 in the same or different bucket.
This class stores same state of object store as client knows about it.
It never talks to server to get any state from server.
It should be used for validation when data is stored with the cortx-test
framework. It acts as a hash cache storing the server state on client side.

 The structure of the client hash cache is as shown below

 { user=user1,
  email=user1@seagate.com,
  buckets=[ {bucket=test-1,
            s3prefix='',
            files=[{name=a.txt, chksum=abcd, seed=1, size=1024, },  {b.txt},]
            }
            ,

            {bucket=test-2,
            s3prefix='',
            files=[{name=a.txt, chksum=abcd, seed=1, size=1024, },  {b.txt},]
            }
         ]
 }

"""
import copy
import threading
import multiprocessing


class DataManager(object):
    """ Save objects meta data that went to storage for each test."""

    def __init__(self, user):
        self.buckets = list()
        self._change_tracker = dict()
        self.user = user
        self.state = dict()
        self.change_id = -1
        self.count = -1
        self.lock = threading.Lock()
        self.writelock = threading.Lock()

    def get_all_buckets_for_user(self, user):
        if user is None:
            raise ValueError('user is mandatory')
        if self._change_tracker != {}:
            if user not in self._change_tracker:
                self._change_tracker[user] = []
                return None
            if not self._change_tracker[user]:
                return None
            return self._change_tracker[user][len(self._change_tracker[user]) - 1]
        else:
            return None

    def get_files_within_bucket(self, user, bid=None, ver=None):
        if self._change_tracker != {} and bid is not None:
            if bid not in self._change_tracker:
                self._change_tracker[bid] = []
            return self._change_tracker[user][bid]
        return None

    def add_files_to_bucket(self, user, bucket, file_obj, checksum, size, ver=None):
        if self._change_tracker != {} and bid is not None:
            if bid not in self._change_tracker:
                self._change_tracker[bid] = []
            return self._change_tracker[user][bid]
        return None

    def persist_cache(self, ch, user):
        tch = copy.deepcopy(ch)
        if not user:
            raise ValueError('user is mandatory')
        if user not in self._change_tracker:
            self._change_tracker[user] = []
        self._change_tracker[user].append((tch,))

    def delete_file_from_bucket(self):
        pass

    def update_file_in_bucket(self):
        pass

    def get_stored_file_entry(self, uid, file_name):
        if self._change_tracker and uid is not None:
            if uid not in self._change_tracker:
                return
            entry = self._change_tracker[uid][len(self._change_tracker[uid]) - 1]
            for e in entry:
                if e['name'] == file_name:
                    return e
        return dict()

    def collect_test_run_client_state(self):
        """Combine cache for all test runners from a single target setup"""
        raise NotImplementedError('we might need this for implementing DI TP.')

    def get_versions_of_object(self, user):
        """Will be applicable in future."""
        raise NotImplementedError('Versioning not supported on Object Store.')
