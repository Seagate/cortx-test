""" Layouts for Query tab in Query QA tab ."""
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


import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from Common_callbacks import query_tab_callbacks as qtc

test_results_options = [
    {'label': '  PASS  ', 'value': 'PASS'},
    {'label': '  FAIL  ', 'value': 'FAIL'},
    {'label': '  BLOCKED  ', 'value': 'BLOCKED'},
    {'label': '  ABORTED  ', 'value': 'ABORTED'},
]

# TAB 4 Query DB
query_input_style = {'width': '200px', 'margin-right': '15px', 'margin-top': '10px'}

first_row = dbc.Row([
    dcc.Dropdown(
        id="query_branch",
        placeholder="Branch Name",
        style=query_input_style,
        multi=True,
        options=qtc.get_distinct_field_values("buildType")
    ),

    dcc.Dropdown(
        id='query_build',
        placeholder="Build Number",
        style=query_input_style,
        multi=True,
        options=qtc.get_distinct_field_values("buildNo")
    ),

    dcc.Dropdown(
        id='query_system_type',
        placeholder="System type",
        style=query_input_style,
        multi=True,
        options=qtc.get_distinct_field_values("testPlanLabel")
    ),
    dcc.Dropdown(
        id='query_feature',
        placeholder="Feature",
        style=query_input_style,
        multi=True,
        options=qtc.get_distinct_field_values("feature")
    ),
],
    justify='center',
)
second_row = dbc.Row([
    dcc.Dropdown(
        id='query_test_plan',
        placeholder="Test Plan",
        style=query_input_style,
        multi=True,
        options=qtc.get_distinct_field_values("testPlanID")
    ),
    dcc.Dropdown(
        id='query_test_execution',
        placeholder="Test Execution",
        style=query_input_style,
        multi=True,
        options=qtc.get_distinct_field_values("testExecutionID")
    ),
    dcc.Dropdown(
        id='query_test_id',
        placeholder="Test ID",
        style=query_input_style,
        multi=True,
        options=qtc.get_distinct_field_values("testID")
    ),
    dcc.Dropdown(
        id='query_execution_type',
        placeholder="Execution Type",
        style=query_input_style,
        multi=True,
        options=qtc.get_distinct_field_values("executionType")
    ),
],
    justify='center',
)
third_row = dbc.Row(
    [
        dcc.Checklist(
            id='query_test_results',
            options=test_results_options,
            style={'display': 'inline'},
            labelStyle={'font-size': '20px', 'display': 'inline'}
        ),
    ],
    justify='center',
)
forth_row = dbc.Row(
    [
        dbc.RadioItems(id='query_table_view',
                       options=[
                           {'label': 'Brief View', 'value': 'brief'},
                           {'label': 'Detail View', 'value': 'detail'}
                       ],
                       value='brief',
                       labelStyle={'display': 'inline'},
                       style={'margin-top': '20px', 'margin-right': '30px'}),
        dbc.Button("Get Results!", id="query_result_button", color="success",
                   style={'height': '36px', 'margin-top': '20px'}),
    ],
    justify='center',
)

query_database = dbc.Card(
    dbc.CardBody(
        [
            html.Div(first_row),
            html.Br(),
            html.Div(second_row),
            html.Br(),
            html.Div(third_row),
            html.Br(),
            html.Div(forth_row),
            html.Br(),
            html.Div(id="table_query_result_count", className='text-center',
                        style={'color': '#001a33', 'margin': 20, 'font-size': 18}),
            dcc.Loading(html.Div(id="table_query_result"))
        ]
    )
)
