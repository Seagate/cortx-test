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

# External modules import
from dash_bootstrap_components import Card, CardBody, Row, Button, Tab
from dash_core_components import Dropdown, Graph
import dash_html_components as html
import dash_daq as daq

from Performance.styles import dict_style_sub_tab, dict_style_sub_label, dict_style_dropdown_medium, dict_dropdown_normal_Style

# Variable declarations
Xfilter = [
    {'label': 'Object Size', 'value': 'Object_Size'},
    {'label': 'Build', 'value': 'Build'},
]

benchmarks = [
    {'label': 'S3Bench', 'value': 'S3bench'},
    {'label': 'COSBench', 'value': 'Cosbench'},
    {'label': 'HSBench', 'value': 'Hsbench'},
]

operations = [
    {'label': 'Read & Write', 'value': 'both'},
    {'label': 'Read', 'value': 'read'},
    {'label': 'Write', 'value': 'write'},
]

release = [
    {'label': 'LR-R1', 'value': '1'},
    {'label': 'LR-R2', 'value': '2'}
]

# set of compulsary input options
first_input_set = Row([
    Dropdown(
        id="filter_dropdown",
        options=Xfilter,
        placeholder="Filter by",
        style=dict_style_dropdown_medium
    ),
    Dropdown(
        id="release_dropdown_first",
        options=release,
        placeholder="Select Release",
        style=dict_dropdown_normal_Style
    ),
    Dropdown(
        id="branch_dropdown_first",
        placeholder="Select Branch",
        style=dict_dropdown_normal_Style
    ),
    Dropdown(
        id='dropdown_first',
        placeholder="Build/object Size",
        style=dict_dropdown_normal_Style
    ),
    Dropdown(
        id='profiles_options_first',
        placeholder="Select Profile",
        style={'display': 'none'}
    ),
    Dropdown(
        id="benchmark_dropdown_first",
        options=benchmarks,
        placeholder="Benchmark",
        # value='S3bench',
        style=dict_style_dropdown_medium
    ),
    Dropdown(
        id='configs_dropdown_first',
        placeholder="Choose configurations",
        style={'display': 'none'}
    ),
    Dropdown(
        id="operations_dropdown_first",
        options=operations,
        placeholder="Operation",
        value='both',
        style=dict_style_dropdown_medium
    ),
    daq.ToggleSwitch(
        id="compare_flag",
        label="Compare",
        labelPosition="bottom",
        style={'color': '#FFFFFF', 'margin-top': '15px'}
    )
],
    justify='center'
)

# set of non-mandatory input options
second_input_set = Row([
    Dropdown(
        id="release_dropdown_second",
        options=release,
        placeholder="Select Release",
        style={'display': 'none'}
    ),
    Dropdown(
        id="branch_dropdown_second",
        placeholder="Select Branch",
        style={'display': 'none'}
    ),
    Dropdown(
        id='dropdown_second',
        placeholder="Select Build",
        style={'display': 'none'}
    ),
    Dropdown(
        id='profiles_options_second',
        placeholder="Select Profile",
        style={'display': 'none'}
    ),
    Button("Get!", id="get_graphs", color="success",
           style={'height': '35px', 'margin-top': '20px'}),
],
    justify='center', style={'margin-bottom': '20px'}
)

# graph layouts function
graphs_layout = Card(
    CardBody(
        [
            html.P(html.U("Graphical Representation of Performance Data", id="graphs_headings"),
                   style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),
            html.P("Note: Each data point represents PER NODE data. Data is displayed for the builds on which PerfPro has run.",  style={
                   "font-weight": "bold", 'font-size': '20px', 'color': '#D00000'}),

            Graph(id='plot_Throughput'),
            Graph(id='plot_Latency'),
            Graph(id='plot_IOPS'),
            Graph(id='plot_TTFB'),
            Graph(id='plot_all'),
        ]
    ),
    className="flex-sm-fill nav-link"
)

graphs_perf_tabs = html.Div(
    Tab(graphs_layout, id="perf_graphs_content", label="Performance Graphs",
        style=dict_style_sub_tab, label_style=dict_style_sub_label
        )
)
