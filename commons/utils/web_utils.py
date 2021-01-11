import logging
import requests

import ctp.common.ctperrors as ctper
from ctp.common.ctpexception import CTPException

log = logging.getLogger(__name__)


# =============================================================================
# Functions
# =============================================================================
def http_head_request(url, verify=False):
    """
    Head request to specified url
    :param verify:
    :param url:
    :return:
    """
    # headers = {
    #     'User-Agent': self.user_agent
    # }
    log.info("Getting head response")
    try:
        response = requests.head(url, verify=verify)
    except requests.exceptions.ConnectionError as error:
        err_msg = "error communication with the host: {}\n{}".format(url, error)
        log.error(err_msg)
        raise CTPException(ctper.HTTP_CONNECTION_ERROR, err_msg)
    log.debug("Head response: {}".format(response))
    return response

def http_get_request(url, verify=False):
    """
    Function to execute get request
    :param str url: Endpoint url
    :param bool verify: True|False
    :return json: response
    """
    log.info("Getting head response")
    try:
        response = requests.get(url, verify=verify)
    except requests.exceptions.ConnectionError as error:
        err_msg = "error communication with the host: {}\n{}".format(url, error)
        log.error(err_msg)
        raise CTPException(ctper.HTTP_CONNECTION_ERROR, err_msg)
    log.debug("Get response: {}".format(response))
    return response
