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

"""Tab 3 : Defect list for Test Execution Callbacks"""

import json
from http import HTTPStatus
import dash_table
import pandas as pd
import requests
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import common
from common import app


@app.callback(
    Output('table_test_execution_wise_defect', 'children'),
    [Input('test_execution_submit_button', 'n_clicks'),
     Input('test_execution_input', 'value')]
)
def gen_table_execution_wise_defect(n_clicks, te_ids):
    """
    Callback : Returns the defect details attached to the test execution ids
    :param n_clicks: Event after submit button clicked.
    :param te_ids: List of test execution id's
    :return: Datatable
    """
    if n_clicks is None or te_ids is None:
        raise PreventUpdate

    te_list = te_ids.split(",")
    df_execution_wise_defect = pd.DataFrame(columns=["issue_no", "issue_comp",
                                                     "issue_name", "issue_priority",
                                                     "test_execution"])
    for te_id in te_list:
        issue_list = []
        query_input = {
            "query": {"testExecutionID": te_id,
                      "$or": [{"testResult": "FAIL"}, {"testResult": "BLOCKED"}]},
            "projection": {"issueIDs": True}}
        query_input.update(common.credentials)
        response = requests.request("GET", common.search_endpoint, headers=common.headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            for each in json_response["result"]:
                issue_list.extend(each["issueIDs"])

        te_df = common.get_issue_details(issue_list)
        for i in te_df:
            te_df["test_execution"] = te_id
        df_execution_wise_defect = df_execution_wise_defect.append(te_df)

    if common.debug_prints:
        print("gen_table_execution_wise_defect : Dataframe returned ")
        print(df_execution_wise_defect)

    execution_wise_defect = dash_table.DataTable(
        id="execution_wise_defect",
        columns=[{"name": str(i).upper(), "id": i} for i in df_execution_wise_defect.columns],
        data=df_execution_wise_defect.to_dict('records'),
        style_header=common.dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'}
                                ],
        style_cell=common.dict_style_cell
    )
    return execution_wise_defect
