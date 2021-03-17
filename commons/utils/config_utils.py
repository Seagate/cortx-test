#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""
Python library which have config related operations using package
like config parser, yaml etc.
"""
import logging
import os
import json
import shutil
import re
from configparser import ConfigParser, MissingSectionHeaderError, NoSectionError
from defusedxml.cElementTree import parse
import yaml
from jsonschema import validate
import commons.errorcodes as cterr
from commons.exceptions import CTException

LOG = logging.getLogger(__name__)
MAIN_CONFIG_PATH = "config/main_config.yaml"


def read_yaml(fpath: str) -> tuple:
    """
    Read yaml file and return dictionary/list of the content.

    :param str fpath: Path of yaml file to be read
    :return: Boolean, Data
    """
    if os.path.isfile(fpath):
        with open(fpath) as fin:
            try:
                data = yaml.safe_load(fin)
            except yaml.YAMLError as exc:
                err_msg = "Failed to parse: {}\n{}".format(fpath, str(exc))
                LOG.error(err_msg)
                return False, exc

    else:
        err_msg = "Specified file doesn't exist: {}".format(fpath)
        LOG.error(err_msg)
        return False, cterr.FILE_MISSING

    return True, data


def write_yaml(
        fpath: str,
        write_data: dict or list,
        backup: bool = True) -> tuple:
    """
    Function overwrites the content of given yaml file with given data.

    :param str fpath: yaml file path to be overwritten
    :param dict/list write_data: data to be written in yaml file
    :param bool backup: if set False, backup will not be taken before
    overwriting
    :return: True/False, yaml file path
    :rtype: boolean, str
    """
    try:
        if backup:
            bkup_path = f'{fpath}.bkp'
            shutil.copy2(fpath, bkup_path)
            LOG.debug("Backup file %s at %s", fpath, bkup_path)
        with open(fpath, 'w') as fobj:
            yaml.safe_dump(write_data, fobj)
        LOG.debug("Updated yaml file at %s", fpath)
    except FileNotFoundError as error:
        LOG.error(
            "%s", CTException(cterr.FILE_MISSING, error))
        return False, error
    return True, fpath


def create_content_json(path: str, data: object) -> str:
    """
    Function to create json file.

    :param path: json file path is to be created.
    :param data: Data to write in json file
    :return: path of the file.
    """
    with open(path, 'w') as outfile:
        json.dump(data, outfile, ensure_ascii=False)

    return path


def read_content_json(fpath: str) -> dict:
    """
    Function to read json file.

    :param fpath: Path of the json file
    :return: Data of the json file
    """
    with open(fpath, 'rb') as json_file:
        data = json.loads(json_file.read())

    return data


def parse_xml_controller(filepath: str, field_list: list, xml_tag: str =
                         "PROPERTY") -> tuple:
    """
    Function parses xml file and converts it into nested dictionary.

    :param filepath: File path of the xml file to be parsed
    :type: str
    :param field_list: List of the required fields
    :type: list of the strings
    :param xml_tag: Tag in the xml file
    :type: str
    :return: Nested dictionary having values of the fields
    mentioned in field list
    """
    try:
        elem_parse = parse(filepath).getroot()
        dict_data = {}
        new_d = {}
        list_keys = []
        i = 0

        fields = field_list
        for child in elem_parse.iter(xml_tag):
            dict_data['dict_{}'.format(i)] = {}
            for field in fields:
                if (child.attrib['name']) == field:
                    new_d[field] = child.text
                    list_keys.append('True')
                    dict_data['dict_{}'.format(i)] = new_d
            if list_keys.count('True') == len(fields):
                i += 1
                new_d = {}
                list_keys = []

        LOG.debug("Removing empty dictionaries")
        i = 0
        while True:
            if dict_data['dict_{}'.format(i)] == {}:
                del dict_data['dict_{}'.format(i)]
                break
            i += 1

        LOG.debug(dict_data)
        return True, dict_data
    except FileNotFoundError as error:
        LOG.error(
            "%s", CTException(cterr.FILE_MISSING, error))
        return False, error


def get_config(path: str, section: str = None, key: str = None) -> list or str:
    """
    Get config file value as per the section and key.

    :param path: File path
    :param section: Section name
    :param key: Section key name
    :return: key value else all items else None
    """
    try:
        config = ConfigParser()
        config.read(path)
        if section and key:
            # LOG.debug(config.get(section, key))
            return config.get(section, key)
        # LOG.debug(config.items(section))

        return config.items(section)
    except MissingSectionHeaderError:
        key_str = "{}=".format(key)
        with open(path, "r") as file_pointer:
            for line in file_pointer:
                if key_str in line and "#" not in line:
                    return line[len(key_str):].strip()
        return None


def update_config_ini(path: str, section: str, key: str, value: str) -> bool:
    """
    Update config file value as per the section and key.

    :param path: File path
    :param section: Section name
    :param key: Section key name
    :param value: new value
    :return: boolean
    """
    config = ConfigParser()
    config.read(path)
    try:
        try:
            config.set(section, key, value)
        except NoSectionError as error:
            LOG.warning(error)
            config.add_section(section)
            config.set(section, key, value)
        with open(path, "w") as configfile:
            config.write(configfile)
    except TypeError as error:
        LOG.error("%s", CTException(cterr.INVALID_OPTION_VALUE, error))
        return False
    return True


def update_config_helper(filename: str, key: str, old_value: str,
                         new_value: str, delimiter: str) -> tuple:
    """
    helper method for update_cfg_based_on_separator.

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
                            LOG.debug("old_pattern: %s", old_pattern)
                            LOG.debug("new_pattern: %s", new_pattern)
                        else:
                            old_pattern = key + "=" + old_value
                            new_pattern = key + "=" + new_value
                        if len(ol_value) > len(nw_value):
                            new_pattern = new_pattern + " " * (len(ol_value) - len(nw_value))
                        match = re.search(old_pattern, data)
                        if match:
                            span_ = match.span()
                            f_in.seek(span_[0])
                            f_in.write(new_pattern)
                            LOG.debug(
                                "Old pattern %s got replaced by "
                                "new pattern %s", old_pattern, new_pattern)
                            f_in.seek(0, 0)
                            new_data = f_in.read()
                            return True, new_data

    return False, "Failed to replace Old pattern {} with new pattern {}".format(
        old_value, new_value)


def update_cfg_based_on_separator(filename: str, key: str, old_value: str,
                                  new_value: str) -> tuple:
    """
    Editing a file provided with : or = separator.

    :param filename: file to update
    :param key: key in file
    :param old_value: old value of key
    :param new_value: new value of key
    :return: bool
    """
    try:
        status, resp = False, None
        with open(filename, 'r+') as f_in:
            for line in f_in.readlines():
                if "=" in line and key in line:
                    status, resp = update_config_helper(
                        filename, key, old_value, new_value, "=")
                elif ":" in line and key in line:
                    status, resp = update_config_helper(
                        filename, key, old_value, new_value, ":")
        return status, resp
    except AttributeError as error:
        LOG.debug(
            'Old value : %s is incorrect, please correct it and try again',
            old_value)
        return False, error
    except IOError as error:
        os.remove(filename)
        os.rename(filename + '_bkp', filename)
        LOG.debug(
            "Removed original corrupted file and Backup file has been restored")
        LOG.debug(
            "*ERROR* An exception occurred in upload_config : %s", error)

        return False, error


def read_write_config(config: str or int, path: str) -> None:
    """
    read and update values from source_file to destination config.

    :param config: key from source_file
    :param path: path of destination config
    :type path: str
    :return: None
    """
    LOG.debug("Reading and updating : %s at %s", config, path)
    conf_values = read_yaml(MAIN_CONFIG_PATH)[1]
    LOG.debug("VALUES TO UPDATE: %s", conf_values[config])
    dict_val = conf_values[config]
    keys = dict_val.keys()
    LOG.debug(keys)
    curr_values = read_yaml(path)[1]
    LOG.debug("OLD CONFIG : %s", curr_values)
    for key in keys:
        if key in curr_values:
            try:
                for i_key in dict_val[key].keys():
                    if i_key in curr_values[key]:
                        LOG.debug("Replacing inner_key : %s", i_key)
                        LOG.debug("Old value : %s", curr_values[key][i_key])
                        curr_values[key][i_key] = dict_val[key][i_key]
                        LOG.debug(
                            "New value : %s", dict_val[key][i_key])
            except IOError as error:
                LOG.debug("Replacing key : %s", key)
                LOG.debug("Old value : %s", curr_values[key])
                curr_values[key] = dict_val[key]
                LOG.debug("New value : %s", dict_val[key])
                LOG.error(
                    "*ERROR* An exception occurred in upload_config : %s", error)

    write_yaml(path, curr_values, backup=False)
    updated_values = read_yaml(path)
    LOG.debug("UPDATED CONFIG : %s", updated_values)


def update_configs(all_configs: dict) -> None:
    """
    Update all configs mentioned in ALL_CONFIGS with values of MAIN_CONFIG_PATH.

    :param all_configs: Dictionary of paths of all config files
    :type all_configs: dict
    """
    for conf in all_configs.keys():
        read_write_config(conf, all_configs[conf])

def verify_json_schema(self, instance, *schemas):
    """
    Verify the schema for the given instance of the response
    exception is raised if the schema doesn't match 
    which can be handled by calling function
    :param instance: json log instance which needs to be verified.
    :param schemas: json schema for verification
    """

    for schema in schemas:
        validate(instance=instance, schema=schema)
