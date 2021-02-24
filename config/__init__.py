from commons.utils import config_utils
from config import params
from config.params import COMMON_CONFIG
from config.params import RAS_CONFIG_PATH
from config.params import SSPL_TEST_CONFIG_PATH
from config.params import COMMON_DESTRUCTIVE_CONFIG_PATH

CMN_CFG = config_utils.read_yaml(COMMON_CONFIG)[1]
RAS_VAL = config_utils.read_yaml(RAS_CONFIG_PATH)[1]
RAS_TEST_CFG = config_utils.read_yaml(SSPL_TEST_CONFIG_PATH)[1]
CMN_DESTRUCTIVE_CFG = config_utils.read_yaml(COMMON_DESTRUCTIVE_CONFIG_PATH)[1]
