from pymongo import MongoClient
from pymongo.errors import PyMongoError
import configparser
from urllib.parse import quote_plus

# A MongoDb instance can have multiple databases in it.
# Each database can have multiple collections(tables) in it.
# Each collection can have multiple documents(row) in it.
config = configparser.ConfigParser()
config.read('config.ini')
hostname = config["MONGODB_URI"]["hostname"]
db_username = config["MONGODB_URI"]["db_username"]
db_password = config["MONGODB_URI"]["db_password"]
hostURI = "mongodb://{0}:{1}@{2}".format(quote_plus(db_username),
                                         quote_plus(db_password),
                                         hostname)
def find(db_filter):
    """
    Find multiple documents matching the db_filter

        Parameters:
            db_filter (dict): A query that matches the document to delete
                e.g. {'result': 'Fail'} will query database for documents with result as Fail
        Returns:
            result (bool): find operation successfully completed or not
    """
    with MongoClient(hostURI) as client:
        db = client['cft_test_results']
        tests = db.results
        result = None
        try:
            result = tests.find(db_filter)
        except PyMongoError as mongo_error:
            print("Unable to search documents from database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            print("Documents search complete")
            return result


def count_documents(db_filter):
    """
    Count documents matching the db_filter

        Parameters:
            db_filter (dict): A query that matches the document to delete
                e.g. {'result': 'Fail'} will query database for documents with result as Fail
        Returns:
            result (int): number of documents matching the db_filter
    """
    with MongoClient(hostURI) as client:
        db = client['cft_test_results']
        tests = db.results
        result = None
        try:
            result = tests.count_documents(db_filter)
        except PyMongoError as mongo_error:
            print("Unable to search documents from database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            print("Documents count complete")
            return result


def find_distinct(entry, db_filter):
    """
       Find distinct values of entry field

       Parameters:
           entry: field whose distinct values are required
           db_filter (dict): A query that matches the document to delete
               e.g. {'result': 'Fail'} will query database for documents with result as Fail
       Returns:
           result (int): number of documents matching the db_filter
       """
    with MongoClient(hostURI) as client:
        db = client['cft_test_results']
        tests = db.results
        result = None
        try:
            result = tests.distinct(entry, db_filter)
        except PyMongoError as mongo_error:
            print("Unable to search documents from database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            print("Distinct documents retrieved")
            return result
