from pymongo import MongoClient
from pymongo.errors import PyMongoError
import configparser

# A MongoDb instance can have multiple databases in it.
# Each database can have multiple collections(tables) in it.
# Each collection can have multiple documents(row) in it.
config = configparser.ConfigParser()
config.read('config.ini')
writeHostURI = config["MONGODB_URI"]["writeHostURI"]
readHostURI = config["MONGODB_URI"]["readHostURI"]


def add_one_to_database(data):
    """
    Add single document to mongodb database

        Parameters:
            data (dict): The document to be inserted

        Returns:
            result (bool): insert operation successfully completed or not
    """
    with MongoClient(writeHostURI) as client:
        db = client['cft_test_results']  # Connect to cft_test_results database
        tests = db.results  # Connect to results collection in cft_test_results database
        try:
            tests.insert_one(data)
        except PyMongoError as mongo_error:
            print("Unable to insert documents into database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            print("Document added into database")
        return True


def add_multiple_to_database(data):
    """
    Add single document to mongodb database

        Parameters:
            data (list of dict): List of documents to be inserted

        Returns:
            result (bool): insert operation successfully completed or not
    """
    with MongoClient(writeHostURI) as client:
        db = client['cft_test_results']  # Connect to cft_test_results database
        tests = db.results  # Connect to results collection in cft_test_results database
        try:
            tests.insert_many(data)
        except PyMongoError as mongo_error:
            print("Unable to insert documents into database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            print("Documents added into database")
            return True


def find_and_update_one(db_filter, update):
    """
    Finds a single document and updates it

        Parameters:
            db_filter (dict): A query that matches the document to update
                e.g. {'testid': 'Test1'} will query database for a document with testid as Test1
            update (dict): The update operations to apply
                e.g. {'$set': {'result': 'Pass'}} will set Pass in result field
        Returns:
            result (bool): update operation successfully completed or not
    """
    with MongoClient(writeHostURI) as client:
        db = client['cft_test_results']
        tests = db.results
        try:
            tests.find_one_and_update(db_filter, {"$set": update})
        except PyMongoError as mongo_error:
            print("Unable to find and update document into database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            print("Document updated in database")
            return True


def delete_one(db_filter):
    """
    Delete a single document matching the db_filter

        Parameters:
            db_filter (dict): A query that matches the document to delete
                e.g. {'testid': 'Test1'} will query database for a document with testid as Test1
        Returns:
            result (bool): delete operation successfully completed or not
    """
    with MongoClient(writeHostURI) as client:
        db = client['cft_test_results']
        tests = db.results
        try:
            tests.delete_one(db_filter)
        except PyMongoError as mongo_error:
            print("Unable to delete a document from database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            print("Document deleted from database")
            return True


def delete_many(db_filter):
    """
    Delete multiple documents matching the db_filter

        Parameters:
            db_filter (dict): A query that matches the document to delete
                e.g. {'build': 'demo'} will query database for documents with build as demo
        Returns:
            result (bool): delete operation successfully completed or not
    """
    with MongoClient(writeHostURI) as client:
        db = client['cft_test_results']
        tests = db.results
        try:
            tests.delete_many(db_filter)
        except PyMongoError as mongo_error:
            print("Unable to delete documents from database. Observed following exception:")
            print(mongo_error)
            return False
        else:
            print("Documents deleted from database")
            return True


def find(db_filter):
    """
    Find multiple documents matching the db_filter

        Parameters:
            db_filter (dict): A query that matches the document to delete
                e.g. {'result': 'Fail'} will query database for documents with result as Fail
        Returns:
            result (bool): find operation successfully completed or not
    """
    with MongoClient(readHostURI) as client:
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
    with MongoClient(readHostURI) as client:
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
    with MongoClient(readHostURI) as client:
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
