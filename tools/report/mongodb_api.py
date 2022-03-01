"""Functions to pull data from mongoDB using pymongo."""
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
                print(f"User does not have permission for operation. {ops_exception}")
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
