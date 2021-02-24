import os
from commons.utils import config_utils
from config import params
from config.params import COMMON_CONFIG, CSM_CONFIG
from commons import configmanager

CMN_CFG = config_utils.read_yaml(COMMON_CONFIG)
CSM_CFG = configmanager.get_config_wrapper(fpath=CSM_CONFIG)
if os.path.exists("setups.json"):
    SETUP_DETAILS = config_utils.read_content_json("setups.json")
elif os.getenv('TARGET') is not None:
    setup_query = {"setupname": os.environ["TARGET"]}
    SETUP_DETAILS = configmanager.get_config_wrapper(setup_query = setup_query)
else:
    SETUP_DETAILS = configmanager.get_config_db(setup_query = {})
    config_utils.create_content_json("setups.json", SETUP_DETAILS)
    

