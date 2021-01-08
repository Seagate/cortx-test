#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#


################################################################################
# Standard libraries
################################################################################
import logging
import os
import yaml
import json
import shutil
import re
import xml.etree.ElementTree
from configparser import ConfigParser, MissingSectionHeaderError
################################################################################
# Local libraries
################################################################################

import commons.errorcodes as cterr
from commons.exceptions import CTException

################################################################################
# Constants
################################################################################
log = logging.getLogger(__name__)

################################################################################
# YAML Functions
################################################################################


def read_yaml(fpath):
    """Read yaml file and return dictionary/list of the content"""
    if os.path.isfile(fpath):
        with open(fpath) as fin:
            try:
                data = yaml.safe_load(fin)
            except yaml.YAMLError as exc:
                err_msg = "Failed to parse: {}\n{}".format(fpath, str(exc))
                raise CTException(cterr.YAML_SYNTAX_ERROR, err_msg)

    else:
        err_msg = "Specified file doesn't exist: {}".format(fpath)
        raise CTException(cterr.FILE_MISSING, err_msg)

    return data


def write_yaml(fpath, write_data, backup=True):
    """
    This functions overwrites the content of given yaml file with given data
    :param str fpath: yaml file path to be overwritten
    :param dict/list write_data: data to be written in yaml file
    :param bool backup: if set False, backup will not be taken before overwriting
    :return: True/False, yaml file path
    :rtype: boolean, str
    """
    try:
        if backup:
            bkup_path = f'{fpath}.bkp'
            shutil.copy2(fpath, bkup_path)
            log.debug("Backup file {} at {}".format(fpath, bkup_path))
        with open(fpath, 'w') as fobj:
            yaml.safe_dump(write_data, fobj)
        log.debug("Updated yaml file at {}".format(fpath))
    except BaseException as error:
        log.error(
            "{}".format(CTException(cterr.FILE_MISSING, error)))
        return False, error
    return True, fpath

################################################################################
# JSON Functions
################################################################################


def create_content_json(home, data, user_json):
    """

    :param home:
    :param data:
    :param user_json:
    :return:
    """
    pth = os.path.join(home, user_json)
    with open(pth, 'w') as outfile:
        json.dump(data, outfile, ensure_ascii=False)


def read_content_json(home, user_json):
    """

    :param home:
    :param user_json:
    :return:
    """
    pth = os.path.join(home, user_json)
    data = None
    with open(pth, 'rb') as json_file:
        data = json.loads(json_file.read())
    return data

################################################################################
# XML Functions
################################################################################


def parse_xml_controller(filepath, field_list, xml_tag="PROPERTY"):
    """
    This function parses xml file and converts it into nested dictionary.
    :param filepath: File path of the xml file to be parsed
    :type: str
    :param field_list: List of the required fields
    :type: list of the strings
    :param xml_tag: Tag in the xml file
    :type: str
    :return: Nested dictionary having values of the fields mentioned in
    field list
    :rtype: Nested dict
    """
    try:
        e = xml.etree.ElementTree.parse(filepath).getroot()

        d = {}
        new_d = {}
        listkeys = []
        i = 0

        fields = field_list
        for child in e.iter(xml_tag):
            d['dict_{}'.format(i)] = {}
            for field in fields:
                if (child.attrib['name']) == field:
                    new_d[field] = child.text
                    listkeys.append('True')
                    d['dict_{}'.format(i)] = new_d
            if listkeys.count('True') == len(fields):
                i += 1
                new_d = {}
                listkeys = []

        log.debug("Removing empty dictionaries")
        i = 0
        while True:
            if d['dict_{}'.format(i)] == {}:
                del (d['dict_{}'.format(i)])
                break
            i += 1

        log.debug(d)
        return True, d
    except BaseException as error:
        log.error(
            "{}".format(CTException(cterr.FILE_MISSING, error)))

################################################################################
# Config Parser Functions
################################################################################


def get_config(path, section=None, key=None):
    """
    Get config file value as per the section and key
    :param path: File path
    :param section: Section name
    :param key: Section key name
    :return: key value else all items else None
    """
    try:
        config = ConfigParser()
        config.read(path)
        if section and key:
            log.debug(config.get(section, key))
            return config.get(section, key)
        else:
            log.debug(config.items(section))
            return config.items(section)
    except MissingSectionHeaderError:
        keystr = "{}=".format(key)
        with open(path, "r") as fp:
            for line in fp:
                if keystr in line and "#" not in line:
                    return line[len(keystr):].strip()
        return None


def update_config_ini(path, section, key, value):
    """
    Update config file value as per the section and key
    :param path: File path
    :param section: Section name
    :param key: Section key name
    :param value: new value
    :return: boolean
    """
    config = ConfigParser()
    config.read(path)
    try:
        config.set(section, key, value)
        with open(path, "w") as configfile:
            config.write(configfile)
    except Exception as error:
        log.error("{}".format(CTException(cterr.INVALID_CONFIG_FILE, error)))
        return False
    return True


def update_config_helper(filename, key, old_value, new_value, delimiter):
    """
    helper method for update_cfg_based_on_separator
    :param filename: file to update
    :param key: key in file
    :param old_value: old value of key
    :param new_value: new value of key
    :param delimiter: delimiter used in file
    :return: bool, string
    """
    if os.path.exists(filename):
        shutil.copy(filename, filename + '_bkp')
        nw_value = list(new_value)
        ol_value = list(old_value)
        with open(filename, 'r+') as f_in:
            for line in f_in.readlines():
                if delimiter in line:
                    if key in line:
                        f_in.seek(0, 0)
                        data = f_in.read()
                        if delimiter == ':':
                            if '"' in data:
                                old_pattern = '{}{}{}"{}"'.format(
                                    key, ":", " ", old_value)
                                new_pattern = '{}{}{}"{}"'.format(
                                    key, ":", " ", new_value)
                            else:
                                old_pattern = '{}{}{}{}'.format(
                                    key, ":", " ", old_value)
                                new_pattern = '{}{}{}{}'.format(
                                    key, ":", " ", new_value)
                            log.debug("old_pattern: {}".format(old_pattern))
                            log.debug("new_pattern: {}".format(new_pattern))
                        else:
                            old_pattern = key + "=" + old_value
                            new_pattern = key + "=" + new_value
                        if len(ol_value) > len(nw_value):
                            count = len(ol_value) - len(nw_value)
                            new_pattern = new_pattern + " " * count
                            match = re.search(old_pattern, data)
                            span_ = match.span()
                            f_in.seek(span_[0])
                            f_in.write(new_pattern)
                            log.debug(
                                "Old pattern {} got replaced by new pattern {}".format(
                                    old_pattern, new_pattern))
                            f_in.seek(0, 0)
                            new_data = f_in.read()
                            return True, new_data
                        else:
                            match = re.search(old_pattern, data)
                            span_ = match.span()
                            f_in.seek(span_[0])
                            f_in.write(new_pattern)
                            log.debug(
                                "Old pattern {} got replaced by new pattern {}".format(
                                    old_pattern, new_pattern))
                            f_in.seek(0, 0)
                            new_data = f_in.read()
                            return True, new_data


def update_cfg_based_on_separator(filename, key, old_value, new_value):
    """
    Editing a file provided with : or = separator
    :param filename: file to update
    :param key: key in file
    :param old_value: old value of key
    :param new_value: new value of key
    :return: bool
    """
    try:
        with open(filename, 'r+') as f_in:
            for line in f_in.readlines():
                if "=" in line:
                    update_config_helper(
                        filename, key, old_value, new_value, "=")
                elif ":" in line:
                    update_config_helper(
                        filename, key, old_value, new_value, ":")
                return True, new_value
    except AttributeError as error:
        log.error(
            'Old value : {} is incorrect, please correct it and try again'.format(old_value))
        return False, error
    except Exception as error:
        os.remove(filename)
        os.rename(filename + '_bkp', filename)
        log.debug(
            "Removed original corrupted file and Backup file has been restored ")
        log.error(
            "*ERROR* An exception occurred in upload_config : {}".format(error))
        return False, error

################################################################################
# Update YAML configs
################################################################################
# Dictionary mapping to keys in config/main_config.yaml
# ALL_CONFIGS keys should match keys in config/main_config.yaml


MAIN_CONFIG_PATH = "config/main_config.yaml"
# ALL_CONFIGS = {
#     "common_config": "config/common_config.yaml",
#     "s3_config": "config/s3/s3_config.yaml",
#     "blackbox_config_jcloud": "config/blackbox/test_jcloud_jclient.yaml",
#     "prov_config": "config/provisioner/provisioner_config.yaml",
#     "prov_reset": "config/provisioner/test_provisioner_reset.yaml",
#     "prov_system": "config/provisioner/test_provisioner_system.yaml",
#     "ras_config": "config/ras/ras_config.yaml",
#     "ras_testlib_unittest": "config/ras/test_ras_test_lib_unittest.yaml",
#     "csm_config": "config/csm/csm_config.yaml",
# }


def read_write_config(config, path):
    """
    read and update values from source_file to destination config
    :param config: key from source_file
    :type config: str
    :param path: path of destination config
    :type path: str
    :return: None
    """
    log.debug("Reading and updating : {} at {}".format(config, path))
    conf_values = read_yaml(MAIN_CONFIG_PATH)
    log.debug("VALUES TO UPDATE:",  conf_values[config])
    dict_val = conf_values[config]
    keys = dict_val.keys()
    log.debug(keys)
    curr_values = read_yaml(path)
    log.debug("OLD CONFIG : {}".format(curr_values))
    for key in keys:
        if key in curr_values:
            try:
                for i_key in dict_val[key].keys():
                    if i_key in curr_values[key]:
                        log.debug("Replacing inner_key : {}".format(i_key))
                        log.debug("Old value : {}".format(curr_values[key][i_key]))
                        curr_values[key][i_key] = dict_val[key][i_key]
                        log.debug("New value : {}".format(dict_val[key][i_key]))
            except BaseException as error:
                log.debug("Replacing key : {}".format(key))
                log.debug("Old value : {}".format(curr_values[key]))
                curr_values[key] = dict_val[key]
                log.debug("New value : {}".format(dict_val[key]))
                log.error(
                    "*ERROR* An exception occurred in upload_config : {}".format(
                        error))

    write_yaml(path, curr_values, backup=False)
    updated_values = read_yaml(path)
    log.debug("UPDATED CONFIG : {}".format(updated_values))


def update_configs(all_configs):
    """
    Update all configs mentioned in ALL_CONFIGS with values of MAIN_CONFIG_PATH
    :param all_configs: Dictionary of paths of all config files
    :type all_configs: dict
    """
    for conf in all_configs.keys():
        read_write_config(conf, all_configs[conf])
