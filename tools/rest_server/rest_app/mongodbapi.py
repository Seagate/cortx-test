# -*- coding: utf-8 -*-
"""MongoDb APIs, backend for REST Server."""
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

from http import HTTPStatus

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
            return False, (HTTPStatus.SERVICE_UNAVAILABLE,
                           "Unable to connect to mongoDB. Probably MongoDB server is down")
        except OperationFailure as ops_exception:
            if ops_exception.code == 18:
                return False, (HTTPStatus.UNAUTHORIZED, f"Wrong username/password. {ops_exception}")
            if ops_exception.code == 13:
                return False, (HTTPStatus.FORBIDDEN,
                               f"User does not have permission for operation. {ops_exception}")
            return False, (HTTPStatus.SERVICE_UNAVAILABLE,
                           f"Unable to connect to mongoDB. {ops_exception}")
        except PyMongoError as mongo_error:
            return False, (HTTPStatus.SERVICE_UNAVAILABLE,
                           f"Unable to connect to mongoDB. {mongo_error}")

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
        On failure returns http status code and message
        On success returns number of documents
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.count_documents(query)
        return True, result


@pymongo_exception
def find_documents(query: dict,
                   projection: dict,
                   uri: str,
                   db_name: str,
                   collection: str
                   ) -> (bool, str):
    """
    Return search results for query from MongoDB database

    Args:
        query: Query to be searched in MongoDB
        projection: Fields to be returned
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database

    Returns:
        On failure returns http status code and message
        On success returns documents
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.find(query, projection)
        return True, result


@pymongo_exception
def add_document(data: dict,
                 uri: str,
                 db_name: str,
                 collection: str
                 ) -> (bool, str):
    """
    Add document in MongoDB database

    Args:
        data: Data for creating document in MongoDB
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database

    Returns:
        On failure returns http status code and message
        On success returns created document ID
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.insert_one(data)
        return True, result


@pymongo_exception
def update_documents(query: dict,
                     data: dict,
                     uri: str,
                     db_name: str,
                     collection: str
                     ) -> (bool, str):
    """
    Search and update all documents found in query

    Args:
        query: Query to be searched
        data: Data for creating document in MongoDB
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database

    Returns:
        On failure returns http status code and message
        On success returns created document ID
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.update_many(query, data)
        return True, result


# pylint: disable=too-many-arguments
@pymongo_exception
def update_document(query: dict,
                    data: dict,
                    uri: str,
                    db_name: str,
                    collection: str,
                    upsert: bool
                    ) -> (bool, str):
    """
    Search and update one document found in query

    Args:
        query: Query to be searched
        data: Data for creating document in MongoDB
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database
        upsert: Create entry if not present

    Returns:
        On failure returns http status code and message
        On success returns created document ID
    """
    with MongoClient(uri) as client:
        database = client[db_name]
        tests = database[collection]
        result = tests.find_one_and_update(query, data, upsert=upsert)
        return True, result


@pymongo_exception
def distinct_fields(field: str,
                    query: dict,
                    uri: str,
                    db_name: str,
                    collection: str
                    ) -> (bool, int):
    """
    Get distinct fields for given query from MongoDB database

    Args:
        field: Field for distinct
        query: Query to be searched in MongoDB
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database

    Returns:
        On failure returns http status code and message
        On success returns number of documents
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.distinct(field, query)
        return True, result


@pymongo_exception
def aggregate(data: list,
              uri: str,
              db_name: str,
              collection: str
              ) -> (bool, str):
    """
    Aggregate query  MongoDB database

    Args:
        data: Data for querying document in MongoDB
        uri: URI of MongoDB database
        db_name: Database name
        collection: Collection name in database

    Returns:
        On failure returns http status code and message
        On success returns created document ID
    """
    with MongoClient(uri) as client:
        pymongo_db = client[db_name]
        tests = pymongo_db[collection]
        result = tests.aggregate(data)
        return True, result
