"""Common file for dash callbacks."""
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# 
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
# -*- coding: utf-8 -*-
# !/usr/bin/python

import configparser
import json
import sys
from http import HTTPStatus

import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
import pandas as pd
import requests
from jira import JIRA

external_stylesheets = [
    dbc.themes.COSMO,
    dbc.themes.BOOTSTRAP,
    ] # 'https://use.fontawesome.com/releases/v5.8.1/css/all.css'
app = dash.Dash(__name__, external_stylesheets=external_stylesheets,
                prevent_initial_callbacks=True, suppress_callback_exceptions=True)

app.title = "CORTX Companion"
server = app.server
__version__ = "5.27"

DEBUG_PRINTS = False

# database Details
config = configparser.ConfigParser()
config.read('config.ini')
try:
    search_endpoint = config["REST"]["search_endpoint"]
    distinct_endpoint = config["REST"]["distinct_endpoint"]
    timing_endpoint = config["REST"]["timing_endpoint"]
    aggregate_endpoint = config["REST"]["aggregate_endpoint"]
    count_endpoint = config["REST"]["count_endpoint"]
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
    {'label': 'LR-R1', 'value': 'LR1'},
    {'label': 'LR-R2', 'value': 'LR2'}
]

# common style
dict_style_table_caption = {'font-size': '20px', 'font-weight': 'bold', 'color': '#3131b0',
                            'margin-top': '18px', 'margin-bottom': '5px', 'font-family': 'Serif'}
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


def get_data_to_html_rows(data, col_names, row_span_text, no_of_rows_to_span):
    """
    Generate hmtl rows of the given data
    As row span feature is not supported in datatable,
    :param data: list of list(row)
    :param row_span_text:text to spanned across no of rows
    :param no_of_rows_to_span:
    :return:
    """
    rows = []
    for i in enumerate(data):
        row = []
        if i == 0:
            row.append(html.Td(row_span_text, rowSpan=no_of_rows_to_span))
        for col_no in range(len(col_names)):
            value = data[i][col_no]
            row.append(html.Td(children=value))
        rows.append(html.Tr(row))
    return rows


def get_df_to_rows(dataframe, row_span_text, no_of_rows_to_span):
    """
    Generate hmtl rows of the given dataframe
    As row span feature is not supported in datatable,
    added different dataframe for each subcomponent(sharing the same row)
    :param dataframe: Dataframe
    :param row_span_text:text to spanned across no of rows
    :param no_of_rows_to_span:
    :return:
    """
    rows = []
    for i in range(len(dataframe)):
        row = []
        if i == 0:
            row.append(html.Td(row_span_text, rowSpan=no_of_rows_to_span))
        for col in dataframe.columns:
            value = dataframe.iloc[i][col]
            row.append(html.Td(children=value))
        rows.append(html.Tr(row))
    return rows


def r2_get_previous_builds(branch, build_no, no_of_prev_builds=1):
    query_input = {
        "aggregate": [{"$group": {"_id": {"buildNo": "$buildNo", "buildType": "$buildType"},

                                  "testStartTime": {"$min": "$testStartTime"}}},
                      {"$sort": {"testStartTime": 1}}]}
    if DEBUG_PRINTS:
        print("r2_get_previous_builds query :{}".format(query_input))
    query_input.update(credentials)
    response = requests.request("GET", aggregate_endpoint, headers=headers,
                                data=json.dumps(query_input))
    build_list = []
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        for each in json_response["result"]:
            if each["_id"]["buildType"] == branch:
                build_list.append(each["_id"]["buildNo"])
        if build_no in build_list:
            index = build_list.index(build_no)
            if no_of_prev_builds > index:
                prev_list = build_list[:index]
            else:
                prev_list = build_list[index - no_of_prev_builds:index]
        else:
            prev_list = []

    else:
        print("r2_get_previous_builds error code :{}".format(response.status_code))
    return prev_list


def add_link(row):
    temp = "https://jts.seagate.com/browse/" + row
    l = "[{0}]({1})".format(row, temp)
    return l


def get_testplan_ID(query):
    temp_query = {"query": query, "field": "testPlanID"}
    # print(f"get_testplan_ID : {query}")
    temp_query.update(credentials)
    response = requests.request("GET", distinct_endpoint, headers=headers,
                                data=json.dumps(temp_query))
    if response.status_code == HTTPStatus.OK:
        json_response = json.loads(response.text)
        tps = json_response["result"]
        tps.sort(reverse=True)
        if len(tps):
            return tps[0]
    return None
