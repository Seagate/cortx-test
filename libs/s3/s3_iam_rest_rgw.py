#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""RGW_api test library which contains CRUD of IAM user."""
# pylint: disable=E0401
import asyncio
from http import HTTPStatus
import json
import base64
from hashlib import sha1
import hmac
import ssl
from urllib.parse import urlencode
from typing import Any, Dict, Optional, Tuple
from time import gmtime, strftime
from aiohttp import ClientSession, ClientError

from config import CMN_CFG
from commons import params
from comptests.s3.exceptions.s3_client_exception import HttpClientException
from comptests.s3.exceptions.s3_client_exception import S3ClientException

class HttpClient:
    '''
     Base HTTP client for CORTX utils.
     Enable user to asynchronously send HTTP requests.
    '''
    #pylint: disable-msg=too-many-arguments
    def __init__(
        self, host: str = 'localhost', port: int = 30080,
        tls_enabled: bool = False, ca_bundle: str = '',
        timeout: int = 5
    ) -> None:
        """
        Initialize the client.
        :param host: hostname of the server.
        :param port: port of the server.
        :param tls_enabled: flag to use https.
        :param ca_bundle: path to the root CA certificate.
        :param timeout: connection timeout.
        :returns: None.
        """

        self._host = host
        self._port = port
        self._url = f"{'https' if tls_enabled else 'http'}://{host}:{port}"
        self._ssl_ctx = ssl.create_default_context(cafile=ca_bundle) if ca_bundle else False
        self._timeout = timeout
    @classmethod
    def http_date(cls) -> str:
        """
        Return the 'now' datetime in RFC 1123 format.
        :returns: string with datetime.
        """

        now = gmtime()
        return strftime("%a, %d %b %Y %H:%M:%S +0000", now)
    #pylint: disable-msg=too-many-arguments
    async def request(
        self, verb: str, path: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        request_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[HTTPStatus, Optional[str]]:
        """
        Send the request to the server.
        :param verb: HTTP method of the request (GET, POST, etc.).
        :param path: server's URI to send the request to (e.g. /admin/user).
        :param headers: HTTP headers of the request.
        :param query_params: request parameters to be added into the query.
        :param request_params: request parameters to be added into the body.
        :returns: HTTP status and the body of the response.
        """

        final_url = self._url
        if path is not None:
            final_url += '/' if not path.startswith('/') else ""
            final_url += path
        if query_params is not None:
            final_url += "?" if "?" not in path else "&"
            final_url += urlencode(query_params)
        async with ClientSession() as http_session:
            try:
                async with http_session.request(method=verb, headers=headers, data=request_params,
                                                url=final_url, ssl=self._ssl_ctx,
                                                timeout=self._timeout) as resp:
                    status = resp.status
                    body = await resp.text()
                    return status, body
            except ClientError as error:
                raise HttpClientException(str(error)) from None

class S3Client(HttpClient):
    """
    Low level S3 HTTP client.
    Enable user to send signed HTTP requests to the any S3 REST API.
    """
    #pylint: disable-msg=too-many-arguments
    def __init__(
        self, access_key_id: str, secret_access_key: str,
        host: str = 'localhost', port: int = 8000,
        tls_enabled: bool = False, ca_bundle: str = '',
        timeout: int = 5
    ) -> None:
        """
        Initialize the client.
        :param access_key_id: access key id of the admin user.
        :param secret_access_key: secret access key of the admin user.
        :param host: hostname of the S3 server.
        :param port: port of the S3 server.
        :param tls_enabled: flag to use https.
        :param ca_bundle: path to the root CA certificate.
        :param timeout: connection timeout.
        :returns: None.
        """

        super().__init__(host, port, tls_enabled, ca_bundle, timeout)
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key

    def _generate_signature(self, verb: str, headers: Dict[str, str], path: str) -> str:
        """
        Generate an S3 compatible authorization signature.
        :param verb: HTTP method of the request (GET, POST, etc.).
        :param headers: HTTP headers of the request.
        :param path: server's URI to send the request to (e.g. /admin/user).
        :returns: signature string.
        """

        required_headers = ["content-md5", "content-type", "date"]
        string_to_sign = f"{verb}\n"
        for key in sorted(required_headers):
            val = headers.get(key, "")
            string_to_sign += f"{val}\n"
        string_to_sign += path.split('?')[0]
        string_to_sign_bytes = string_to_sign.encode("UTF-8")
        secret_access_key_bytes = self._secret_access_key.encode("UTF-8")
        secret_key_hmac = hmac.new(secret_access_key_bytes, string_to_sign_bytes, sha1).digest()
        signature_bytes = base64.b64encode(secret_key_hmac).strip()
        signature = f"AWS {self._access_key_id}:{signature_bytes.decode('UTF-8')}"
        return signature
    #pylint: disable-msg=too-many-arguments
    async def signed_http_request(
        self, verb: str, path: str, headers: Dict[str, str] = None,
        query_params: Dict[str, Any] = None, request_params: Dict[str, Any] = None
    ) -> Tuple[HTTPStatus, Optional[str]]:
        """
        Send an S3-signed request.
        :param verb: HTTP method of the request (GET, POST, etc.).
        :param path: server's URI to send the request to (e.g. /admin/user).
        :param headers: HTTP headers of the request.
        :param query_params: request parameters to be added into the query.
        :param request_params: request parameters to be added into the body.
        :returns: HTTP status and the body of the response.
        """

        # 'content-type' and 'date' headers need to be signed.
        # If not provided by the user they might be attached by the HTTP framework
        # at the time of sending making the signature incorrect.
        # Here headers are manually added in a proper format.
        if headers is None:
            headers = {}
        if 'content-type' not in headers:
            headers['content-type'] = 'application/x-www-form-urlencoded'
        headers['date'] = self.http_date()
        # 'Authorization' header provides the required signature
        headers['authorization'] = self._generate_signature(verb, headers, path)
        try:
            status, body = await self.request(verb, path, headers, query_params, request_params)
            return status, body
        except (HttpClientException, asyncio.TimeoutError) as error:
            reason = str(error)
            if isinstance(error, asyncio.TimeoutError):
                reason = "Request timeout"
            raise S3ClientException(reason) from None

class RestApiRgw:
    """
    Class related to rgw rest Api's operations.
    IAM related operations.
    """

    ACCESS_KEY = CMN_CFG["rgw_admin"]["access_key"]
    SECRET_KEY = CMN_CFG["rgw_admin"]["secret_key"]
    HOST = CMN_CFG["nodes"][0]["hostname"]
    PORT = CMN_CFG["rgw_admin"]["port"]
    async def create_user(self,user_params) -> Tuple[HTTPStatus, Dict[str, Any]]:
        """
        Illustrate S3Client signed_http_request work.
        Create IAM user by specifying parameters, HTTP method and path.
        :returns: HTTP status code and user information as parsed json.
        """

        rgwcli = S3Client(
           self.ACCESS_KEY , self.SECRET_KEY, self.HOST, self.PORT, tls_enabled=False)
        status, body = await rgwcli.signed_http_request(
            'PUT', params.IAM_USER, query_params=user_params)
        user_info = json.loads(body)
        return status, user_info
    async def delete_user(self,user_params) -> Tuple[HTTPStatus, Dict[str, Any]]:
        """
        Illustrate S3Client signed_http_request work.
        Create IAM user by specifying parameters, HTTP method and path.
        :returns: HTTP status code and user information as parsed json.
        """

        rgwcli = S3Client(
            self.ACCESS_KEY , self.SECRET_KEY, self.HOST, self.PORT, tls_enabled=False)
        status = await rgwcli.signed_http_request(
            'DELETE', params.IAM_USER, query_params=user_params)
        return status

    async def get_user_info(self,user_params) -> Tuple[HTTPStatus, Dict[str, Any]]:
        """
        Illustrate S3Client signed_http_request work.
        Create IAM user by specifying parameters, HTTP method and path.
        :returns: HTTP status code and user information as parsed json.
        """

        rgwcli = S3Client(
            self.ACCESS_KEY , self.SECRET_KEY, self.HOST, self.PORT, tls_enabled=False)
        status, user_info = await rgwcli.signed_http_request(
            'GET', params.IAM_USER, query_params=user_params)
        return status, user_info

    async def put_user_policy(self,user_params) -> Tuple[HTTPStatus, Dict[str, Any]]:
        """
        Illustrate S3Client signed_http_request work.
        Create IAM user by specifying parameters, HTTP method and path.
        :returns: HTTP status code and user information as parsed json.
        """

        rgwcli = S3Client(
            self.ACCESS_KEY , self.SECRET_KEY, self.HOST, self.PORT, tls_enabled=False)
        status = await rgwcli.signed_http_request(
            'POST', "/", query_params=user_params)
        return status

    async def delete_user_policy(self, user_params, access_key= None,
                                 secret_key=None) -> Tuple[HTTPStatus, Dict[str, Any]]:
        """
        Delete IAM User Policy
        :param user_params: User Parameters.
        :param access_key: Access Key.
        :param secret_key: Secret Key.
        :returns: HTTP status code and user information as parsed json.
        """
        if access_key and secret_key:
            rgw_client = S3Client(
                access_key, secret_key, self.HOST, self.PORT, tls_enabled=False)
            status = await rgw_client.signed_http_request('POST', "/", query_params=user_params)
            return status

        rgwcli = S3Client(
        self.ACCESS_KEY , self.SECRET_KEY, self.HOST, self.PORT, tls_enabled=False)
        status = await rgwcli.signed_http_request('POST', "/", query_params=user_params)
        return status

    async def get_user_policy(self,user_params, access_key=None,
                              secret_key=None) -> Tuple[HTTPStatus, Dict[str, Any]]:
        """
        Illustrate S3Client signed_http_request work.
        Create IAM user by specifying parameters, HTTP method and path.
        :returns: HTTP status code and user information as parsed json.
        """

        if access_key and secret_key:
            rgw_client = S3Client(
                access_key, secret_key, self.HOST, self.PORT, tls_enabled=False)
            status = await rgw_client.signed_http_request('POST', "/", query_params=user_params)
            return status

        rgwcli = S3Client(
        self.ACCESS_KEY , self.SECRET_KEY, self.HOST, self.PORT, tls_enabled=False)
        status = await rgwcli.signed_http_request('POST', "/", query_params=user_params)
        return status
