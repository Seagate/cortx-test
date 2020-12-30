import configparser
from urllib.parse import quote_plus
from datetime import datetime
import flask
from flask_restx import Resource, fields, Api

import mongodbapi

app = flask.Flask(__name__)

api = Api(app, version='1.0', title='MongoREST APIs')

config = configparser.ConfigParser()
config.read('config.ini')
try:
    db_hostname = config["MongoDB"]["db_hostname"]
    db_name = config["MongoDB"]["db_name"]
    collection = config["MongoDB"]["collection"]
except KeyError:
    print("Could not start REST server. Please verify config.ini file")
    exit(1)

db_keys_int = ["noOfNodes", "testExecutionTime"]
db_keys_array = ["nodesHostname", "testIDLabels", "testTags"]
db_keys_str = ["clientHostname", "OSVersion", "testName", "testID", "testPlanID",
               "testExecutionID", "testType", "testComponent", "testTeam",
               "testStartTime", "buildType", "buildNo", "logPath",
               "testResult", "healthCheckResult", "executionType"]
db_keys = db_keys_int + db_keys_array + db_keys_str

extra_db_keys_str = ["issueType", "issueID"]
extra_db_keys_bool = ["isRegression", "logCollectionDone"]
extra_db_keys = extra_db_keys_bool + extra_db_keys_str

search_fields = api.model('SearchDBEntry', {
    db_keys_str[0]: fields.String,  # clientHostname
    db_keys_str[1]: fields.String,  # OSVersion
    db_keys_str[2]: fields.String,  # testName
    db_keys_str[3]: fields.String,  # testID
    db_keys_str[4]: fields.String,  # testPlanID
    db_keys_str[5]: fields.String,  # testExecutionID
    db_keys_str[6]: fields.String,  # testType
    db_keys_str[7]: fields.String,  # testComponent
    db_keys_str[8]: fields.String,  # testTeam
    db_keys_str[9]: fields.DateTime,  # testStartTime
    db_keys_str[10]: fields.String,  # buildType
    db_keys_str[11]: fields.String,  # buildNo
    db_keys_str[12]: fields.String,  # logPath
    db_keys_str[13]: fields.String,  # testResult
    db_keys_str[14]: fields.String,  # healthCheckResult
    db_keys_str[15]: fields.String,  # executionType
    db_keys_array[0]: fields.List(fields.String),  # nodesHostname
    db_keys_array[1]: fields.List(fields.String),  # testIDLabels
    db_keys_array[2]: fields.List(fields.String),  # testTags
    db_keys_int[0]: fields.Integer,  # noOfNodes
    db_keys_int[1]: fields.Integer,  # testExecutionTime
    extra_db_keys_str[0]: fields.String(),  # issueType
    extra_db_keys_str[1]: fields.String(),  # issueID
    extra_db_keys_bool[0]: fields.Boolean(),  # isRegression
    extra_db_keys_bool[1]: fields.Boolean(),  # logCollectionDone
    "username": fields.String(required=True),
    "password": fields.String(required=True)
})

create_fields = api.model('CreateDBEntry', {
    db_keys_str[0]: fields.String(required=True),         # clientHostname
    db_keys_str[1]: fields.String(required=True),         # OSVersion
    db_keys_str[2]: fields.String(required=True),         # testName
    db_keys_str[3]: fields.String(required=True),         # testID
    db_keys_str[4]: fields.String(required=True),         # testPlanID
    db_keys_str[5]: fields.String(required=True),         # testExecutionID
    db_keys_str[6]: fields.String(required=True),         # testType
    db_keys_str[7]: fields.String(required=True),         # testComponent
    db_keys_str[8]: fields.String(required=True),         # testTeam
    db_keys_str[9]: fields.DateTime(required=True),       # testStartTime
    db_keys_str[10]: fields.String(required=True),        # buildType
    db_keys_str[11]: fields.String(required=True),        # buildNo
    db_keys_str[12]: fields.String(required=True),        # logPath
    db_keys_str[13]: fields.String(required=True),        # testResult
    db_keys_str[14]: fields.String(required=True),        # healthCheckResult
    db_keys_str[15]: fields.String(required=True),        # executionType
    db_keys_array[0]: fields.List(fields.String, required=True),  # nodesHostname
    db_keys_array[1]: fields.List(fields.String, required=True),  # testIDLabels
    db_keys_array[2]: fields.List(fields.String, required=True),  # testTags
    db_keys_int[0]: fields.Integer(required=True),        # noOfNodes
    db_keys_int[1]: fields.Integer(required=True),        # testExecutionTime
    extra_db_keys_str[0]: fields.String(),                # issueType
    extra_db_keys_str[1]: fields.String(),                # issueID
    extra_db_keys_bool[0]: fields.Boolean(),              # isRegression
    extra_db_keys_bool[1]: fields.Boolean(),              # logCollectionDone
    "username": fields.String(required=True),
    "password": fields.String(required=True),
})


def check_db_keys(json_data: dict) -> bool:
    """
    Check if mandatory db fields present

    Args:
        json_data: Data from request

    Returns:
        bool
    """
    for key in db_keys:
        if key not in json_data.keys():
            return False
    return True


def check_user_pass(json_data: dict) -> bool:
    """
    Check if mandatory username and password present in request

    Args:
        json_data: Data from request

    Returns:
        bool
    """
    if "username" in json_data.keys() and "password" in json_data.keys():
        return True
    return False


def validate_mandatory_db_fields(json_data: dict) -> (bool, tuple):
    """
    Validate format of each element

    Args:
        json_data: Data from request

    Returns:
        On failure returns http status code and message
        On success returns datetime in ISO 8601 format
    """
    for key in db_keys_int:
        if type(json_data[key]) != int:
            return False, (400, f"{key} should be integer")
    for key in db_keys_str:
        if type(json_data[key]) != str:
            return False, (400, f"{key} should be string")
    for key in db_keys_array:
        if type(json_data[key]) != list:
            return False, (400, f"{key} should be list")
        else:
            for item in json_data[key]:
                if type(item) != str:
                    return False, (400, f"{item} in {key} should be string")
    try:
        test_start_time = datetime.fromisoformat(json_data["testStartTime"])
    except ValueError:
        return False, (400, "testStartTime should be in ISO 8601 format")
    return True, test_start_time


def validate_extra_db_fields(json_data: dict) -> (bool, tuple):
    """
    Validate format of extra fields in request

    Args:
        json_data: Data from request

    Returns:
        On failure returns http status code and message
        On success returns True
    """
    for key in extra_db_keys_bool:
        if key in json_data.keys() and type(json_data[key]) != bool:
            return False, (400, f"{key} should be boolean")
    for key in extra_db_keys_str:
        if key in json_data.keys() and type(json_data[key]) != str:
            return False, (400, f"{key} should be string")
    return True, None


def validate_update_request(json_data: dict) -> (bool, tuple):
    """
    Validate format of fields in update request

    Args:
        json_data: Data from request

    Returns:
        On failure returns http status code and message
        On success returns True
    """
    update_keys = ["filter", "update"]
    for key in update_keys:
        if key not in json_data.keys():
            return False, (400, f"Please provide {update_keys} keys")
    for key in update_keys:
        if type(json_data[key]) != dict:
            return False, (400, f"Please provide {update_keys} keys as dictionary")
    return True, None


@api.route("/search", doc={"description": "Search test execution entries in MongoDB"})
@api.doc(body=search_fields)
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong username/password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(404, "Not Found: No entry for that query in MongoDB.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Search(Resource):
    @staticmethod
    def get():
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=400,
                                  response="Body is empty")
        if not check_user_pass(json_data):
            return flask.Response(status=400,
                                  response="username/password missing in request body")
        else:
            uri = "mongodb://{0}:{1}@{2}".format(quote_plus(json_data["username"]),
                                                 quote_plus(json_data["password"]),
                                                 db_hostname)
            del json_data["username"]
            del json_data["password"]
            count_results = mongodbapi.count_documents(json_data, uri, db_name, collection)
            if count_results[0] and count_results[1] > 0:
                query_results = mongodbapi.find_documents(json_data, uri,
                                                          db_name, collection)
                if query_results[0]:
                    output = []
                    for s in query_results[1]:
                        del s["_id"]
                        output.append(s)
                    return flask.jsonify({'result': output})
                else:
                    return flask.Response(status=query_results[1][0],
                                          response=query_results[1][1])
            elif count_results[0] and count_results[1] == 0:
                return flask.Response(status=404,
                                      response=f"No results for query {json_data}")
            elif not count_results[0]:
                return flask.Response(status=count_results[1][0],
                                      response=count_results[1][1])


@api.route("/create", doc={"description": "Add test execution entry in MongoDB"})
@api.doc(body=create_fields)
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong username/password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Create(Resource):
    @staticmethod
    def post():
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=400,
                                  response="Body is empty")
        if not check_db_keys(json_data):
            return flask.Response(status=400,
                                  response="Please provide all db keys")
        if not check_user_pass(json_data):
            return flask.Response(status=400,
                                  response="username/password missing in request body")

        # Validate formats of mandatory fields
        validate_result = validate_mandatory_db_fields(json_data)
        if not validate_result[0]:
            return flask.Response(status=validate_result[1][0],
                                  response=validate_result[1][1])
        else:
            json_data["testStartTime"] = validate_result[1]

        # Validate formats of extra fields
        valid_result = validate_extra_db_fields(json_data)
        if not valid_result[0]:
            return flask.Response(status=valid_result[1][0],
                                  response=valid_result[1][1])

        uri = "mongodb://{0}:{1}@{2}".format(quote_plus(json_data["username"]),
                                             quote_plus(json_data["password"]),
                                             db_hostname)
        del json_data["username"]
        del json_data["password"]
        add_result = mongodbapi.add_document(json_data, uri, db_name, collection)
        if add_result[0]:
            return flask.Response(status=201,
                                  response=f"Entry created. ID {add_result[1].inserted_id}")
        else:
            return flask.Response(status=add_result[1][0],
                                  response=add_result[1][1])


@api.route("/update", doc={"description": "Update test execution entries in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong username/password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Update(Resource):
    @staticmethod
    def patch():
        json_data = flask.request.get_json()
        print(json_data)
        if not json_data:
            return flask.Response(status=400,
                                  response="Body is empty")
        if not check_user_pass(json_data):
            return flask.Response(status=400,
                                  response="username/password missing in request body")

        # Validate if data has filter and update keys
        validate_result = validate_update_request(json_data)
        if not validate_result[0]:
            return flask.Response(status=validate_result[1][0],
                                  response=validate_result[1][1])

        uri = "mongodb://{0}:{1}@{2}".format(quote_plus(json_data["username"]),
                                             quote_plus(json_data["password"]),
                                             db_hostname)
        del json_data["username"]
        del json_data["password"]
        update_result = mongodbapi.update_document(json_data["filter"], json_data["update"],
                                                   uri, db_name, collection)
        if update_result[0]:
            return flask.Response(status=200,
                                  response=f"Entry Updated. "
                                           f"Matched count {update_result[1].matched_count} "
                                           f"Updated count {update_result[1].modified_count}")
        else:
            return flask.Response(status=update_result[1][0],
                                  response=update_result[1][1])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)
