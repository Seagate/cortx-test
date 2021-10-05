"""Performance statistics UI layout designs"""
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

from dash_bootstrap_components import Card, CardBody, Row, Button, Tab, Tabs
from dash_core_components import Dropdown, Markdown
import dash_html_components as html
from Performance.styles import style_sub_tab, style_table_caption,\
    style_sub_label, style_perf_captions, style_workload_captions,\
    dict_Style_Stats_input_options, style_filters_captions, dict_button_style


release = [
    {'label': 'LR-R1', 'value': '1'},
    {'label': 'LR-R2', 'value': '2'}
]


statistics_layout = Card(
    CardBody([
        html.P(html.U("Performance Metrics Statistics Summary"),
               style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),
        html.P("Note: Each data point represents PER CLUSTER data. \
            Data is displayed for the builds on which PerfPro has run.",
               style={"font-weight": "bold", 'font-size': '20px', 'color': '#D00000'}),
        html.P("Run Details", style=style_perf_captions),
        Markdown('''
            ___
            '''),
        html.P(id="statistics_workload",
               style=style_workload_captions),
        html.P("S3Bench", style=style_perf_captions),
        Markdown('''
            ___
            '''),

        html.P("IOPath Performance Statistics",
               style=style_table_caption),
        html.Div(id="statistics_s3bench_table"),

        html.P("Metadata Operations Latency (captured with 1KB object)",
               style=style_table_caption),
        html.Div(id="statistics_metadata_table"),

        html.Br(),
        html.P("COSBench", style=style_perf_captions),
        Markdown('''
            ___
            '''),

        html.P("IOPath Performance Statistics (Mixed IO - Read 50%, Write 50%)",
               style=style_table_caption),
        html.Div(id="statistics_cosbench_table"),

        html.Br(),
        html.P("HSBench", style=style_perf_captions),
        Markdown('''
            ___
            '''),

        html.P("IOPath Performance Statistics",
               style=style_table_caption),
        html.Div(id="statistics_hsbench_table"),

        html.P("Bucket Operations Statistics",
               style=style_table_caption),
        Row(
            Dropdown(
                id="perf_bucketops_dropdown",
                placeholder="Select Object Size",
                style=dict_Style_Stats_input_options
            ), justify='center'),
        html.Div(id="statistics_bucketops_table",
                 style={'margin-top': '20px'}),
    ]
    ),
    className="flex-sm-fill nav-link"
)

stats_input_options = [
    Row(
        [
            html.P("Setup Configuration » ", style=style_filters_captions),
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
                placeholder="Select Cluster % Fill",
                style=dict_Style_Stats_input_options
            )
        ],
        justify='center'
    ),
    Row(
        [
            html.P("User Configuration » ", style=style_filters_captions),
            Dropdown(
                id='perf_iteration_dropdown',
                placeholder="Select Iterations",
                style=dict_Style_Stats_input_options
            ),
            Dropdown(
                id='perf_custom_dropdown',
                placeholder="Select Tag",
                style=dict_Style_Stats_input_options
            )
        ],
        justify='center'
    ),
    Row(
        [
            html.P("Benchmark Configuration » ", style=style_filters_captions),
            Dropdown(
                id='perf_sessions_dropdown',
                placeholder="Select Sessions",
                style=dict_Style_Stats_input_options
            ),
            Dropdown(
                id='perf_buckets_dropdown',
                placeholder="Select Buckets",
                style=dict_Style_Stats_input_options
            ),

            Button("Show", id="perf_submit_button", n_clicks=0, color="success",
                   style=dict_button_style),
        ],
        justify='center', style={'margin-bottom': '20px'}
    )
]

degraded_read_layout = Card(
    CardBody([
        html.P(html.U("Read Performance of Degraded Cluster"),
               style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),
        html.P("Note: Each data point represents PER CLUSTER data.",  style={
            "font-weight": "bold", 'font-size': '20px', 'color': '#D00000'}),

        html.P("S3Bench", style=style_perf_captions),
        Markdown('''
            ___
            '''),

        html.P("Throughput Chart",
               style=style_table_caption),
        html.Div(id="statistics_s3bench_degraded_throughput"),
        html.P("Latency Chart",
               style=style_table_caption),
        html.Div(id="statistics_s3bench_degraded_latency"),
        html.P("IOPS Chart",
               style=style_table_caption),
        html.Div(id="statistics_s3bench_degraded_iops"),
        html.P("TTFB Chart",
               style=style_table_caption),
        html.Div(id="statistics_s3bench_degraded_ttfb"),

        html.P("COSBench", style=style_perf_captions),
        Markdown('''
            ___
            '''),

        html.P("Throughput Chart",
               style=style_table_caption),
        html.Div(id="statistics_cosbench_degraded_throughput"),
        html.P("Latency Chart",
               style=style_table_caption),
        html.Div(id="statistics_cosbench_degraded_latency"),
        html.P("IOPS Chart",
               style=style_table_caption),
        html.Div(id="statistics_cosbench_degraded_iops"),

        html.P("HSBench", style=style_perf_captions),
        Markdown('''
            ___
            '''),

        html.P("Throughput Chart",
               style=style_table_caption),
        html.Div(id="statistics_hsbench_degraded_throughput"),
        html.P("Latency Chart",
               style=style_table_caption),
        html.Div(id="statistics_hsbench_degraded_latency"),
        html.P("IOPS Chart",
               style=style_table_caption),
        html.Div(id="statistics_hsbench_degraded_iops"),
    ]),
    className="flex-sm-fill nav-link"
)


# statistics_perf_tabs = Tabs([
#     Tab(statistics_layout, id="perf_statistics_content", label="Performance Statistics",
#         style=style_sub_tab, label_style=style_sub_label
#         ),
#     Tab(degraded_read_layout, id="perf_degraded_read_content", label="Degraded Read Performance",
#         style=style_sub_tab, label_style=style_sub_label
#         )
#     ],
#     className="nav nav nav-pills nav-fill nav-pills flex-column flex-sm-row"
# )

statistics_perf_tabs = html.Div(
    Tab(statistics_layout, id="perf_statistics_content", label="Performance Statistics",
        style=style_sub_tab, label_style=style_sub_label
        )
)
