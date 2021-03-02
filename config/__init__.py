import os
import sys
from commons.utils import config_utils
from config.params import COMMON_CONFIG, CSM_CONFIG, SETUPS_FPATH
from config.params import RAS_CONFIG_PATH
from config.params import SSPL_TEST_CONFIG_PATH
from config.params import COMMON_DESTRUCTIVE_CONFIG_PATH
from commons import configmanager

CMN_CFG = config_utils.read_yaml(COMMON_CONFIG)[1]
RAS_VAL = config_utils.read_yaml(RAS_CONFIG_PATH)[1]
RAS_TEST_CFG = config_utils.read_yaml(SSPL_TEST_CONFIG_PATH)[1]
CMN_DESTRUCTIVE_CFG = config_utils.read_yaml(COMMON_DESTRUCTIVE_CONFIG_PATH)[1]
CSM_CFG = configmanager.get_config_wrapper(fpath=CSM_CONFIG)

args = sys.argv
args = dict(zip(args[::2],args[1::2]))

if '--local' in args and args['--local']:
    target = args['--target']
elif os.getenv('TARGET') is not None:
    target = os.environ["TARGET"]
else:
    target = "automation"

if os.path.exists(SETUPS_FPATH):
    SETUP_DETAILS = config_utils.read_content_json(SETUPS_FPATH)[target]
else:
    setup_query = {"setupname": target}
    SETUP_DETAILS = configmanager.get_config_wrapper(setup_query = setup_query)[target]
