# -*- coding: utf-8 -*-
"""Timings APIs endpoint entry functions."""
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
from urllib.parse import quote_plus

import flask
from flask_restx import Resource, Namespace

from . import mongodbapi, read_config, validations

api = Namespace('Timings API', path="/", description='Timings related operations')


@api.route("/timings", doc={"description": "Create new entry of timings in DB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class Timings(Resource):
    """Methods for timings endpoint, to set and get timings data"""

    @staticmethod
    def post():
        """Create new timing entry."""
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="db_username/db_password missing in request body")
        response = validations.check_timings_fields(json_data)
        if not response[0]:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response=f"Unknown fields given or mandatory fields missing "
                                           f"{response[1]}")

        # Validate formats of mandatory fields
        validate_result = validations.validate_timings_fields(json_data)
        if not validate_result[0]:
            return flask.Response(status=validate_result[1][0],
                                  response=validate_result[1][1])
        json_data["testStartTime"] = validate_result[1]

        # Validate formats of extra fields
        valid_result = validations.validate_extra_timings_fields(json_data)
        if not valid_result[0]:
            return flask.Response(status=valid_result[1][0],
                                  response=valid_result[1][1])

        # Build MongoDB URI using username and password
        uri = read_config.MONGODB_URI.format(quote_plus(json_data["db_username"]),
                                             quote_plus(json_data["db_password"]),
                                             read_config.db_hostname)

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]

        add_result = mongodbapi.add_document(json_data, uri, read_config.db_name,
                                             read_config.timing_collection)
        if add_result[0]:
            ret = flask.Response(status=HTTPStatus.OK,
                                 response=f"Entry created. ID {add_result[1].inserted_id}")
        else:
            ret = flask.Response(status=add_result[1][0], response=add_result[1][1])
        return ret

    # pylint: disable=too-many-return-statements
    @staticmethod
    def get():
        """Get timing entry."""
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="db_username/db_password missing in request body")
        validate_field = validations.validate_get_timings_fields(json_data)
        if not validate_field[0]:
            return flask.Response(status=validate_field[1][0], response=validate_field[1][1])

        uri = read_config.MONGODB_URI.format(quote_plus(json_data["db_username"]),
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
                                                   read_config.timing_collection)
        if not count_results[0]:
            return flask.Response(status=count_results[1][0],
                                  response=count_results[1][1])
        if count_results[0] and count_results[1] == 0:
            return flask.Response(status=HTTPStatus.NOT_FOUND,
                                  response=f"No results for query {json_data}")

        query_results = mongodbapi.find_documents(json_data["query"], projection, uri,
                                                  read_config.db_name,
                                                  read_config.timing_collection)
        if query_results[0]:
            output = []
            for results in query_results[1]:
                del results["_id"]
                output.append(results)
            return flask.jsonify({'result': output})
        return flask.Response(status=query_results[1][0], response=query_results[1][1])
