import configparser
from http import HTTPStatus
from urllib.parse import quote_plus

import flask
from flask_restx import Resource, fields, Api

import mongodbapi
import validations

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


search_fields = api.model('SearchDBEntry', {
    validations.db_keys_str[0]: fields.String,  # clientHostname
    validations.db_keys_str[1]: fields.String,  # OSVersion
    validations.db_keys_str[2]: fields.String,  # testName
    validations.db_keys_str[3]: fields.String,  # testID
    validations.db_keys_str[4]: fields.String,  # testPlanID
    validations.db_keys_str[5]: fields.String,  # testExecutionID
    validations.db_keys_str[6]: fields.String,  # testType
    validations.db_keys_str[7]: fields.String,  # testComponent
    validations.db_keys_str[8]: fields.String,  # testTeam
    validations.db_keys_str[9]: fields.DateTime,  # testStartTime
    validations.db_keys_str[10]: fields.String,  # buildType
    validations.db_keys_str[11]: fields.String,  # buildNo
    validations.db_keys_str[12]: fields.String,  # logPath
    validations.db_keys_str[13]: fields.String,  # testResult
    validations.db_keys_str[14]: fields.String,  # healthCheckResult
    validations.db_keys_str[15]: fields.String,  # executionType
    validations.db_keys_array[0]: fields.List(fields.String),  # nodesHostname
    validations.db_keys_array[1]: fields.List(fields.String),  # testIDLabels
    validations.db_keys_array[2]: fields.List(fields.String),  # testTags
    validations.db_keys_int[0]: fields.Integer,  # noOfNodes
    validations.db_keys_int[1]: fields.Integer,  # testExecutionTime
    validations.extra_db_keys_str[0]: fields.String(),  # issueType
    validations.extra_db_keys_str[1]: fields.String(),  # issueID
    validations.extra_db_keys_bool[0]: fields.Boolean(),  # isRegression
    validations.extra_db_keys_bool[1]: fields.Boolean(),  # logCollectionDone
    "username": fields.String(required=True),
    "password": fields.String(required=True)
})

create_fields = api.model('CreateDBEntry', {
    validations.db_keys_str[0]: fields.String(required=True),         # clientHostname
    validations.db_keys_str[1]: fields.String(required=True),         # OSVersion
    validations.db_keys_str[2]: fields.String(required=True),         # testName
    validations.db_keys_str[3]: fields.String(required=True),         # testID
    validations.db_keys_str[4]: fields.String(required=True),         # testPlanID
    validations.db_keys_str[5]: fields.String(required=True),         # testExecutionID
    validations.db_keys_str[6]: fields.String(required=True),         # testType
    validations.db_keys_str[7]: fields.String(required=True),         # testComponent
    validations.db_keys_str[8]: fields.String(required=True),         # testTeam
    validations.db_keys_str[9]: fields.DateTime(required=True),       # testStartTime
    validations.db_keys_str[10]: fields.String(required=True),        # buildType
    validations.db_keys_str[11]: fields.String(required=True),        # buildNo
    validations.db_keys_str[12]: fields.String(required=True),        # logPath
    validations.db_keys_str[13]: fields.String(required=True),        # testResult
    validations.db_keys_str[14]: fields.String(required=True),        # healthCheckResult
    validations.db_keys_str[15]: fields.String(required=True),        # executionType
    validations.db_keys_array[0]: fields.List(fields.String, required=True),  # nodesHostname
    validations.db_keys_array[1]: fields.List(fields.String, required=True),  # testIDLabels
    validations.db_keys_array[2]: fields.List(fields.String, required=True),  # testTags
    validations.db_keys_int[0]: fields.Integer(required=True),        # noOfNodes
    validations.db_keys_int[1]: fields.Integer(required=True),        # testExecutionTime
    validations.extra_db_keys_str[0]: fields.String(),                # issueType
    validations.extra_db_keys_str[1]: fields.String(),                # issueID
    validations.extra_db_keys_bool[0]: fields.Boolean(),              # isRegression
    validations.extra_db_keys_bool[1]: fields.Boolean(),              # logCollectionDone
    "username": fields.String(required=True),
    "password": fields.String(required=True),
})


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
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="username/password missing in request body")
        else:
            # Build MongoDB URI using username and password
            uri = "mongodb://{0}:{1}@{2}".format(quote_plus(json_data["username"]),
                                                 quote_plus(json_data["password"]),
                                                 db_hostname)

            # Delete username and password as not needed to add those fields in DB
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
                return flask.Response(status=HTTPStatus.NOT_FOUND,
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
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_db_keys(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Please provide all db keys")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="username/password missing in request body")

        # Validate formats of mandatory fields
        validate_result = validations.validate_mandatory_db_fields(json_data)
        if not validate_result[0]:
            return flask.Response(status=validate_result[1][0],
                                  response=validate_result[1][1])
        else:
            json_data["testStartTime"] = validate_result[1]

        # Validate formats of extra fields
        valid_result = validations.validate_extra_db_fields(json_data)
        if not valid_result[0]:
            return flask.Response(status=valid_result[1][0],
                                  response=valid_result[1][1])

        # Build MongoDB URI using username and password
        uri = "mongodb://{0}:{1}@{2}".format(quote_plus(json_data["username"]),
                                             quote_plus(json_data["password"]),
                                             db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["username"]
        del json_data["password"]

        add_result = mongodbapi.add_document(json_data, uri, db_name, collection)
        if add_result[0]:
            return flask.Response(status=HTTPStatus.OK,
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
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="username/password missing in request body")

        # Validate if data has filter and update keys
        validate_result = validations.validate_update_request(json_data)
        if not validate_result[0]:
            return flask.Response(status=validate_result[1][0],
                                  response=validate_result[1][1])

        # Build MongoDB URI using username and password
        uri = "mongodb://{0}:{1}@{2}".format(quote_plus(json_data["username"]),
                                             quote_plus(json_data["password"]),
                                             db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["username"]
        del json_data["password"]
        update_result = mongodbapi.update_document(json_data["filter"], json_data["update"],
                                                   uri, db_name, collection)
        if update_result[0]:
            return flask.Response(status=HTTPStatus.OK,
                                  response=f"Entry Updated. "
                                           f"Matched count {update_result[1].matched_count} "
                                           f"Updated count {update_result[1].modified_count}")
        else:
            return flask.Response(status=update_result[1][0],
                                  response=update_result[1][1])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)
