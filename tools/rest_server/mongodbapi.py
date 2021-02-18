from http import HTTPStatus

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure


def pymongo_exception(func):
    def new_func(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            return ret
        except ServerSelectionTimeoutError:
            return False, (HTTPStatus.SERVICE_UNAVAILABLE,
                           "Unable to connect to mongoDB. Probably MongoDB server is down")
        except OperationFailure as e1:
            if e1.code == 18:
                return False, (HTTPStatus.UNAUTHORIZED, f"Wrong username/password. {e1}")
            elif e1.code == 13:
                return False, (HTTPStatus.FORBIDDEN,
                               f"User does not have permission for operation. {e1}")
            else:
                return False, (HTTPStatus.SERVICE_UNAVAILABLE,
                               f"Unable to connect to mongoDB. {e1}")
        except PyMongoError as e2:
            return False, (HTTPStatus.SERVICE_UNAVAILABLE, f"Unable to connect to mongoDB. {e2}")

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
        db = client[db_name]
        tests = db[collection]
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
        db = client[db_name]
        tests = db[collection]
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
        db = client[db_name]
        tests = db[collection]
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
        db = client[db_name]
        tests = db[collection]
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
