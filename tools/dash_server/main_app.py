""" Main file for the Dashboard server."""
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

import os
import tab_layouts as tl
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import flask
from common import app, versions, server
from callbacks import defect_list_tab_callbacks, exe_report_callbacks
from callbacks import exe_report_callbacks


@server.route('/favicon.ico')
def favicon():
    """
    Seagate logo used as icon that appears at top of browser tab
    """
    return flask.send_from_directory(os.path.join(server.root_path, 'static'), 'favicon.ico')


toast = html.Div(
    [
        dbc.Toast(
            "Please verify and enter correct build number.No Data found this build number.",
            id="positioned-toast",
            header="Wrong build number",
            is_open=False,
            dismissable=True,
            icon="danger",
            duration=6000,
            # top: 66 positions the toast below the navbar
            style={"position": "fixed", "top": 25, "right": 10, "width": 350},
        ),
    ]
)
# two buttons on top right
search_bar = dbc.Row(
    [
        dbc.Col
            ([
            dbc.Button("Cortx Sharepoint", color="light", size="lg", className="mr-1", outline=True,
                       href="https://seagatetechnology.sharepoint.com/sites/gteamdrv1/tdrive1224",
                       target="_blank"),
            dbc.Button("CFT Sharepoint", color="light", size="lg", className="mr-1", outline=True,
                       href="https://seagatetechnology.sharepoint.com/:f:/r/sites/gteamdrv1/tdri"
                            "ve1224/Shared%20Documents/CFT_IntegrationTeam?csf=1&web=1&e=9Wgzsx",
                       target="_blank")],
            width="auto",
        ),
    ],
    no_gutters=True,
    className="ml-auto flex-nowrap mt-3 mt-md-0",
    align="center",
)

navbar = dbc.Navbar(
    [
        html.A(
            dbc.Row([
                dbc.Col(html.Img(src=app.get_asset_url(
                    "seagate.png"), height="100px")),
                dbc.Col(dbc.NavbarBrand("CORTX CFT Dashboard",
                                        style={'font-size': 40, }), className="align-self-center"),
                dbc.Col(dbc.Button("Cortx Sharepoint", color="light", size="lg", className="mr-1",
                                   outline=True,
                                   href="https://seagatetechnology.sharepoint.com/sites/gteamdrv1/"
                                        "tdrive1224",
                                   target="_blank"),
                        width="auto", className="justify-content-end"),
                dbc.Col(dbc.Button("CFT Sharepoint", color="light", size="lg", className="mr-1",
                                   outline=True,
                                   href="https://seagatetechnology.sharepoint.com/:f:/r/sites/"
                                        "gteamdrv1/tdrive1224/Shared%20Documents/"
                                        "CFT_IntegrationTeam?csf=1&web=1&e=9Wgzsx",
                                   target="_blank"),
                        width="auto", className="justify-content-end")
            ],
                no_gutters=True,

            ),
        ),
    ],
    color="dark",
    dark=True,
)
build_report_header = dbc.Jumbotron(html.H4(html.Em("... looking for build number!")),
                                    id="build_report_header",
                                    style={'padding': '1em',
                                           'background': 'transparent', 'text-align': 'center'})
input_options = dbc.Row(
    [
        dcc.Dropdown(
            id="version_dropdown",
            options=versions,
            placeholder="select version",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px"},
        ),

        dcc.Dropdown(
            id='build_no_dropdown',
            placeholder="select build",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px"},
        ),

        dbc.Button("Get!", id="submit_button", n_clicks=0, color="success",
                   style={'height': '35px'}),
    ],
    justify='center'
)
input_optional_options = dbc.Row(
    [
        dcc.Dropdown(
            id='test_system_dropdown',
            placeholder="Test System Type",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px"},
        ),

        dcc.Dropdown(
            id='test_team_dropdown',
            placeholder="Select test component(Optional)",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px"},
        ),
    ],
    justify='center',
    style={"margin-top": "18px"}
)

# ---Overall layout-------------------------------------------------------------------
dict_style_tab = {'margin-left': 20, 'margin-right': 20}
dict_style_label = {'font-size': '18px', 'color': '#44cc00', 'background-color': '#343a40'}

tabs = dbc.Tabs(
    [
        dbc.Tab(tl.exec_report_content, label="Executive Report", style=dict_style_tab,
                label_style=dict_style_label),
        dbc.Tab(tl.engg_report_content, label="Engineers Report", style=dict_style_tab,
                label_style=dict_style_label),
        dbc.Tab(tl.defect_list_per_tp_content, label='Defect List for Test Execution Plans',
                style=dict_style_tab,
                label_style=dict_style_label),
        dbc.Tab(tl.performance_content, label='Performance', style=dict_style_tab,
                label_style=dict_style_label),
        dbc.Tab(tl.query_database, label='Query Database', style=dict_style_tab,
                label_style=dict_style_label),
    ],
    className="nav nav nav-pills nav-fill nav-pills flex-column flex-sm-row",
    id="tabs",
)

app.layout = html.Div([
    navbar,
    input_options,
    input_optional_options,
    build_report_header,
    tabs,
    dcc.Location(id='url', refresh=False),
    toast,
    html.Link(
        rel='stylesheet',
        href='/static/topography.css'
    )])

if __name__ == '__main__':
    app.run_server(port=5002, threaded=True, debug=True)
