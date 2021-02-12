import configparser
from http import HTTPStatus
from urllib.parse import quote_plus

import flask
from flask_restx import Resource, Api

import mongodbapi
import validations

app = flask.Flask(__name__)

api = Api(app, version='1.0', title='ReportsDB APIs')

config = configparser.ConfigParser()
config.read('config.ini')
try:
    db_hostname = config["MongoDB"]["db_hostname"]
    db_name = config["MongoDB"]["db_name"]
    collection = config["MongoDB"]["collection"]
except KeyError:
    print("Could not start REST server. Please verify config.ini file")
    exit(1)

MONGODB_URI = "mongodb://{0}:{1}@{2}"


@api.route("/reportsdb/search", doc={"description": "Search test execution entries in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
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
                                  response="db_username/db_password missing in request body")
        validate_field = validations.validate_search_fields(json_data)
        if not validate_field[0]:
            return flask.Response(status=validate_field[1][0], response=validate_field[1][1])

        uri = MONGODB_URI.format(quote_plus(json_data["db_username"]),
                                 quote_plus(json_data["db_password"]),
                                 db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]

        # Projection can be used to return certain fields from documents
        projection = None
        # Received request with projection field and projection is not empty dictionary
        if "projection" in json_data and bool(json_data["projection"]):
            projection = json_data["projection"]

        count_results = mongodbapi.count_documents(json_data["query"], uri, db_name, collection)
        if count_results[0] and count_results[1] > 0:
            query_results = mongodbapi.find_documents(json_data["query"], projection, uri,
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


@api.route("/reportsdb/create", doc={"description": "Add test execution entry in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Create(Resource):
    @staticmethod
    def post():
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="db_username/db_password missing in request body")

        response = validations.check_db_keys(json_data)
        if not response[0]:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response=f"Unknown fields given or mandatory fields missing  "
                                           f"{response[1]}")

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
        uri = MONGODB_URI.format(quote_plus(json_data["db_username"]),
                                 quote_plus(json_data["db_password"]),
                                 db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]

        add_result = mongodbapi.add_document(json_data, uri, db_name, collection)
        if add_result[0]:
            return flask.Response(status=HTTPStatus.OK,
                                  response=f"Entry created. ID {add_result[1].inserted_id}")
        else:
            return flask.Response(status=add_result[1][0],
                                  response=add_result[1][1])


@api.route("/reportsdb/update", doc={"description": "Update test execution entries in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Update(Resource):
    @staticmethod
    def patch():
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="db_username/db_password missing in request body")

        # Validate if data has filter and update keys
        validate_result = validations.validate_update_request(json_data)
        if not validate_result[0]:
            return flask.Response(status=validate_result[1][0],
                                  response=validate_result[1][1])

        # Build MongoDB URI using username and password
        uri = MONGODB_URI.format(quote_plus(json_data["db_username"]),
                                 quote_plus(json_data["db_password"]),
                                 db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]
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
