"""Functions to pull data from mongoDB using pymongo."""
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
import sys

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure


def pymongo_exception(func):
    """Decorator for pymongo exceptions"""
    def new_func(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            return ret
        except ServerSelectionTimeoutError:
            print("Unable to connect to mongoDB. Probably MongoDB server is down")
            sys.exit(1)
        except OperationFailure as ops_exception:
            if ops_exception.code == 18:
                print(f"Wrong username/password. {ops_exception}")
                sys.exit(1)
            elif ops_exception.code == 13:
                print(
                    f"User does not have permission for operation. {ops_exception}")
                sys.exit(1)
            else:
                print(f"Unable to connect to mongoDB. {ops_exception}")
                sys.exit(1)
        except PyMongoError as mongo_error:
            print(f"Unable to connect to mongoDB. {mongo_error}")
            sys.exit(1)

    return new_func


@pymongo_exception
def count_documents(query: dict,
                    uri: str,
                    db_name: str,
                    collection: str
                    ) -> (bool, int):
    """
    Count search results for query from MongoDB database

    Args:
        query: Query to be searched in MongoDB
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database

    Returns:
        On success returns number of documents
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.count_documents(query)
        return result


@pymongo_exception
def find_documents(query: dict,
                   uri: str,
                   db_name: str,
                   collection: str
                   ) -> (bool, str):
    """
    Return search results for query from MongoDB database

    Args:
        query: Query to be searched in MongoDB
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database

    Returns:
        On success returns documents
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.find(query)
        return result


@pymongo_exception
def find_distinct_values(key: str,
                         query: dict,
                         uri: str,
                         db_name: str,
                         collection: str
                         ) -> (bool, str):
    """
    Return search results for distinct values for key in MongoDB database

    Args:
        key: Key field to get distinct values for
        query: Query to be searched in MongoDB
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database

    Returns:
        On success returns array of fields
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.distinct(key, query)
        return result


# collection.find(query).sort([("_id", pymongo.DESCENDING)]).limit(1)
@pymongo_exception
def get_aggregate(query: dict, group_query: dict, uri: str, db_name: str, collection: str
                  ) -> (bool, int):
    """
    Count search results for query from MongoDB database

    Args:
        query: Query to be searched in MongoDB
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database

    Returns:
        On success returns number of documents
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.aggregate([
            {"$match": query},
            {"$group": group_query}
        ])
        try:
            return list(result)[0]
        except IndexError:
            return {}
