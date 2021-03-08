# -*- coding: utf-8 -*-
"""Test Execution endpoint entry functions."""
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

from http import HTTPStatus
from urllib.parse import quote_plus

import flask
from flask_restx import Resource, Namespace

from . import mongodbapi, read_config, validations

api = Namespace('Test Execution', path="/reportsdb",
                description='Test execution related operations')


@api.route("/search", doc={"description": "Search test execution entries in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(404, "Not Found: No entry for that query in MongoDB.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Search(Resource):
    """Search endpoint"""

    @staticmethod
    def get():
        """Get test execution entry."""
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

        uri = read_config.mongodb_uri.format(quote_plus(json_data["db_username"]),
                                             quote_plus(json_data["db_password"]),
                                             read_config.db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]

        # Projection can be used to return certain fields from documents
        projection = None
        # Received request with projection field and projection is not empty dictionary
        if "projection" in json_data and bool(json_data["projection"]):
            projection = json_data["projection"]

        count_results = mongodbapi.count_documents(json_data["query"], uri, read_config.db_name,
                                                   read_config.results_collection)
        if not count_results[0]:
            return flask.Response(status=count_results[1][0],
                                  response=count_results[1][1])
        if count_results[0] and count_results[1] == 0:
            return flask.Response(status=HTTPStatus.NOT_FOUND,
                                  response=f"No results for query {json_data}")

        query_results = mongodbapi.find_documents(json_data["query"], projection, uri,
                                                  read_config.db_name,
                                                  read_config.results_collection)
        if query_results[0]:
            output = []
            for results in query_results[1]:
                del results["_id"]
                output.append(results)
            return flask.jsonify({'result': output})
        return flask.Response(status=query_results[1][0], response=query_results[1][1])


@api.route("/create", doc={"description": "Add test execution entry in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Create(Resource):
    """Create endpoint"""

    @staticmethod
    def post():
        """Create test execution entry."""
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
        json_data["testStartTime"] = validate_result[1]

        # Validate formats of extra fields
        valid_result = validations.validate_extra_db_fields(json_data)
        if not valid_result[0]:
            return flask.Response(status=valid_result[1][0],
                                  response=valid_result[1][1])

        # Build MongoDB URI using username and password
        uri = read_config.mongodb_uri.format(quote_plus(json_data["db_username"]),
                                             quote_plus(json_data["db_password"]),
                                             read_config.db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]

        add_result = mongodbapi.add_document(json_data, uri, read_config.db_name,
                                             read_config.results_collection)
        if add_result[0]:
            ret = flask.Response(status=HTTPStatus.OK,
                                 response=f"Entry created. ID {add_result[1].inserted_id}")
        else:
            ret = flask.Response(status=add_result[1][0], response=add_result[1][1])
        return ret


@api.route("/update", doc={"description": "Update test execution entries in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Update(Resource):
    """Update endpoint"""

    @staticmethod
    def patch():
        """Update test execution entry."""
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
        uri = read_config.mongodb_uri.format(quote_plus(json_data["db_username"]),
                                             quote_plus(json_data["db_password"]),
                                             read_config.db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]
        update_result = mongodbapi.update_documents(json_data["filter"], json_data["update"],
                                                    uri, read_config.db_name,
                                                    read_config.results_collection)
        if update_result[0]:
            return flask.Response(status=HTTPStatus.OK,
                                  response=f"Entry Updated. "
                                           f"Matched count {update_result[1].matched_count} "
                                           f"Updated count {update_result[1].modified_count}")
        return flask.Response(status=update_result[1][0], response=update_result[1][1])


@api.route("/distinct", doc={"description": "Get distinct values for given key"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(404, "Not Found: No entry for that query in MongoDB.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Distinct(Resource):
    """Update endpoint"""

    @staticmethod
    def get():
        """Get distinct values for given field."""
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="db_username/db_password missing in request body")
        validate_field = validations.validate_distinct_fields(json_data)
        if not validate_field[0]:
            return flask.Response(status=validate_field[1][0], response=validate_field[1][1])

        uri = read_config.mongodb_uri.format(quote_plus(json_data["db_username"]),
                                             quote_plus(json_data["db_password"]),
                                             read_config.db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]

        # Projection can be used to return certain fields from documents
        query = {}
        # Received request with projection field and projection is not empty dictionary
        if "query" in json_data and bool(json_data["query"]):
            query = json_data["query"]

        count_results = mongodbapi.distinct_fields(json_data["field"], query, uri,
                                                   read_config.db_name,
                                                   read_config.results_collection)
        if not count_results[0]:
            return flask.Response(status=count_results[1][0],
                                  response=count_results[1][1])
        return flask.jsonify({'result': count_results[1]})
