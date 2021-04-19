""" Layouts for each of the tab."""
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


import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import common

# R1 TAB 1: Executive report
report_header_style = {'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold',
                       'font-family': 'Serif'}

bucketOps = [
    {'label': 'Average Latency', 'value': 'AvgLat'},
    {'label': 'Minimum Latency', 'value': 'MinLat'},
    {'label': 'Maximum Latency', 'value': 'MaxLat'},
    {'label': 'IOPS', 'value': 'Iops'},
    {'label': 'Throughput', 'value': 'Mbps'},
    {'label': 'Operations', 'value': 'Ops'},
    {'label': 'Execution Time', 'value': 'Seconds'},
]
bucketops_caption = [
    html.Caption(dbc.Row([html.Tr([html.Th("Bucket Operations for")]),
                          dcc.Dropdown(
                              id="Bucket_Ops_Dropdown",
                              options=bucketOps,
                              placeholder="Average Latency",
                              style={'width': '300px', 'verticalAlign': 'middle',
                                     "margin-right": "15px"},
                          ),
                          html.P(
                              html.Em("⟽ Select one of the bucket operations to view statistics."),
                              className="card-text", ),

                          ], justify="center", align="center"
                         ),
                 ),
]
r1_exec_report_content = dbc.Card(
    dbc.CardBody(
        [
            html.P(html.U("Executive Report"), style=report_header_style),
            html.P(html.H5(id="r1_product_heading_exe"), className="card-text", ),
            html.P(html.H5(id="r1_build_heading_exe"), className="card-text", ),
            html.P(html.H5(id="r1_date_heading_exe"), className="card-text", ),
            html.P("Reported Bugs", style=common.dict_style_table_caption),
            dcc.Loading(html.Div(id="r1_table_reported_bugs_exe")),
            html.P("Overall QA Report", style=common.dict_style_table_caption),
            html.Div(id="r1_table_overall_qa_report_exe"),
            html.P("Feature Breakdown Summary", style=common.dict_style_table_caption),
            html.Div(id="r1_table_feature_breakdown_summary"),
            html.P("Code Maturity", style=common.dict_style_table_caption),
            html.Div(id="r1_table_code_maturity"),
            html.P("Single Bucket Performance Statistics (Average) using S3Bench - in a Nutshell",
                   style=common.dict_style_table_caption),
            html.Div(id="r1_table_s3_bucket_perf")
        ]
    ),
    className="flex-sm-fill nav-link",
)

# R1 TAB 2: Engg report
r1_engg_report_content = dbc.Card(
    dbc.CardBody(
        [
            html.P(html.U("Engineer Report"), style=report_header_style),
            html.P(html.H5(id="r1_product_heading_eng"), className="card-text", ),
            html.P(html.H5(id="r1_build_heading_eng"), className="card-text", ),
            html.P(html.H5(id="r1_date_heading_eng"), className="card-text"),
            html.P("Reported Bugs", style=common.dict_style_table_caption),
            dcc.Loading(html.Div(id="r1_table_reported_bugs_engg")),
            html.P("Overall QA Report", style=common.dict_style_table_caption),
            html.Div(id="r1_table_overall_qa_report_engg"),
            html.P("Component Level Tests Summary", style=common.dict_style_table_caption),
            html.Div(id="r1_table_comp_summary"),
            html.P("Timing Summary (seconds)", style=common.dict_style_table_caption),
            html.Div(id="r1_table_timing_summary"),
            html.P("Single Bucket Performance Statistics (Average) using S3Bench",
                   style=common.dict_style_table_caption),
            html.Div(id="r1_table_detailed_s3_bucket_perf"),
            html.P("Metadata Latencies(captured with 1KB object)",
                   style=common.dict_style_table_caption),
            html.Div(id="r1_table_metadata_latency"),
            html.P("Multiple Buckets Performance Statistics (Average) using HSBench and COSBench",
                   style=common.dict_style_table_caption),
            html.Div(id="r1_table_multi_bucket_perf_stats"),
            html.Div(dbc.Table(bucketops_caption),style = {'textAlign': 'center'}),
            html.Div(id = "r1_table_bucket_ops_data"),
            html.P("Detail Reported Bugs", style=common.dict_style_table_caption),
            dcc.Loading(html.Div(id="r1_table_detail_reported_bugs"))
        ]
    ),
    className="flex-sm-fill nav-link active",
)

# R2 TAB 1: Executive report
r2_exec_report_content = dbc.Card(
    dbc.CardBody(
        [
            html.P(html.U("Executive Report"), style=report_header_style),
            html.P(html.H5(id="product_heading_exe"), className="card-text", ),
            html.P(html.H5(id="build_heading_exe"), className="card-text", ),
            html.P(html.H5(id="date_heading_exe"), className="card-text", ),
            html.P("Reported Bugs", style=common.dict_style_table_caption),
            dcc.Loading(html.Div(id="table_reported_bugs_exe")),
            html.P("Overall QA Report", style=common.dict_style_table_caption),
            html.Div(id="table_overall_qa_report_exe"),
            html.P("Feature Breakdown Summary", style=common.dict_style_table_caption),
            html.Div(id="table_feature_breakdown_summary"),
            html.P("Code Maturity", style=common.dict_style_table_caption),
            html.Div(id="table_code_maturity"),
            html.P("Single Bucket Performance Statistics (Average) using S3Bench - in a Nutshell",
                   style=common.dict_style_table_caption),
            html.Div(id="table_s3_bucket_perf")
        ]
    ),
    className="flex-sm-fill nav-link",
)

# R2 TAB 2 : Engg report
r2_engg_report_content = dbc.Card(
    dbc.CardBody(
        [
            html.P(html.U("Engineer Report"), style=report_header_style),
            html.P(html.H5(id="product_heading_eng"), className="card-text", ),
            html.P(html.H5(id="build_heading_eng"), className="card-text", ),
            html.P(html.H5(id="date_heading_eng"), className="card-text"),
            html.P("Reported Bugs", style=common.dict_style_table_caption),
            dcc.Loading(html.Div(id="table_reported_bugs_engg")),
            html.P("Overall QA Report", style=common.dict_style_table_caption),
            html.Div(id="table_overall_qa_report_engg"),
            html.P("Component Level Issues Summary", style=common.dict_style_table_caption),
            html.Div(id="table_comp_summary"),
            html.P("Timing Summary (seconds)", style=common.dict_style_table_caption),
            html.Div(id="table_timing_summary"),
            html.P("Single Bucket Performance Statistics (Average) using S3Bench",
                   style=common.dict_style_table_caption),
            html.Div(id="table_detailed_s3_bucket_perf"),
            html.P("Metadata Latencies(captured with 1KB object)",
                   style=common.dict_style_table_caption),
            html.Div(id="table_metadata_latency"),
            html.P("Multiple Buckets Performance Statistics (Average) using HSBench and COSBench",
                   style=common.dict_style_table_caption),
            html.Div(id="table_multi_bucket_perf_stats"),
            html.P("Detail Reported Bugs", style=common.dict_style_table_caption),
            dcc.Loading(html.Div(id="table_detail_reported_bugs"))
        ]
    ),
    className="flex-sm-fill nav-link active",
)

# TAB3: Input for Test Execution wise defects table
testPlan_inputs = dbc.Row(
    dbc.Col(dbc.InputGroup([
        dbc.Input(id="test_execution_input",
                  placeholder="Enter , separated Test Execution IDs or Test Plan IDs",
                  debounce=True),
        dbc.InputGroupAddon(
            dbc.Button("Get defects!", id="test_execution_submit_button", color="success"),
            addon_type="postpend",
        )], style={'margin': 10}),
        width=5),
    justify="center"
)

defect_list_per_tp_content = dbc.Card(

    dbc.CardBody(
        [
            testPlan_inputs,
            dcc.Loading(
                (
                    dbc.Row(
                        [dbc.Col(
                            html.Div(id='table_test_execution_wise_defect', className='text-center',
                                     style={'margin': 20, 'margin-top': 10,
                                            'margin-bottom': 20}))
                        ]),
                    dbc.Row(
                        [dbc.Col(html.Div(id='test_execution_wise_defect_error'),
                                 className='text-center',
                                 style={'color': '#ff0000', 'margin': 20, 'font-size': 20})]
                    )
                )
            )
        ]
    ),
    className="flex-sm-fill nav-link",
)
