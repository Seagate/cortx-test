from commons.utils import config_utils
from config import params
from config.params import COMMON_CONFIG, CSM_CONFIG
CMN_CFG = config_utils.read_yaml(COMMON_CONFIG)[1]
CSM_CFG = config_utils.read_yaml(CSM_CONFIG)[1]

