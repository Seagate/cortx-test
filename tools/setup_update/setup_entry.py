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
"""
Script can be used to insert / update setup in the DB
"""
import os
import logging
from urllib.parse import quote_plus
import json
from pymongo import MongoClient

FPATH = os.path.join(os.path.dirname(__file__), "setup_entry.json")
DB_HOSTNAME = """cftic1.pun.seagate.com:27017,
cftic2.pun.seagate.com:27017,
apollojenkins.pun.seagate.com:27017/
?authSource=cft_test_results&replicaSet=rs0"""
DB_NAME = "cft_test_results"
SYS_INFO_COLLECTION = "r2_systems"
DBUSER=os.environ['DBUSER']
DBPSWD=os.environ['DBPSWD']

def insert_new_setup():
    LOG = logging.getLogger(__name__)
    with open(FPATH, 'rb') as json_file:
        data = json.loads(json_file.read())
    setupname = data['setupname']
    setup_query = {"setupname": setupname}
    LOG.debug("Database hostname: %s", DB_HOSTNAME)
    LOG.debug("Database name: %s", DB_NAME)
    LOG.debug("Collection name: %s", SYS_INFO_COLLECTION)
    mongodburi = "mongodb://{0}:{1}@{2}"
    uri = mongodburi.format(quote_plus(DBUSER), quote_plus(DBPSWD), DB_HOSTNAME)
    LOG.debug("URI : %s", uri)
    client = MongoClient(uri)
    setup_db = client[DB_NAME]
    collection_obj = setup_db[SYS_INFO_COLLECTION]
    LOG.debug("Collection obj for DB interaction %s", collection_obj)
    LOG.debug("Setup query : %s", setup_query)
    LOG.debug("Data to be updated : %s", data)
    import pdb
    pdb.set_trace()
    if not collection_obj.find(setup_query).count():
        rdata = collection_obj.update(setup_query, {'$set': data})
    if collection_obj.find(setup_query).count():
        LOG.error("Setup entry failed.")
    else:
        LOG.debug("Data is updated successfully")

if __name__ == '__main__':
    insert_new_setup()
