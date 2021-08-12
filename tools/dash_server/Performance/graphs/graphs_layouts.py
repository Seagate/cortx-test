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

from Performance.styles import style_sub_tab, style_sub_label,\
        style_dropdown_small, style_dropdown_small_2, \
        style_dropdown_medium, style_dropdown_large, dict_button_style, dict_Style_Stats_input_options

# Variable declarations
Xfilter = [
    {'label': 'Object Size', 'value': 'Object_Size'},
    {'label': 'Build', 'value': 'Build'},
]

release = [
    {'label': 'LR-R1', 'value': '1'},
    {'label': 'LR-R2', 'value': '2'}
]

benchmarks = [ # get from database
    {'label': 'S3Bench', 'value': 'S3bench'},
    {'label': 'COSBench', 'value': 'Cosbench'},
    {'label': 'HSBench', 'value': 'Hsbench'},
]

operations = [ # write a function for this
    {'label': 'Read & Write', 'value': 'both'},
    {'label': 'Read', 'value': 'read'},
    {'label': 'Write', 'value': 'write'},
]


graphs_input_options = [
    Row(
        [
            Dropdown(
                id="graphs_filter_dropdown",
                options=Xfilter,
                placeholder="Filter by",
                style= style_dropdown_small
            ),
            Dropdown(
                id="graphs_benchmark_dropdown",
                options=benchmarks,
                placeholder="Benchmark",
                style=style_dropdown_small_2
            ),
            Dropdown(
                id="graphs_operations_dropdown",
                options=operations,
                placeholder="Operation",
                value='both',
                style=style_dropdown_medium
            ),
        ],
        justify='center'
    ),
    Row(
        [
            Dropdown(
                id="graphs_release_dropdown",
                options=release,
                placeholder="Release",
                style=style_dropdown_small
            ),
            Dropdown(
                id="graphs_branch_dropdown",
                placeholder="Branch",
                style=style_dropdown_small_2
            ),
            Dropdown(
                id='graphs_build_dropdown',
                placeholder="Build/Object Size",
                style=style_dropdown_medium
            ),
            Dropdown(
                id='graphs_nodes_dropdown',
                placeholder="Nodes",
                style=style_dropdown_small
            ),
            Dropdown(
                id='graphs_pfull_dropdown',
                placeholder="Cluster % Fill",
                style=style_dropdown_small_2
            ),
            Dropdown(
                id='graphs_iteration_dropdown',
                placeholder="Iterations",
                style=style_dropdown_small_2
            ),
            Dropdown(
                id='graphs_custom_dropdown',
                placeholder="Select Tag",
                style=style_dropdown_medium
            ),
            Dropdown(
                id='graphs_sessions_dropdown',
                placeholder="Sessions",
                style=style_dropdown_medium
            ),
            Dropdown(
                id='graphs_buckets_dropdown',
                placeholder="Buckets",
                style=style_dropdown_medium
            ),
        ],
        justify='center'
    ),
    Row(
        [
            daq.ToggleSwitch(
                id="compare_flag",
                label="Compare",
                labelPosition="bottom",
                style={'color': '#FFFFFF', 'margin-top': '15px', 'margin-right': '10px'}
            ),
            Dropdown(
                id="graphs_release_compare_dropdown",
                options=release,
                placeholder="Release",
                style={'display': 'none'},
            ),
            Dropdown(
                id="graphs_branch_compare_dropdown",
                placeholder="Branch",
                style={'display': 'none'}
            ),
            Dropdown(
                id='graphs_build_compare_dropdown',
                placeholder="Build/Object Size",
                style={'display': 'none'}
            ),
            Dropdown(
                id='graphs_nodes_compare_dropdown',
                placeholder="Nodes",
                style={'display': 'none'}
            ),
            Dropdown(
                id='graphs_pfull_compare_dropdown',
                placeholder="Cluster % Fill",
                style={'display': 'none'}
            ),
            Dropdown(
                id='graphs_iteration_compare_dropdown',
                placeholder="Iterations",
                style={'display': 'none'}
            ),
            Dropdown(
                id='graphs_custom_compare_dropdown',
                placeholder="Select Tag",
                style={'display': 'none'}
            ),
            Dropdown(
                id='graphs_sessions_compare_dropdown',
                placeholder="Sessions",
                style={'display': 'none'}
            ),
            Dropdown(
                id='graphs_buckets_compare_dropdown',
                placeholder="Buckets",
                style={'display': 'none'}
            ),
            Button("Show", id="graphs_submit_button", n_clicks=0, color="success",
                style=dict_button_style),
        ],
        justify='center'
    )
]


graphs_perf_tabs = html.Div(
    Tab(
        Card(
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
        ),
        id="perf_graphs_content", label="Performance Graphs",
        style=style_sub_tab, label_style=style_sub_label
    )
)
