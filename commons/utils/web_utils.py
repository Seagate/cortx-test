import logging
import requests
from typing import Any
from requests import Response

log = logging.getLogger(__name__)


def http_head_request(url:str, verify:bool=False):
    """
    Head request to specified url
    :param url: Endpoint url
    :param verify: True|False
    :return json: response
    """
    # headers = {
    #     'User-Agent': self.user_agent
    # }
    log.info("Getting head response")
    response = requests.head(url, verify=verify)
    log.debug("Head response: {}".format(response))
    return response


def http_get_request(url:str, verify:bool=False):
    """
    Function to execute get request
    :param url: Endpoint url
    :param verify: True|False
    :return json: response
    """
    log.info("Getting head response")
    response = requests.get(url, verify=verify)
    log.debug("Get response: {}".format(response))
    return response


def http_post_request(url: str, data: Any, headers: dict = {}, verify: bool = False) -> Response:
    log.info("Execute post request, url - [%s], data - [%s]" % (url, data))
    response = requests.post(url, json=data, headers=headers, verify=verify)
    log.info("Post request {} executed successfully.".format(url))
    log.debug("response headers - {}" % response.headers)
    log.debug("response content - {}" % response.json())
    return response


def http_patch_request(url: str, data: Any, headers: dict = {}, verify: bool = False) -> Response:
    log.info("Execute patch request, url - [%s], data - [%s]" % (url, data))
    response = requests.patch(url, json=data, headers=headers, verify=verify)
    log.info("Patch request {} executed successfully.".format(url))
    log.debug("response headers - {}" % response.headers)
    log.debug("response content - {}" % response.json())
    return response
