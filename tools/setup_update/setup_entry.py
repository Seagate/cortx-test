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
Script can be used to insert new setup in the DB
"""
import os
import logging
from urllib.parse import quote_plus
import yaml
import json

from pymongo import MongoClient
from commons import pswdmanager
from commons.params import DB_HOSTNAME, DB_NAME, SYS_INFO_COLLECTION

LOG = logging.getLogger(__name__)
fpath = "setup_entry.json"
setupname="unique"
setup_query ={"setupname":setupname}
with open(fpath, 'rb') as json_file:
    data = json.loads(json_file.read())
LOG.debug("Database hostname: %s", DB_HOSTNAME)
LOG.debug("Database name: %s", DB_NAME)
LOG.debug("Collection name: %s", SYS_INFO_COLLECTION)
db_creds = pswdmanager.get_secrets(secret_ids=['DBUSER', 'DBPSWD'])
mongodburi = "mongodb://{0}:{1}@{2}"
uri = mongodburi.format(quote_plus(db_creds['DBUSER']), quote_plus(db_creds['DBPSWD']), DB_HOSTNAME)
LOG.debug("URI : %s", uri)
client = MongoClient(uri)
setup_db = client[DB_NAME]
collection_obj = setup_db[SYS_INFO_COLLECTION]
LOG.debug("Collection obj for DB interaction %s", collection_obj)
LOG.debug("Setup query : %s", setup_query)
LOG.debug("Data to be updated : %s", data)
rdata = collection_obj.insert_one(setup_query, data)
LOG.debug("Data is updated successfully")