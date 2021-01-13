import logging
import requests

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
