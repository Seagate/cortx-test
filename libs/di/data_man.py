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
"""Serves as S3 client data manager. It will be able to remember object
versions and their meta data data(checksum and seeds) after interleaved executions.
This will help to recreate exactly same data and it can be uploaded to S3 server
 in the same or different bucket.
This class stores same state of object store as client knows about it.
It never talks to server to get any state from server.
It should be used for validation when data is stored with the cortx-test
framework. It acts as a hash cache storing the server state on client side.

 The structure of the client hash cache is as shown below
{
 user1={ user=user1,
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
}
"""
import os
import logging
import threading
import random
import multiprocessing
from commons import params
from commons.utils import system_utils
from commons.utils import config_utils
from commons.exceptions import CortxTestException

# Container level
C_LEVEL_TOP = 1
C_LEVEL_USER = 2
C_LEVEL_BUCKET = 3

LOGGER = logging.getLogger(__name__)


class DataManager(object):
    """ Save objects meta data that went to storage for each test."""

    def __init__(self):
        self.buckets = list()
        self.change_tracker = dict()
        self.state = dict()
        self.rlock = threading.Lock()
        self.wlock = threading.Lock()
        self.plock = multiprocessing.Lock()

    def prepare_file_data(self, user):
        """Read data before saving."""
        p_home = params.META_DATA_HOME
        if not os.path.exists(p_home):
            try:
                system_utils.mkdirs(p_home)
            except (OSError, Exception) as fault:
                LOGGER.exception(str(fault), exc_info=fault.__traceback__)
                raise

        fpath = os.path.join(p_home, user + params.USER_META_JSON)

        if not os.path.exists(fpath):
            fpath = config_utils.create_content_json(fpath, {}, ensure_ascii=True)
            LOGGER.info(f'Created metadata file for user {user}')
        return fpath

    def store_file_data(self, data, user):
        """Store data in user meta json file.
        The data needs to comply with the json structure.
        """
        p_home = params.META_DATA_HOME
        fpath = os.path.join(p_home, user + params.USER_META_JSON)
        if not os.path.exists(fpath):
            raise CortxTestException('It is expected that the json path should be created by now')
        config_utils.create_content_json(fpath, data, ensure_ascii=True)

    def get_all_buckets_data_for_user(self, user):
        if user is None:
            raise ValueError('user is mandatory')

        fpath = self.prepare_file_data(user)
        # improve with ijson lib
        data = config_utils.read_content_json(fpath=fpath)
        if data:
            if user != data['name']:
                return None
            if not data['buckets']:
                return None
            return data['buckets']
        else:
            return None

    def get_files_within_bucket(self, bkt_container, bucket):
        if bucket is not None and bkt_container:
            if not bkt_container['files']:
                return None
            return bkt_container['files']
        return None

    def get_file_within_bucket(self, name, bkt_container, bucket):
        """Find file within a bucket and return None if not.
        Returns the same dict object within bucket container.
        """
        if bucket is not None and bkt_container:
            for _file_dict in bkt_container['files']:
                if _file_dict['name'] == name:
                    return _file_dict
        return None

    def get_container(self, level=C_LEVEL_BUCKET, **kwargs):
        """Create bucket level container to store bucket's data.
            bucket container has name=<>, s3prefix='', files
            user container has name=<>, email='', buckets
        """
        container = None
        if level == C_LEVEL_BUCKET:
            container = dict(name='', s3prefix='', files=list())
        elif level == C_LEVEL_USER:
            container = dict(name='', email='', buckets=list())
        elif level == C_LEVEL_TOP:
            container = dict()
        return container

    def _check_bucket_exists_in_buckets(self, bucket):
        """Protected API."""
        return True if bucket in self.buckets else False

    def _get_bucket_container_from_buckets(self, data, bucket, user):
        """Protected get bucket container API."""
        if user is None:
            raise ValueError('user is mandatory')
        if data:
            if user != data['name'] or not data['buckets']:
                container = self.get_container(level=C_LEVEL_BUCKET)
                container['name'] = bucket
                return container, False
            for bkt in data['buckets']:
                if bkt['name'] == bucket:
                    return bkt, True
        # means create a container for caller
        container = self.get_container(level=C_LEVEL_BUCKET)
        container['name'] = bucket
        return container, False  # anyway return an empty container

    def add_file_to_bucket(self, user, bucket, file_dict):
        """The updates within process will be in-memory and then persisted to json."""
        file_obj, checksum = file_dict['name'], file_dict['checksum']
        size, seed, mtime = file_dict['size'], file_dict['seed'], file_dict['mtime']
        data = dict()
        if bucket is not None:
            with self.wlock:
                fpath = self.prepare_file_data(user)
                data = config_utils.read_content_json(fpath=fpath)
                if not data or user != data['name']:
                    data = self.get_container(level=C_LEVEL_USER)
                    data['name'] = user
                bkt_container, flag = self._get_bucket_container_from_buckets(data, bucket, user)

                # usage files = self.get_files_within_bucket(bkt_container, user, bucket)
                fdict = self.get_file_within_bucket(file_obj, bkt_container, bucket)
                if not fdict:
                    # format of fdict is name=a.txt, chksum=abcd, seed=1, size=1024
                    fdict = dict(name=file_obj, checksum=checksum,
                                 sz=size, seed=seed, mtime=mtime)
                    bkt_container['files'].append(fdict)
                else:
                    fdict['checksum'] = checksum
                    fdict['sz'] = size
                    fdict['seed'] = seed
                    fdict['mtime'] = mtime

                if not flag:
                    data['buckets'].append(bkt_container)

                self.store_file_data(data, user)

    def delete_file_from_bucket(self):
        raise NotImplementedError('coming soon')

    def update_file_in_bucket(self):
        raise NotImplementedError('Currently add file takes care of it')

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


def dummy_test(change_manager, user, keys, file_dicts, nbuckets):
    """Test function to test this lib. Refer main of this file."""
    print(f'starting thread {threading.current_thread().getName()}')
    buckets = [user + '-bucket' + str(i) for i in range(nbuckets)]
    for bucket in buckets:
        try:
            change_manager.add_file_to_bucket(user, bucket, file_dicts)
        except (OSError, Exception) as ex:
            LOGGER.error(f'exception occurred %s', str(ex))


if __name__ == '__main__':
    LOGGER.info('Starting tests')
    jobs = []
    nbuckets = 4
    users = {"user1": ["AKIAvVRBu_qhRc2eOpMJwXOBjQ", "cT1tEIKo8SztEBpqHF5OroZkqda7kpph7DFQfZAz"],
             "user2": ["AKIAwxH4rqnwRqmXoX5HzyV8xA", "C5dBsRcL73wLyLEZr858nymh2h70abFvxINNSkRa"],
             "user3": ["AKIAql9gSmpcQnGyuHbiziTzng", "Ow6mYLCji2nBMCrMZDzG7/u2tu9WX0FjFI0ihOlG"],
             "user4": ["AKIA3iswZrw0R7mKtHJZizImKg", "TcvKJRfJnYS8H4f53B2g0urn/8+7uFG44vStPiwt"],
             "user5": ["AKIAZxC27C5kSRKomFywnCUE_A", "OLkz+6+eyV1IsXA2HBx6wtmRdihW0o/wktoCLCZf"],
             "user6": ["AKIA1s420Uw3RnWuRH_jU5YL9g", "JUq17VoBHInxd2Oftec592v/nVuNXlT185KsPc/N"],
             "user7": ["AKIAvzZoU96eQPucwPCYvD7kWw", "D7A+mEI/hu+0EAe02dZYbPZFD9BcmBPvdB5yaRRy"],
             "user8": ["AKIAdLhZ3gGSSCW3Ul1ECrjq2g", "OKGEDDWS4D+ohrOf0w8nYcgCXGZ0GE2WTVL6zAOC"],
             "user9": ["AKIA5Hx6gvLNTCuOAc7k6MYQ0w", "+xx/Y6IJWDQEGLzclUIwNVeSa3DfX09jGbbhi+M+"],
             "user10": ["AKIARmsEWm0NTvi2NJ5HD4sIzw", "TlIjEvDS2Q4LoEXbESqhyJ/CdC531f5Za4Bbwcmy"]
             }

    objects = [{'name': 'a.txt', 'checksum': 'abcd', 'seed': 1, 'size': 1024, 'mtime': "1"},
               {'name': 'b.txt', 'checksum': 'efgh', 'seed': 11, 'size': 1024, 'mtime': "1"},
               {'name': 'c.txt', 'checksum': 'ijkl', 'seed': 111, 'size': 1024, 'mtime': "1"},
               {'name': 'd.txt', 'checksum': 'mnop', 'seed': 1111, 'size': 1024, 'mtime': "1"},
               {'name': 'a.txt', 'checksum': 'mabcd', 'seed': 1, 'size': 1024, 'mtime': "1"},
               {'name': 'b.txt', 'checksum': 'mefgh', 'seed': 11, 'size': 1024, 'mtime': "1"},
               {'name': 'c.txt', 'checksum': 'mijkl', 'seed': 111, 'size': 1024, 'mtime': "1"},
               {'name': 'd.txt', 'checksum': 'mmnop', 'seed': 1111, 'size': 1024, 'mtime': "1"}]

    change_manager = DataManager()
    i = 0
    while i < 2:
        for user, keys in users.items():
            p = threading.Thread(target=dummy_test,
                                 args=(change_manager, user, keys,
                                       objects[random.randint(0, 7)], nbuckets))
            jobs.append(p)
        i += 1
    for p in jobs:
        p.start()
    for p in jobs:
        p.join()

    LOGGER.info('Upload Done for all users')
