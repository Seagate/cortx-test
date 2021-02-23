from commons.utils import config_utils
from config import params
from config.params import COMMON_CONFIG, RAS_CONFIG_PATH,\
    SSPL_TEST_CONFIG_PATH, COMMON_DESTRUCTIVE_CONFIG_PATH

CMN_CFG = config_utils.read_yaml(COMMON_CONFIG)[1]
RAS_VAL = config_utils.read_yaml(RAS_CONFIG_PATH)[1]
RAS_TEST_CFG = config_utils.read_yaml(SSPL_TEST_CONFIG_PATH)[1]
CMN_DESTRUCTIVE_CFG = config_utils.read_yaml(COMMON_DESTRUCTIVE_CONFIG_PATH)[1]
