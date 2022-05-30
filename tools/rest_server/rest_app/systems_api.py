# -*- coding: utf-8 -*-
"""System endpoint entry functions."""
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

api = Namespace('Systems', path="/systemdb", description='Systems related operations')


@api.route("/search", doc={"description": "Search for system entries in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(404, "Not Found: No entry for that query in MongoDB.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class SearchSystems(Resource):
    """
       Rest API: search
       Endpoint: /systemdb/search
       For performing search operation on r2_systems collection.
    """

    # pylint: disable=too-many-return-statements
    @staticmethod
    def get():
        """Get for systems"""
        json_data = flask.request.get_json()
        if not json_data:
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="Body is empty")
        if not validations.check_user_pass(json_data):
            return flask.Response(status=HTTPStatus.BAD_REQUEST,
                                  response="db_username/db_password missing in request body")

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
                                                   read_config.system_collection)
        if count_results[0] and count_results[1] > 0:
            query_results = mongodbapi.find_documents(json_data["query"], projection, uri,
                                                      read_config.db_name,
                                                      read_config.system_collection)
            if query_results[0]:
                output = []
                for results in query_results[1]:
                    del results["_id"]
                    output.append(results)
                return flask.jsonify({'result': output})

            return flask.Response(status=query_results[1][0], response=query_results[1][1])
        if count_results[0] and count_results[1] == 0:
            return flask.Response(status=HTTPStatus.NOT_FOUND,
                                  response=f"No results for query {json_data}")
        if not count_results[0]:
            return flask.Response(status=count_results[1][0],
                                  response=count_results[1][1])
        return flask.Response(status=HTTPStatus.BAD_REQUEST,
                              response=f"No results for query {json_data}")

    def __str__(self):
        return self.__class__.__name__


@api.route("/create", doc={"description": "Add system entry in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class CreateSystems(Resource):
    """
         Rest API: create
         Endpoint: /systemdb/create
         For performing create operation on r2_systems collection.
      """

    @staticmethod
    def post():
        """Post for systems"""
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

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]

        add_result = mongodbapi.add_document(json_data, uri, read_config.db_name,
                                             read_config.system_collection)
        if add_result[0]:
            return flask.Response(status=HTTPStatus.OK,
                                  response=f"Entry created. ID {add_result[1].inserted_id}")
        return flask.Response(status=add_result[1][0], response=add_result[1][1])

    def __str__(self):
        return self.__class__.__name__


@api.route("/update", doc={"description": "Update system entries in MongoDB"})
@api.response(200, "Success")
@api.response(400, "Bad Request: Missing parameters. Do not retry.")
@api.response(401, "Unauthorized: Wrong db_username/db_password.")
@api.response(403, "Forbidden: User does not have permission for operation.")
@api.response(503, "Service Unavailable: Unable to connect to mongoDB.")
class UpdateSystems(Resource):
    """
         Rest API: update
         Endpoint: /systemdb/update
         For performing update operation on r2_systems collection.
      """

    @staticmethod
    def patch():
        """Patch for systems"""
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

        # Delete username and password as not needed to add those fields in DB
        del json_data["db_username"]
        del json_data["db_password"]
        update_result = mongodbapi.update_document(json_data["filter"], json_data["update"],
                                                   uri, read_config.db_name,
                                                   read_config.system_collection, upsert=False)
        if update_result[0]:
            return flask.Response(status=HTTPStatus.OK,
                                  response="Entry Updated.")
        return flask.Response(status=update_result[1][0], response=update_result[1][1])

    def __str__(self):
        return self.__class__.__name__
