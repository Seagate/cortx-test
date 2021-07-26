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
    dict_style_sub_label, style_perf_captions, style_workload_captions, dict_Style_Stats_input_options


release = [
    {'label': 'LR-R1', 'value': '1'},
    {'label': 'LR-R2', 'value': '2'}
]


statistics_layout = Card(
    CardBody([
        html.P(html.U("Performance Metrics Statistics Summary"),
               style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),
        html.P("Note: Each data point represents PER CLUSTER data.",  style={
            "font-weight": "bold", 'font-size': '20px', 'color': '#D00000'}),
        html.P("S3 Bench", style=style_perf_captions),
        Markdown('''
            ___
            '''),
        Row(
            Dropdown(
                id='perf_sessions_s3_dropdown',
                placeholder="Select Sessions",
                style=dict_Style_Stats_input_options
            ), justify='center'),

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
        Row([
            Dropdown(
                id='perf_sessions_hs_dropdown',
                placeholder="Select Sessions",
                style=dict_Style_Stats_input_options
            ),
            Dropdown(
                id='perf_buckets_hs_dropdown',
                placeholder="Select Buckets",
                style=dict_Style_Stats_input_options
            )
        ], justify='center'),

        html.P("IOPath Performance Statistics",
               style=dict_style_table_caption),
        html.P(id="statistics_hsbench_workload",
               style=style_workload_captions),
        html.Div(id="statistics_hsbench_table"),

        html.P("Bucket Operations Statistics",
               style=dict_style_table_caption),
        Row(
            Dropdown(
                id="perf_bucketops_dropdown",
                placeholder="Select Object Size",
                style=dict_Style_Stats_input_options
            ), justify='center'),
        html.Div(id="statistics_bucketops_table", style= {'margin-top': '20px'}),

        html.Br(),
        html.P("COS Bench", style=style_perf_captions),
        Markdown('''
            ___
            '''),
        Row([
            Dropdown(
                id='perf_sessions_cos_dropdown',
                placeholder="Select Sessions",
                style=dict_Style_Stats_input_options
            ),
            Dropdown(
                id='perf_buckets_cos_dropdown',
                placeholder="Select Buckets",
                style=dict_Style_Stats_input_options
            )],
            justify='center'
            ),

        html.P("IOPath Performance Statistics",
               style=dict_style_table_caption),
        html.P(id="statistics_cosbench_workload",
               style=style_workload_captions),
        html.Div(id="statistics_cosbench_table"),
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
            style=dict_Style_Stats_input_options,
        ),

        Dropdown(
            id="perf_branch_dropdown",
            placeholder="Select Branch",
            style=dict_Style_Stats_input_options,
        ),

        Dropdown(
            id='perf_build_dropdown',
            placeholder="Select Build",
            style=dict_Style_Stats_input_options,
        ),
        Dropdown(
            id='perf_nodes_dropdown',
            placeholder="Select Nodes",
            style=dict_Style_Stats_input_options
        ),
        Dropdown(
            id='perf_pfull_dropdown',
            placeholder="Select cluster utilization",
            style=dict_Style_Stats_input_options
        ),
        Dropdown(
            id='perf_iteration_dropdown',
            placeholder="Select Iterations",
            style=dict_Style_Stats_input_options
        ),
        Dropdown(
            id='perf_custom_dropdown',
            placeholder="Select Profile",
            style=dict_Style_Stats_input_options
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
