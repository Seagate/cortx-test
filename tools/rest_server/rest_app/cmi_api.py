# -*- coding: utf-8 -*-
"""Code Maturity Index endpoint entry functions. This APIs will be used to store CMI for builds."""
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

from copy import deepcopy
from http import HTTPStatus
from urllib.parse import quote_plus

import flask
from flask_restx import Resource, Namespace

from . import mongodbapi, read_config, validations

api = Namespace('CMI', path="/", description='CMI related operations')


@api.route("/cmi", doc={"description": "Create new entry of CMI in db"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class CMI(Resource):
    """Methods for cmi endpoint, to set and get CMI data"""

    @staticmethod
    def post():
        """Create new CMI entry."""
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="db_username/db_password missing in request body")

        response = validations.check_add_cmi_request_fields(json_data)

        # Validate correct fields are present
        if not response[0]:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response=f"Unknown fields given or mandatory fields missing  "
                                           f"{response[1]}")

        # Validate formats of mandatory fields
        validate_result = validations.validate_add_cmi_request_fields(json_data)
        if not validate_result[0]:
            return flask.Response(status=validate_result[1][0],
                                  response=validate_result[1][1])

        # Build MongoDB URI using username and password
        uri = read_config.MONGODB_URI.format(quote_plus(json_data["db_username"]),
                                             quote_plus(json_data["db_password"]),
                                             read_config.db_hostname)

        del json_data["db_username"]
        del json_data["db_password"]

        query = deepcopy(json_data)
        del query["cmi"]

        # Query and update the document if present else create new
        result = mongodbapi.update_document(query, {"$set": {"cmi": json_data["cmi"]}},
                                            uri, read_config.db_name, read_config.cmi_collection,
                                            upsert=True)
        if result[0]:
            return flask.Response(status=HTTPStatus.OK,
                                  response="Entry Updated/Created.")
        return flask.Response(status=result[1][0], response=result[1][1])

    @staticmethod
    def get():
        """Get CMI entry."""
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="db_username/db_password missing in request body")

        # Build MongoDB URI using username and password
        uri = read_config.MONGODB_URI.format(quote_plus(json_data["db_username"]),
                                             quote_plus(json_data["db_password"]),
                                             read_config.db_hostname)

        del json_data["db_username"]
        del json_data["db_password"]

        # Search and return document
        query_results = mongodbapi.find_documents(json_data, None, uri, read_config.db_name,
                                                  read_config.cmi_collection)
        if query_results[0]:
            output = []
            for result in query_results[1]:
                del result["_id"]
                output.append(result)
            return flask.jsonify({'result': output})
        return flask.Response(status=query_results[1][0], response=query_results[1][1])
