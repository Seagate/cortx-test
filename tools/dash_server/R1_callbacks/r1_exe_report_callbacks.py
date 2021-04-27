"""LDR 1 Executive Report Callbacks."""
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, branch 2.0 (the "License");
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

import dash_table
import numpy as np
import pandas as pd
from dash.dependencies import Output, Input, State
from dash.exceptions import PreventUpdate

import R1_callbacks.r1_perf_tables as r1_perf_tables
import common
import mongodbAPIs as r1Api
from common import app


@app.callback(
    [Output('r1_product_heading_exe', 'children'), Output('r1_product_heading_eng', 'children'),
     Output('r1_build_heading_exe', 'children'), Output('r1_build_heading_eng', 'children'),
     Output('r1_date_heading_exe', 'children'), Output('r1_date_heading_eng', 'children')],
    [Input('submit_button', 'n_clicks')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')
     ]
)
def gen_tab_headers(n_clicks, branch, build_no):
    """
    Generate Report headers with details.
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    product_heading = "Product : Lyve Rack 1"
    build_heading = "Build : " + str(build_no)
    date_output = r1Api.find({'build': build_no, 'deleted': False}).sort(
        [("dateOfExecution", 1)]).limit(1)
    date_str = date_output[0]['dateOfExecution'].split("T")[0] + date_output[0][
                                                                     'dateOfExecution'][19::]
    date = "Date : " + str(date_str)
    return product_heading, product_heading, build_heading, build_heading, date, date


@app.callback(
    [Output('r1_table_reported_bugs_engg', 'children'),
     Output('r1_table_reported_bugs_exe', 'children')],
    [Input('submit_button', 'n_clicks')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')
     ]
)
def gen_table_reported_bugs(n_clicks, branch, build_no):
    """
    Generate Priority wise and Cortx/Test issue table
    """
    issue_type = ["Total", "Blocker", "Critical", "Major", "Minor", "Trivial"]
    test_infra_issue_dict = {"Total": 0, "Blocker": 0, "Critical": 0, "Major": 0, "Minor": 0,
                             "Trivial": 0}
    cortx_issue_dict = {"Total": 0, "Blocker": 0, "Critical": 0, "Major": 0, "Minor": 0,
                        "Trivial": 0}

    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    issue_list = r1Api.find_distinct("defectID", {"build": build_no, 'deleted': False})

    df_issue_details = common.get_issue_details(issue_list)
    # check issue type and priority
    # test issues
    df_test_infra_issue = df_issue_details.loc[
        df_issue_details["issue_comp"].isin(["CFT", "Automation"])]
    if common.DEBUG_PRINTS:
        print("test_infra issue {}".format(df_test_infra_issue))
    test_infra_issue_dict["Total"] = df_test_infra_issue.shape[0]

    # cortx issues
    df_cortx_issue = df_issue_details.loc[
        ~df_issue_details["issue_comp"].isin(["CFT", "Automation"])]
    if common.DEBUG_PRINTS:
        print("cortx issue {}".format(df_cortx_issue))
    df_cortx_issue["Total"] = df_cortx_issue.shape[0]

    for i_type in issue_type[:-1]:
        test_infra_issue_dict[i_type] = \
            df_test_infra_issue[df_test_infra_issue["issue_priority"] == i_type].shape[0]
        cortx_issue_dict[i_type] = \
            df_cortx_issue[df_cortx_issue["issue_priority"] == i_type].shape[0]

    df_reported_bugs = pd.DataFrame({"Priority": issue_type,
                                     "Test Infra Issues": test_infra_issue_dict.values(),
                                     "Cortx SW Issues": cortx_issue_dict.values()})
    reported_bugs = dash_table.DataTable(
        id="reported_bugs",
        columns=[{"name": i, "id": i} for i in df_reported_bugs.columns],
        data=df_reported_bugs.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'row_index': 0}, 'color': '#3498DB'},
                                {'if': {'row_index': 1}, 'color': '#CB4335'},
                                {'if': {'row_index': 2}, 'color': '#F39C12'},
                                {'if': {'row_index': 3}, 'color': '#2874A6'},
                                {'if': {'row_index': 4}, 'color': '#2E4053'},
                                {'if': {'row_index': 5}, 'color': '#229954'}
                                ],
        style_cell=common.dict_style_cell
    )
    return reported_bugs, reported_bugs


@app.callback(
    [Output('r1_table_overall_qa_report_engg', 'children'),
     Output('r1_table_overall_qa_report_exe', 'children')],
    [Input('submit_button', 'n_clicks')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value'),
     ]
)
def gen_table_overall_qa_report(n_clicks, branch, build_no):
    """
    Generate Overall test reports along with the previous build reports
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate
    category = ["TOTAL", "PASS", "FAIL", "ABORTED", "BLOCKED", "TODO"]
    current_build = []
    previous_build = []

    try:
        for result_type in category[1:]:
            count = r1Api.count_documents({'build': build_no,
                                           'deleted': False, 'testResult': result_type})
            current_build.append(count)
        current_build.insert(0, sum(current_build))
        print("Current build overall_qa_report {}".format(current_build))
    except Exception as ex:
        print("Error current build received : {}".format(ex))
        current_build = ["-", "-", "-", "-", "-", "-"]

    data_overall_qa_report = {"Category": category,
                              build_no: current_build}

    # add logic to retrieve previous build
    cursor = r1Api.find({'info': 'build sequence R1'})
    build_list = cursor[0][branch]
    if build_list.index(build_no) > 1:
        prev_build_no = build_list[build_list.index(build_no) - 1]
        try:
            for result_type in category[1:]:
                count = r1Api.count_documents({'build': prev_build_no, 'version': branch,
                                               'deleted': False, 'testResult': result_type})
                previous_build.append(count)
            previous_build.insert(0, sum(previous_build))
            print("Previous build overall_qa_report {}".format(previous_build))
        except Exception as ex:
            print("Error Previous build received : {}".format(ex))
            previous_build = ["-", "-", "-", "-", "-", "-"]

        data_overall_qa_report[prev_build_no] = previous_build

    df_overall_qa_report = pd.DataFrame(data_overall_qa_report)
    overall_qa_report = dash_table.DataTable(
        id="overall_qa_report",
        columns=[{"name": i, "id": i} for i in df_overall_qa_report.columns],
        data=df_overall_qa_report.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'row_index': 0}, 'color': '#3498DB'},
                                {'if': {'row_index': 1}, 'color': '#229954'},
                                {'if': {'row_index': 2}, 'color': '#CB4335'},
                                {'if': {'row_index': 3}, 'color': '#2E4053'},
                                {'if': {'row_index': 4}, 'color': '#F39C12'},
                                {'if': {'row_index': 5}, 'color': '#a5a5b5'}
                                ],
        style_cell=common.dict_style_cell
    )
    return overall_qa_report, overall_qa_report


@app.callback(
    Output('r1_table_feature_breakdown_summary', 'children'),
    [Input('submit_button', 'n_clicks')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')
     ]
)
def gen_table_feature_breakdown_summary(n_clicks, branch, build_no):
    """
    Generate feature wise breakdown of test results.
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    feature_list = ['User operations', 'Scalability', 'Availability', 'Longevity',
                    'Performance', 'Usecases', 'Orphans']
    pass_count_list = []
    fail_count_list = []
    total_count_list = []
    for feature in feature_list:
        pass_count = r1Api.count_documents(
            {"build": build_no, "deleted": False, 'testResult': 'PASS', 'feature': feature})
        fail_count = r1Api.count_documents(
            {"build": build_no, "deleted": False, 'feature': feature,
             '$or': [{'testResult': 'FAIL'}, {'testResult': 'BLOCKED'}]})

        pass_count_list.append(pass_count)
        fail_count_list.append(fail_count)
        total_count_list.append(pass_count + fail_count)

    # add total as last row of table
    feature_list.append("Total")
    pass_count_list.append(sum(pass_count_list))
    fail_count_list.append(sum(fail_count_list))
    total_count_list.append(sum(total_count_list))

    if common.DEBUG_PRINTS:
        print("Feature_list {}".format(feature_list))
        print("Pass list {}".format(pass_count_list))
        print("Fail list {}".format(fail_count_list))
        print("Total list {}".format(total_count_list))

    data_feature_breakdown_summary = {"Feature": feature_list,
                                      "Total": total_count_list,
                                      "Passed": pass_count_list,
                                      "Failed": fail_count_list,
                                      }
    df_feature_breakdown_summary = pd.DataFrame(data_feature_breakdown_summary)
    df_feature_breakdown_summary["% Passed"] = (df_feature_breakdown_summary["Passed"] /
                                                df_feature_breakdown_summary["Total"] * 100)
    df_feature_breakdown_summary["% Passed"] = np.ceil(df_feature_breakdown_summary["% Passed"])

    df_feature_breakdown_summary["% Failed"] = (df_feature_breakdown_summary["Failed"] /
                                                df_feature_breakdown_summary["Total"] * 100)
    df_feature_breakdown_summary["% Failed"] = np.floor(df_feature_breakdown_summary["% Failed"])

    feature_breakdown_summary = dash_table.DataTable(
        id="feature_breakdown_summary",
        columns=[{"name": i, "id": i} for i in df_feature_breakdown_summary.columns],
        data=df_feature_breakdown_summary.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'row_index': len(total_count_list)},
                                 'backgroundColor': "#c1c1d6"},
                                {'if': {'column_id': "Feature"},
                                 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=common.dict_style_cell
    )
    return feature_breakdown_summary


@app.callback(
    Output('r1_table_code_maturity', 'children'),
    [Input('submit_button', 'n_clicks')],
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')
     ]
)
def gen_table_code_maturity(n_clicks, branch, build_no):
    """
    Code Maturity with reference to the previous builds
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    output_list = []
    category = ["TOTAL", "PASS", "FAIL", "ABORTED", "BLOCKED"]

    cursor = r1Api.find({'info': 'build sequence R1'})
    build_list = cursor[0][branch]

    prev_build_no = build_list[build_list.index(build_no)::-1]
    output_list = [build_no]
    output_list.extend(prev_build_no)

    print("Output list :", output_list)

    data_code_maturity = {"Category": category}

    for build in output_list:
        temp_list = []
        for each in category[1:]:
            temp_list.append(
                r1Api.count_documents({'build': build, 'deleted': False, 'testResult': each}))
        temp_list.insert(0, sum(temp_list))
        data_code_maturity[build] = temp_list

    print("Data : {}".format(data_code_maturity))
    df_code_maturity = pd.DataFrame(data_code_maturity)
    code_maturity = dash_table.DataTable(
        id="code_maturity",
        columns=[{"name": i, "id": i} for i in df_code_maturity.columns],
        data=df_code_maturity.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Category"}, 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=common.dict_style_cell
    )
    return code_maturity


@app.callback(
    Output('r1_table_s3_bucket_perf', 'children'),
    Input('submit_button', 'n_clicks'),
    [State('branch_dropdown', 'value'),
     State('build_no_dropdown', 'value')]
)
def gen_table_s3_bucket_perf(n_clicks, branch, build_no):
    """
    Single Bucket Performance Statistics using S3bench
    """
    if n_clicks is None or branch is None or build_no is None:
        raise PreventUpdate

    df_s3_bucket_perf = r1_perf_tables.get_single_bucket_perf_data(build_no)
    s3_bucket_perf = dash_table.DataTable(
        id="S3 Bucket Perf",
        columns=[{"name": i, "id": i} for i in df_s3_bucket_perf.columns],
        data=df_s3_bucket_perf.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Statistics"},
                                 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=common.dict_style_cell
    )
    return s3_bucket_perf
