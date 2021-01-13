import pytest
import logging
import os
from commons.utils import system_utils
from commons.utils import config_utils

def test_system_utils():
    system_utils.run_remote_cmd("pwd","10.237.65.202","root","seagate")
    system_utils.run_local_cmd('dir') 
    system_utils.is_path_exists('/home')
    system_utils.is_path_exists("C:\\Users\\532698\\Documents\\EOS\\workspace\\eos-test\\eos_test\\utility")
    system_utils.open_empty_file("C:\\Users\\532698\\Documents\\a.txt")
    system_utils.listdir("C:\\Users\\532698\\Documents\\EOS\\workspace\\eos-test\\eos_test\\utility")
    system_utils.makedir()

def test_config_utils():
    config_utils.read_yaml("unittests/test_yaml.yaml")
    config_utils.write_yaml("unittests/test_yaml.yaml", "Adding extra information")

    json_data = {"_comment" : "Watch out for common error: last entry in list "
                              "can't have comma. Leading _ means not used. See "
                              "http://docs.python.org/library/json.html for "
                              "json->python data types. Note lower case for "
                              "true/false. null is None, but can just not have "
                              "an entry. Defaults are in configparser.py",
                 "csm_details": {"cloud_admin": "email",
                                 "cloud_admin_passowrd": "Seagate"
                                 }
                 }
    config_utils.create_content_json(os.getcwd(), json_data, 'user_json')
    fpath = os.path.join(os.getcwd(), 'user_json')
    config_utils.read_content_json(fpath)
    config_utils.parse_xml_controller("unittests/test_xml.xml",
                                      field_list=['location'])
    config_utils.get_config("config/common_config.yaml", "pdu")
    config_utils.update_config_ini("unittests/test_ini.ini",
                                   section="storage_enclosure",
                                   key="type", value="JBOD")
    config_utils.update_cfg_based_on_separator("unittests/config_yaml.yaml",
                                               "BUILD_VER_TYPE",
                                               "CORTX", "EOS")
