"""Common file for dash callbacks."""
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
# -*- coding: utf-8 -*-
# !/usr/bin/python

import sys
import configparser
import dash
import dash_bootstrap_components as dbc
from jira import JIRA
import pandas as pd

external_stylesheets = [dbc.themes.COSMO]
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                prevent_initial_callbacks=True, suppress_callback_exceptions=True)

app.title = "CORTX Test Status"
server = app.server
__version__ = "5.27"

DEBUG_PRINTS = True

# database Details
config = configparser.ConfigParser()
config.read('config.ini')
try:
    search_endpoint = config["REST"]["search_endpoint"]
    distinct_endpoint = config["REST"]["distinct_endpoint"]

    headers = {
        'Content-Type': 'application/json'
    }

    credentials = {"db_username": config["REST"]["db_username"],
                   "db_password": config["REST"]["db_password"]}
    jira_username = config["JIRA"]["jira_username"]
    jira_password = config["JIRA"]["jira_password"]
except KeyError:
    print("Not able to read the details from config.ini file")
    sys.exit(1)

versions = [
    {'label': 'LR1', 'value': 'LR1'},
    {'label': 'LR2', 'value': 'LR2'}
]

# common style
dict_style_table_caption = {'font-size': '20px', 'font-weight': 'bold', 'color': '#3131b0',
                            'margin-top': '18px', 'margin-bottom': '5px'}
dict_style_header = {'backgroundColor': '#7F8C8D', 'textAlign': 'center', 'font-size': '18px',
                     'fontWeight': 'bold',
                     'border': '1px solid black'}
dict_style_cell = {'textAlign': 'center', 'border': '1px solid black', 'fontWeight': 'bold',
                   'font-size': '15px'}


def get_issue_details(issue_list):
    """
    Query Jira and provide all the detailed info of the issue in issue_list
    :param issue_list: List of the Jira ID
    :return: Dataframe containing Priority,Component,Name and Issue id of issues provided in input
    """
    issue_list = list(set(issue_list))
    print("Unique list in get_issue_details : ", issue_list)
    jira_cred = JIRA({'server': "https://jts.seagate.com/"},
                     basic_auth=(jira_username, jira_password))
    issue_priority_list = []
    issue_component_list = []
    issue_name_list = []
    issue_no_list = []

    # check issue type and priority
    for issue in issue_list:
        issue_details = jira_cred.issue(issue)
        issue_priority_list.append(issue_details.fields.priority.name)
        issue_component_list.append(issue_details.fields.components[0].name)
        issue_name_list.append(issue_details.fields.summary)
        issue_no_list.append(issue)

    overall_details = {
        "issue_no": issue_no_list,
        "issue_comp": issue_component_list,
        "issue_name": issue_name_list,
        "issue_priority": issue_priority_list
    }
    res_dataframe = pd.DataFrame(overall_details)
    return res_dataframe
