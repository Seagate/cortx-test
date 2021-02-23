from commons.utils import config_utils
from config import params
from config.params import COMMON_CONFIG, CSM_CONFIG
from commons import configmanager
import os

CMN_CFG = config_utils.read_yaml(COMMON_CONFIG)
CSM_CFG = configmanager.get_config_wrapper(fpath=CSM_CONFIG)
if os.environ["TARGET"]:
    setup_query = {"setupname": os.environ["TARGET"]}
    SETUP_DETAILS = configmanager.get_config_wrapper(setup_query=setup_query)


