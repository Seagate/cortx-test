""" Main file for the Dashboard server."""
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

import os
import qa_tab_layouts as tl
import query_tab_layout as query_tl
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import flask
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from common import app, versions, server
from Common_callbacks import defect_list_tab_callbacks, \
    main_page_callbacks, query_tab_callbacks  # pylint: disable=unused-import
from R1_callbacks import r1_exe_report_callbacks, \
    r1_engg_report_callbacks  # pylint: disable=unused-import
from R2_callbacks import exe_report_callbacks, \
    engg_report_callbacks  # pylint: disable=unused-import

from Performance.statistics import stats_dropdown_callbacks, statistics_callbacks  # pylint: disable=unused-import
from Performance.graphs import graphs_dropdown_callbacks, graphs_callbacks  # pylint: disable=unused-import
from Performance.perf_main import perf_stats_page, perf_graphs_page


@server.route('/favicon.ico')
def favicon():
    """
    Seagate logo used as icon that appears at top of browser tab
    """
    return flask.send_from_directory(os.path.join(server.root_path, 'static'), 'favicon.ico')


input_options = dbc.Row(
    [
        dcc.Dropdown(
            id="version_dropdown",
            options=versions,
            placeholder="Select Version",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px",
                   "margin-top": "10px"},
        ),

        dcc.Dropdown(
            id="branch_dropdown",
            placeholder="Select Branch",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px",
                   "margin-top": "10px"},
        ),

        dcc.Dropdown(
            id='build_no_dropdown',
            placeholder="Select Build",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px",
                   "margin-top": "10px"},
        ),
        dcc.Dropdown(
            id='test_system_dropdown',
            placeholder="Test System Type",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px",
                   "margin-top": "10px"},
        ),

        dbc.Button("Get!", id="submit_button", n_clicks=0, color="success",
                   style={'height': '36px', 'margin-top': '20px'}),
    ],
    justify='center'
)
input_optional_options = dbc.Row(
    [
        dcc.Dropdown(
            id='test_team_dropdown',
            placeholder="Test Component(Opt)",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px",
                   "margin-top": "10px"},
        ),
        dcc.Dropdown(
            id='test_plan_dropdown',
            placeholder="Test Plan No (Opt)",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px",
                   "margin-top": "10px"},
        )
    ],
    justify='center',
    id="toggle_visibility"
)

# ---Overall layout-------------------------------------------------------------------
dict_style_tab = {'margin-left': 10, 'margin-right': 10}
dict_style_label = {'font-size': '22px', 'color': '#44cc00', 'background-color': '#343a40',
                    'border-style': 'solid', 'border-color': '#ffffff', 'font-family': 'Serif'}

dict_style_sub_tab = {'margin-left': 10,
                      'margin-right': 10, 'margin-top': '10px'}
dict_style_sub_label = {'font-size': '18px', 'color': '#44cc00', 'background-color': '#343a40',
                        'border-style': 'solid', 'margin-top': '20px'}

dict_active_tab_labels = {'background-color': '#81DD59', 'color': '#000000'}


@app.callback(
    Output('exec_report_content', 'children'),
    [Input('version_dropdown', 'value')],
)
def fetch_exec_report(value):
    """
    Fetch executive report based on product version
    :param value:
    :return:
    """
    if not value:
        raise PreventUpdate
    if value == "LR1":
        content = tl.r1_exec_report_content
    else:
        content = tl.r2_exec_report_content
    return content


@app.callback(
    Output('engg_report_content', 'children'),
    [Input('version_dropdown', 'value')],
)
def fetch_engg_report(value):
    """
    Fetch engineering report based on product version
    :param value:
    :return:
    """
    if not value:
        raise PreventUpdate
    if value == "LR1":
        content = tl.r1_engg_report_content
    else:
        content = tl.r2_engg_report_content
    return content


qa_tabs = dbc.Tabs(
    [
        dbc.Tab(id="exec_report_content", label="Executive's Report", style=dict_style_sub_tab,
                label_style=dict_style_sub_label),
        dbc.Tab(id="engg_report_content", label="Engineer's Report", style=dict_style_sub_tab,
                label_style=dict_style_sub_label)
    ],
    className="nav nav nav-pills nav-fill nav-pills flex-column flex-sm-row",
    id="tabs",
)

qa_page = html.Div(
    [
        html.Div(input_options),
        html.Div(input_optional_options),
        html.Div(qa_tabs)
    ]
)

query_tabs = dbc.Tabs(
    [
        dbc.Tab(query_tl.query_database, label='Query Database', style=dict_style_sub_tab,
                label_style=dict_style_sub_label, tab_id="tab_query_db"),
        dbc.Tab(tl.defect_list_per_tp_content, label='Defect List for Test Plans/Test Executions',
                style=dict_style_sub_tab,
                label_style=dict_style_sub_label, tab_id="tab_query_tp")

    ],
    className="nav nav nav-pills nav-fill nav-pills flex-column flex-sm-row",
    id="query_tabs",
)
query_page = html.Div(query_tabs)

main_tabs = dbc.Tabs(
    [
        dbc.Tab(qa_page, label="QA  Reports", style=dict_style_tab, label_style=dict_style_label,
                active_label_style=dict_active_tab_labels),
        dbc.Tab(query_page, label="Query  QA  Data ", style=dict_style_tab,
                label_style=dict_style_label,
                active_label_style=dict_active_tab_labels),
        dbc.Tab(perf_stats_page, label="Performance Statistics", style=dict_style_tab,
                label_style=dict_style_label,
                active_label_style=dict_active_tab_labels),
        dbc.Tab(perf_graphs_page, label="Performance Trends", style=dict_style_tab,
                label_style=dict_style_label,
                active_label_style=dict_active_tab_labels),
    ],
    className="nav nav nav-pills nav-fill nav-pills flex-column flex-sm-row",
    id="main_tabs",
)

cortx_sharepoint = "https://seagatetechnology.sharepoint.com/sites/gteamdrv1/tdrive1224"
cft_sharepoint = "https://seagate-systems.atlassian.net/wiki/spaces/CFT/overview"
navbar = dbc.Navbar(
    [
        html.A(
            dbc.Row(
                [
                    dbc.Col(html.Img(src=app.get_asset_url(
                        "seagate.png"), height="100px")),
                    dbc.Col(dbc.NavbarBrand("CORTX Companion",
                                            style={'font-size': 40, 'textAlign': 'center',
                                                   'width': '800px'}),
                            className='my-auto'),
                    dbc.Col(dbc.Button("Cortx Sharepoint", color="light", size="lg",
                                       outline=True,
                                       href=cortx_sharepoint,
                                       target="_blank",
                                       ),
                            width="auto", className="my-auto"),
                    dbc.Col(dbc.Button("CFT Confluence", color="light", size="lg",
                                       outline=True,
                                       href=cft_sharepoint,
                                       target="_blank"),
                            width="auto", className="my-auto ")
                ],
                # no_gutters=True,
            ),
        ),
    ],
    color="dark",
    dark=True,
)

app.layout = html.Div([
    navbar,
    main_tabs,
    dcc.Location(id='url', refresh=False),
    dbc.Alert(
        "Looks good at 80% page zoom level!",
        id="alert-auto",
        is_open=True,
        dismissable=True,
        color="info",
        style={
            'width': '350px',
            'position': 'absolute',
            'top': 10,
            'right': 0,
            'margin-bottom': '10px',
            'height': '40px'
        }
    ),
    html.Link(
        rel='stylesheet',
        href='/static/topography.css'
    )])

if __name__ == '__main__':
    app.run_server(port=5002, threaded=True, debug=True)
    # app.run_server(port=5002, threaded=True)
