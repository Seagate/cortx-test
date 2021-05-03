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
from dash_core_components import Dropdown, Markdown
import dash_html_components as html
from Performance.styles import dict_style_sub_tab, dict_style_table_caption,\
    dict_style_sub_label, style_perf_captions, style_workload_captions
from Performance.global_functions import benchmark_config, get_dict_from_array
from Performance.statistics.statistics_functions import fetch_configs_from_file

release = [
    {'label': 'LR-R1', 'value': '1'},
    {'label': 'LR-R2', 'value': '2'}
]

bucketOps = get_dict_from_array(fetch_configs_from_file(
    benchmark_config, 'Hsbench', 'object_size'), False)

statistics_layout = Card(
    CardBody(
        [
            html.P(html.U("Performance Metrics Statistics Summary"),
                   style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),
            html.P("S3 Bench", style=style_perf_captions),
            Markdown('''
            ___
            '''),

            html.P("IOPath Performance Statistics",
                   style=dict_style_table_caption),
            html.P(id="statistics_s3bench_workload",
                   style=style_workload_captions),
            html.Div(id="statistics_s3bench_table"),

            html.P("Metadata Operations Latency (captured with 1KB object)",
                   style=dict_style_table_caption),
            html.Div(id="statistics_metadata_table"),

            html.Br(),
            html.P("HS Bench", style=style_perf_captions),
            Markdown('''
            ___
            '''),
            html.P("IOPath Performance Statistics",
                   style=dict_style_table_caption),
            html.P(id="statistics_hsbench_workload_1",
                   style=style_workload_captions),
            html.Div(id="statistics_hsbench_table_1"),
            html.P(id="statistics_hsbench_workload_2",
                   style=style_workload_captions),
            html.Div(id="statistics_hsbench_table_2"),
            html.P(id="statistics_hsbench_workload_3",
                   style=style_workload_captions),
            html.Div(id="statistics_hsbench_table_3"),

            html.P("Bucket Operations Statistics",
                   style=dict_style_table_caption),
            Row(
                Dropdown(
                    id="bucketops_dropdown",
                    options=bucketOps,
                    placeholder="Select object size from given dropdown to get the details.",
                    style={'width': '500px', 'verticalAlign': 'middle', "margin-right": "15px",
                           "margin-top": "10px", 'align-items': 'center', 'justify-content': 'center'},
                ), justify='center'),
            html.P(id="statistics_bucketops_workload_1",
                   style=style_workload_captions),
            html.Div(id="statistics_bucketops_table_1"),
            html.P(id="statistics_bucketops_workload_2",
                   style=style_workload_captions),
            html.Div(id="statistics_bucketops_table_2"),
            html.P(id="statistics_bucketops_workload_3",
                   style=style_workload_captions),
            html.Div(id="statistics_bucketops_table_3"),

            html.Br(),
            html.P("COS Bench", style=style_perf_captions),
            Markdown('''
            ___
            '''),
            html.P("IOPath Performance Statistics",
                   style=dict_style_table_caption),
            html.P(id="statistics_cosbench_workload_1",
                   style=style_workload_captions),
            html.Div(id="statistics_cosbench_table_1"),
            html.P(id="statistics_cosbench_workload_2",
                   style=style_workload_captions),
            html.Div(id="statistics_cosbench_table_2"),
            html.P(id="statistics_cosbench_workload_3",
                   style=style_workload_captions),
            html.Div(id="statistics_cosbench_table_3"),
        ]
    ),
    className="flex-sm-fill nav-link"
)

stats_input_options = Row(
    [
        Dropdown(
            id="perf_release_dropdown",
            options=release,
            placeholder="Select Release",
            style={'width': '200px', 'verticalAlign': 'middle',
                   "margin-right": "15px", "margin-top": "10px"},
        ),

        Dropdown(
            id="perf_branch_dropdown",
            placeholder="Select Branch",
            style={'width': '200px', 'verticalAlign': 'middle',
                   "margin-right": "15px", "margin-top": "10px"},
        ),

        Dropdown(
            id='perf_build_dropdown',
            placeholder="Select Build",
            style={'width': '200px', 'verticalAlign': 'middle',
                   "margin-right": "15px", "margin-top": "10px"},
        ),
        Dropdown(
            id='profiles_options',
            placeholder="Select Profile",
            style={'width': '340px', 'verticalAlign': 'middle',
                   "margin-right": "10px", "margin-top": "10px"}
        ),

        Button("Get!", id="perf_submit_button", n_clicks=0, color="success",
               style={'height': '35px', 'margin-top': '20px'}),
    ],
    justify='center', style={'margin-bottom': '20px'}
)

statistics_perf_tabs = html.Div(
    Tab(statistics_layout, id="perf_statistics_content", label="Performance Statistics",
        style=dict_style_sub_tab, label_style=dict_style_sub_label
        )
)
