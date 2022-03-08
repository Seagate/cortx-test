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
A MongoDb instance can have multiple databases in it.
Each database can have multiple collections(tables) in it.
Each collection can have multiple documents(row) in it.
"""
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import configparser
from urllib.parse import quote_plus



config = configparser.ConfigParser()
config.read('config.ini')
hostname = config["MONGODB_URI"]["hostname"]
db_username = config["MONGODB_URI"]["db_username"]
db_password = config["MONGODB_URI"]["db_password"]
hostURI = "mongodb://{0}:{1}@{2}".format(quote_plus(db_username),
                                         quote_plus(db_password),
                                         hostname)

def find(db_filter):
    '''
    Find multiple documents matching the db_filter

        Parameters:
            db_filter (dict): A query that matches the document to delete
                e.g. {'result': 'Fail'} will query database for documents with result as Fail
        Returns:
            result (bool): find operation successfully completed or not
    '''
    with MongoClient(hostURI) as client:
        db = client['cft_test_results']
        tests = db.timings
        result = None
        try:
            result = tests.find(db_filter)
        except PyMongoError as mongo_error:
            print("Unable to search documents from database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            return result


def count_documents(db_filter):
    '''
    Count documents matching the db_filter

        Parameters:
            db_filter (dict): A query that matches the document to delete
                e.g. {'result': 'Fail'} will query database for documents with result as Fail
        Returns:
            result (int): number of documents matching the db_filter
    '''
    with MongoClient(hostURI) as client:
        db = client['cft_test_results']
        tests = db.timings
        result = None
        try:
            result = tests.count_documents(db_filter)
        except PyMongoError as mongo_error:
            print("Unable to search documents from database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            return result


def find_distinct(entry, db_filter):
    with MongoClient(hostURI) as client:
        db = client['cft_test_results']
        tests = db.timings
        result = None
        try:
            result = tests.distinct(entry, db_filter)
        except PyMongoError as mongo_error:
            print("Unable to search documents from database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            return result
