"""Performance graphs UI layouts designs"""
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

# External modules import
from dash_bootstrap_components import Card, CardBody, Row, Button, Tab
from dash_core_components import Dropdown, Graph, Loading
import dash_html_components as html
import dash_daq as daq

from Performance.styles import (
    style_sub_tab,
    style_sub_label,
    style_dropdown_small_2,
    style_dropdown_medium,
    dict_button_style,
    style_dropdown_large,
)

# Variable declarations
Xfilter = [
    {"label": "Build", "value": "Build"},
    {"label": "Object Size", "value": "Object_Size"},
]

release = [
    {"label": "LC-K8S-CentOS-7.9", "value": "LC_CentOS Linux release 7.9.2009 (Core)"},
    {"label": "LR-R2-CentOS-7.9", "value": "LR2_CentOS Linux release 7.9.2009 (Core)"},
    {"label": "LR-R2-CentOS-7.8", "value": "LR2_CentOS Linux release 7.8.2003 (Core)"},
    {"label": "LR-R1-CentOS", "value": "LR1_CentOS Linux release 7.8.2003 (Core)"},
    {"label": "LR-R1-RHEL", "value": "LR1_RHEL"},
]

benchmarks = [  # get from database
    {"label": "S3Bench", "value": "S3bench"},
    {"label": "COSBench", "value": "Cosbench"},
    {"label": "HSBench", "value": "Hsbench"},
]

operations = [  # write a function for this
    {"label": "Read & Write", "value": "both"},
    {"label": "Read", "value": "Read"},
    {"label": "Write", "value": "Write"},
]


graphs_input_options = [
    Row(
        [
            Dropdown(
                id="graphs_filter_dropdown",
                options=Xfilter,
                placeholder="Filter by",
                value="Build",
                style=style_dropdown_medium,
            ),
            Dropdown(
                id="graphs_benchmark_dropdown",
                options=benchmarks,
                placeholder="Benchmark",
                value="S3bench",
                style=style_dropdown_small_2,
            ),
            Dropdown(
                id="graphs_operations_dropdown",
                options=operations,
                placeholder="Operation",
                value="both",
                style=style_dropdown_medium,
            ),
            Dropdown(
                id="graphs_obj_size_dropdown",
                options=operations,
                placeholder="Operation",
                value="both",
                style={"display": "none"},
            ),
        ],
        justify="center",
    ),
    Row(
        [
            Dropdown(
                id="graphs_release_dropdown",
                options=release,
                placeholder="Release",
                style=style_dropdown_large,
                clearable=False,
            ),
            Dropdown(
                id="graphs_branch_dropdown",
                placeholder="Branch",
                style=style_dropdown_small_2,
            ),
            Dropdown(
                id="graphs_build_dropdown",
                placeholder="Build/Object Size",
                style=style_dropdown_medium,
            ),
            Dropdown(
                id="graphs_nodes_dropdown",
                placeholder="Nodes",
                style=style_dropdown_medium,
            ),
            Dropdown(
                id="graphs_clients_dropdown",
                placeholder="Clients",
                style=style_dropdown_medium,
            ),
            Dropdown(
                id="graphs_pfull_dropdown",
                placeholder="Cluster % Fill",
                style=style_dropdown_small_2,
            ),
            Dropdown(
                id="graphs_custom_dropdown",
                placeholder="Select Tag",
                style=style_dropdown_medium,
            ),
            Dropdown(
                id="graphs_iteration_dropdown",
                placeholder="Iterations",
                style=style_dropdown_small_2,
            ),
            Dropdown(
                id="graphs_sessions_dropdown",
                placeholder="Concurrency",
                style=style_dropdown_medium,
            ),
            Dropdown(
                id="graphs_buckets_dropdown",
                placeholder="Buckets",
                style=style_dropdown_medium,
            ),
            daq.ToggleSwitch(
                id="compare_flag",
                label="Compare",
                labelPosition="bottom",
                style={
                    "color": "#FFFFFF",
                    "margin-top": "15px",
                    "margin-right": "10px",
                },
            ),
        ],
        justify="center",
    ),
    Row(
        [
            Dropdown(
                id="graphs_release_compare_dropdown",
                options=release,
                placeholder="Release",
                style={"display": "none"},
            ),
            Dropdown(
                id="graphs_branch_compare_dropdown",
                placeholder="Branch",
                style={"display": "none"},
            ),
            Dropdown(
                id="graphs_build_compare_dropdown",
                placeholder="Build/Object Size",
                style={"display": "none"},
            ),
            Dropdown(
                id="graphs_nodes_compare_dropdown",
                placeholder="Nodes",
                style={"display": "none"},
            ),
            Dropdown(
                id="graphs_clients_compare_dropdown",
                placeholder="Clients",
                style={"display": "none"},
            ),
            Dropdown(
                id="graphs_pfull_compare_dropdown",
                placeholder="Cluster % Fill",
                style={"display": "none"},
            ),
            Dropdown(
                id="graphs_custom_compare_dropdown",
                placeholder="Select Tag",
                style={"display": "none"},
            ),
            Dropdown(
                id="graphs_iteration_compare_dropdown",
                placeholder="Iterations",
                style={"display": "none"},
            ),
            Dropdown(
                id="graphs_sessions_compare_dropdown",
                placeholder="Concurrency",
                style={"display": "none"},
            ),
            Dropdown(
                id="graphs_buckets_compare_dropdown",
                placeholder="Buckets",
                style={"display": "none"},
            ),
            Button(
                "Plot",
                id="graphs_submit_button",
                n_clicks=0,
                color="success",
                style=dict_button_style,
            ),
        ],
        justify="center",
    ),
]


graphs_perf_tabs = html.Div(
    Tab(
        Card(
            CardBody(
                [
                    html.P(
                        [  # html.I(className="fa fa-info-circle"),
                            "Note: Each data point is PER CLUSTER."
                        ],
                        style={"font-size": "20px", "color": "#3131b0"},
                    ),
                    Loading(Graph(id="plot_Throughput")),
                    Loading(Graph(id="plot_Latency")),
                    Loading(Graph(id="plot_IOPS")),
                    Loading(Graph(id="plot_TTFB")),
                    Loading(Graph(id="plot_all")),
                ]
            ),
            className="flex-sm-fill nav-link",
        ),
        id="perf_graphs_content",
        label="Performance Graphs",
        style=style_sub_tab,
        label_style=style_sub_label,
    )
)
