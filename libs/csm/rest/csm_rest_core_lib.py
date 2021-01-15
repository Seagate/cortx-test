""" This is the core module for REST API. """
import logging
import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from commons.constants import Rest as const

class RestClient:
    """
        This is the class for rest calls
    """

    def __init__(self, config):
        """
        This function will initialize this class
        :param config: configuration of setup
        """
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self._log = logging.getLogger(__name__)
        self._config = config
        self._request = {"get": requests.get, "post": requests.post,
                         "patch": requests.patch, "delete": requests.delete,
                         "put": requests.put}
        self._base_url = "{}:{}".format(
            self._config["ip"], str(self._config["port"]))
        self._json_file_path = self._config[
            "jsonfile"] if 'jsonfile' in self._config else const.JOSN_FILE

    def rest_call(self, request_type, endpoint, secure_connection=True,
                  data=None, headers=None, params=None, json_dict=None,
                  save_json=False):
        """
        This function will request REST methods like GET, POST ,PUT etc.
        :param request_type: get/post/delete/update etc
        :param endpoint: endpoint url
        :param secure_connection: HTTP / HTTPS connection required
        :param data: data required for REST call
        :param headers: headers required for REST call
        :param params: parameters required for REST call
        :param save_json: In case user required to store json file
        :return: response of the request
        """
        # Building final endpoint request url
        set_secure = const.SSL_CERTIFIED if secure_connection else const.NON_SSL
        request_url = "{}{}{}".format(set_secure, self._base_url, endpoint)
        self._log.info("fetching data from : {}".format(request_url))

        # Request a REST call
        response_object = self._request[request_type](
            request_url, headers=headers,
            data=data, params=params, verify=False, json=json_dict)
        self._log.info("result of request is: {}".format(response_object))

        # Can be used in case of larger response
        if save_json:
            with open(self._json_file_path, 'w+') as json_file:
                json_file.write(json.dumps(response_object.json(), indent=4))

        return response_object
