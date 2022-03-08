#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""
Script can be used to insert / update setup in the DB
Update the json with the entries you want to make and run below command.
Sample command: python tools/setup_update/setup_entry.py --dbuser <username> --dbpassword <password>
--new_entry <True/ False>
"""
import os
import logging
import json
import argparse
import ast
from pymongo import MongoClient
from urllib.parse import quote_plus


parser = argparse.ArgumentParser(description='Update the setup entry')
parser.add_argument('--fpath',
                    default=os.path.join(os.path.dirname(__file__), "setup_entry.json"),
                    help='Path of the json entry file')
parser.add_argument('--dbuser',
                    help='Database user')
parser.add_argument('--dbpassword',
                    help='database password')
parser.add_argument('--new_entry',
                    default="True",
                    help='True for new entry , False for update')
args = parser.parse_args()

FPATH = args.fpath
DB_HOSTNAME = """cftic1.pun.seagate.com:27017,
cftic2.pun.seagate.com:27017,
apollojenkins.pun.seagate.com:27017/
?authSource=cft_test_results&replicaSet=rs0"""
DB_NAME = "cft_test_results"
SYS_INFO_COLLECTION = "r2_systems"
DBUSER = args.dbuser
DBPSWD = args.dbpassword


def insert_new_setup():
    new_entry_check = ast.literal_eval(args.new_entry.capitalize())
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
    entry_exist = collection_obj.find(setup_query).count()
    if new_entry_check and entry_exist:
        LOG.error("%s already exists", setup_query)
        print("Entry already exits")
    elif new_entry_check and not entry_exist:
        try:
            rdata = collection_obj.insert_one(data)
            print(f"Record entry {rdata.inserted_id} is inserted successfully")
        except Exception as err:
            print("An exception occurred ::", err)
        return None
    else:
        try:
            rdata = collection_obj.update_one(setup_query, {'$set': data})
            print(f"Record entry {rdata} is updated successfully")
            LOG.debug("Data is updated successfully")
        except Exception as err:
            print("An exception occurred ::", err)
        return None
    setup_details = collection_obj.find_one(setup_query)
    print(f'Modified or inserted setup details {setup_details} ')
    return setup_details


if __name__ == '__main__':
    insert_new_setup()
