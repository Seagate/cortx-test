"""Performance statistics UI layout designs"""
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

from dash_bootstrap_components import Card, CardBody, Row, Button, Tab  # , Tabs
from dash_core_components import Dropdown, Markdown, Loading
import dash_html_components as html
from Performance.styles import style_sub_tab, style_table_caption,\
    style_sub_label, style_perf_captions, style_workload_captions,\
    dict_Style_Stats_input_options, style_filters_captions, dict_button_style


release = [
    {'label': 'LC-K8S-CentOS-7.9',
        'value': 'LC_CentOS Linux release 7.9.2009 (Core)'},
    {'label': 'LR-R2-CentOS-7.9',
        'value': 'LR2_CentOS Linux release 7.9.2009 (Core)'},
    {'label': 'LR-R2-CentOS-7.8',
        'value': 'LR2_CentOS Linux release 7.8.2003 (Core)'},
    {'label': 'LR-R1-CentOS',
        'value': 'LR1_CentOS Linux release 7.8.2003 (Core)'},
    {'label': 'LR-R1-RHEL', 'value': 'LR1_RHEL'},

]


statistics_layout = Card(
    CardBody([
        html.P(["Note: Each data point is PER CLUSTER. \
                Red colored row(s) highlight error(s) encountered during that test."],
               style={'font-size': '20px', 'color': '#3131b0'}),
        # html.P(id="statistics_workload", style=style_workload_captions),
        # html.I(className="fa fa-info-circle"),

        html.P("S3Bench", style=style_perf_captions),
        Markdown('''
            ___
            '''),

        html.P("IOPath Performance Statistics",
               style=style_table_caption),
        Loading(html.Div(id="statistics_s3bench_table")),

        html.P("Metadata Operations Latency (captured with 1KB object)",
               style=style_table_caption),
        Loading(html.Div(id="statistics_metadata_table")),

        html.Br(),
        html.P("COSBench", style=style_perf_captions),
        Markdown('''
            ___
            '''),

        html.P("IOPath Performance Statistics (Mixed IO - Read 50%, Write 50%)",
               style=style_table_caption),
        Loading(html.Div(id="statistics_cosbench_table")),

        html.Br(),
        html.P("HSBench", style=style_perf_captions),
        Markdown('''
            ___
            '''),

        html.P("IOPath Performance Statistics",
               style=style_table_caption),
        Loading(html.Div(id="statistics_hsbench_table")),

        html.P("Bucket Operations Statistics",
               style=style_table_caption),
        Row(
            Dropdown(
                id="perf_bucketops_dropdown",
                placeholder="Select Object Size",
                style=dict_Style_Stats_input_options
            ), justify='center'),
        Loading(html.Div(id="statistics_bucketops_table",
                 style={'margin-top': '20px'})),
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
                id='perf_clients_dropdown',
                placeholder="Select Clients",
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
                id='perf_custom_dropdown',
                placeholder="Select Tag",
                style=dict_Style_Stats_input_options
            ),
            Dropdown(
                id='perf_iteration_dropdown',
                placeholder="Select Iterations",
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
                placeholder="Select Concurrency",
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
        html.P(["Note: Each data point is PER CLUSTER. \
                Red colored row(s) highlight error(s) encountered during that test."],
               style={'font-size': '20px', 'color': '#3131b0'}),
        # html.I(className="fa fa-info-circle"),
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

        # html.P("COSBench", style=style_perf_captions),
        # Markdown('''
        #     ___
        #     '''),

        # html.P("Throughput Chart",
        #        style=style_table_caption),
        # html.Div(id="statistics_cosbench_degraded_throughput"),
        # html.P("Latency Chart",
        #        style=style_table_caption),
        # html.Div(id="statistics_cosbench_degraded_latency"),
        # html.P("IOPS Chart",
        #        style=style_table_caption),
        # html.Div(id="statistics_cosbench_degraded_iops"),

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
        html.Div(id="statistics_hsbench_degraded_iops")
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
