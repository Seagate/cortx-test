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

from dash_bootstrap_components import Card, CardBody, Row, Button, Tab
from dash_core_components import Dropdown, Graph
import dash_html_components as html
from Performance.styles import dict_style_sub_tab, dict_style_sub_label, dict_style_dropdown_medium

versions = [
    {'label': 'Cortx-1.0-Beta', 'value': 'beta'},
    {'label': 'Cortx-1.0', 'value': 'cortx1'},
    {'label': 'Custom', 'value': 'custom'},
    {'label': 'Main', 'value': 'main', 'disabled': True},
    {'label': 'Release', 'value': 'release'},
]

Xfilter = [
    {'label': 'Object Size', 'value': 'Object Size'},
    {'label': 'Build', 'value': 'build'},
]

benchmarks = [
    {'label': 'S3Bench', 'value': 'S3bench'},
    {'label': 'COSBench', 'value': 'Cosbench'},
    {'label': 'HSBench', 'value': 'Hsbench'},
]

config_list = [
    {'label': '100 Sessions, 1 Bucket, 1000 Objects', 'value': '1'},
    {'label': '100 Sessions, 10 Buckets, 100 Objects', 'value': '2'},
    {'label': '100 Sessions, 50 Buckets, 100 Objects', 'value': '3'}
]

operations = [
    {'label': 'Both', 'value': 'both'},
    {'label': 'Read', 'value': 'read'},
    {'label': 'Write', 'value': 'write'},
]

graphs_input_options = Row([
    Dropdown(
        id="graphs_version_dropdown",
        options=versions,
        placeholder="Branch / Version",
        style=dict_style_dropdown_medium
    ),
    Dropdown(
        id="filter_dropdown",
        options=Xfilter,
        placeholder="Filter by",
        style=dict_style_dropdown_medium
    ),
    Dropdown(
        id='configs_dropdown',
        options=config_list,
        placeholder="Choose configurations",
        style={'display': 'none'}
    ),
    Dropdown(
        id='option1_dropdown',
        placeholder="first choice",
        style=dict_style_dropdown_medium
    ),
    Dropdown(
        id='option2_dropdown',
        placeholder="Compare with",
        style={'display': 'none'}
    ),
    Dropdown(
        id="benchmark_dropdown",
        options=benchmarks,
        placeholder="Benchmark",
        value='S3bench',
        style=dict_style_dropdown_medium
    ),
    Dropdown(
        id="operations_dropdown",
        options=operations,
        placeholder="Operation",
        value='both',
        style=dict_style_dropdown_medium
    ),
    Button("Get!", id="get_graph_button", color="success",
           style={'height': '35px', "margin-right": "40px", "margin-top": "10px"}),
],
    justify='center', style={'padding': '10px'}
)

graphs_layout = Card(
    CardBody(
        [
            html.P(html.U("Graphical Representation of Performance Data", id="graphs_headings"),
                   style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),

            Graph(id='plot_Throughput'),
            Graph(id='plot_Latency'),
            Graph(id='plot_IOPS'),
            Graph(id='plot_TTFB'),
            Graph(id='plot_all'),

            html.P('Statistics are displayed only for the builds on which Performance test suite has ran.',
                   className="card-text", style={'margin-top': '10px'})
        ]
    ),
    className="flex-sm-fill nav-link"
)

graphs_perf_tabs = html.Div(
    Tab(graphs_layout, id="perf_graphs_content", label="Performance Graphs",
        style=dict_style_sub_tab, label_style=dict_style_sub_label
        )
)
