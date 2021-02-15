import json
import os
from http import HTTPStatus

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import flask
import pandas as pd
import requests
from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from jira import JIRA

external_stylesheets = [dbc.themes.COSMO]
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                prevent_initial_callbacks=True)
app.title = "CORTX Test Status"
server = app.server

# database Details --------------------------------------------------------
search_endpoint = "http://cftic2.pun.seagate.com:5000/reportsdb/search"
headers = {
    'Content-Type': 'application/json'
}
credentials = {"db_username": "dataread", "db_password": "seagate@123"}
jira_username = "cortx-qa-user1"
jira_password = "ESyAgh999zP9"

# global declarations--------------------------------------------------------
external_stylesheets = [dbc.themes.COSMO]
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "CORTX Test Status"
server = app.server
__version__ = "5.27"

# build versions
versions = [
    {'label': 'Release', 'value': 'Release'},
    {'label': 'Beta', 'value': 'Beta'}
]

# common style
dict_style_table_caption = {'font-size': '20px', 'font-weight': 'bold', 'color': '#3131b0',
                            'margin-top': '18px','margin-bottton': '5px'}
dict_style_header = {'backgroundColor': '#7F8C8D', 'textAlign': 'center', 'font-size': '18px',
                     'fontWeight': 'bold',
                     'border': '1px solid black'}
dict_style_cell = {'textAlign': 'center', 'border': '1px solid black', 'fontWeight': 'bold',
                   'font-size': '15px'}


# Main page code --------------------------------------------------------------
@server.route('/favicon.ico')
def favicon():
    return flask.send_from_directory(os.path.join(server.root_path, 'static'), 'favicon.ico')


toast = html.Div(
    [
        dbc.Toast(
            "Please verify and enter correct build number. Data is not there for this build number.",
            id="positioned-toast",
            header="Wrong build number",
            is_open=False,
            dismissable=True,
            icon="danger",
            duration=6000,
            # top: 66 positions the toast below the navbar
            style={"position": "fixed", "top": 25, "right": 10, "width": 350},
        ),
    ]
)
# two buttons on top right
search_bar = dbc.Row(
    [
        dbc.Col([
            dbc.Button("Cortx Sharepoint", color="light", size="lg", className="mr-1", outline=True,
                       href="https://seagatetechnology.sharepoint.com/sites/gteamdrv1/tdrive1224",
                       target="_blank"),
            dbc.Button("CFT Sharepoint", color="light", size="lg", className="mr-1", outline=True,
                       href="https://seagatetechnology.sharepoint.com/:f:/r/sites/gteamdrv1/tdrive1224/Shared%20Documents/CFT_IntegrationTeam?csf=1&web=1&e=9Wgzsx",
                       target="_blank")],
            width="auto",
        ),
    ],
    no_gutters=True,
    className="ml-auto flex-nowrap mt-3 mt-md-0",
    align="center",
)

navbar = dbc.Navbar(
    [
        html.A(
            dbc.Row([
                dbc.Col(html.Img(src=app.get_asset_url(
                    "seagate.png"), height="100px")),
                dbc.Col(dbc.NavbarBrand("CORTX CFT Dashboard",
                                        className="ml-2",
                                        style={'font-size': 40, 'text-align': 'center'}))
            ],
                align="center",
                no_gutters=True,
            ),
        ),
        dbc.NavbarToggler(id="navbar-toggler"),
        dbc.Collapse(search_bar, id="navbar-collapse", navbar=True),
    ],
    color="dark",
    dark=True,
)
build_report_header = dbc.Jumbotron(html.H4(html.Em("... looking for build number!")),
                                    id="build_report_header",
                                    style={'padding': '1em',
                                           'background': 'transparent', 'text-align': 'center'})
input_options = dbc.Row(
    [
        dcc.Dropdown(
            id="version_dropdown",
            options=versions,
            placeholder="select version",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px"},
        ),

        dcc.Dropdown(
            id='build_no_dropdown',
            placeholder="select build",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px"},
        ),

        dbc.Button("Get!", id="submit_button", n_clicks=0, color="success",
                   style={'height': '35px'}),
    ],
    justify='center'
)
input_optional_options = dbc.Row(
    [
        dcc.Dropdown(
            id='test_system_dropdown',
            placeholder="Test System Type",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px"},
        ),

        dcc.Dropdown(
            id='test_team_dropdown',
            placeholder="Select test component(Optional)",
            style={'width': '200px', 'verticalAlign': 'middle', "margin-right": "15px"},
        ),
    ],
    justify='center',
    style={"margin-top": "18px"}
)
##---TAB 1 Executive report--------------------------------------------------------------------------

product_heading_exe = "Lyve Drive"

exec_report_content = dbc.Card(
    dbc.CardBody(
        [
            html.P(html.U("Executive Report"),
                   style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),
            html.P(html.H5(id="product_heading_exe"), className="card-text", ),
            html.P(html.H5(id="build_heading_exe"), className="card-text", ),
            html.P(html.H5(id="date_heading_exe"), className="card-text", ),
            html.P("Reported Bugs", style=dict_style_table_caption),
            html.Div(id="table_reported_bugs_exe"),
            html.P("Overall QA Report", style=dict_style_table_caption),
            html.Div(id="table_overall_qa_report_exe"),
            html.P("Feature Breakdown Summary", style=dict_style_table_caption),
            html.Div(id="table_feature_breakdown_summary"),
            html.P("Code Maturity", style=dict_style_table_caption),
            html.Div(id="table_code_maturity"),
            html.P("Single Bucket Performance Statistics (Average) using S3Bench - in a Nutshell",
                   style=dict_style_table_caption),
            html.Div(id="table_s3_bucket_perf")
        ]
    ),
    className="flex-sm-fill nav-link",
)

##---TAB 2 Engg report------------------------------------------------------------------------------------------
engg_report_content = dbc.Card(
    dbc.CardBody(
        [
            html.P(html.U("Engineers Report"),
                   style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),
            html.P(html.H5(id="product_heading_eng"), className="card-text", ),
            html.P(html.H5(id="build_heading_eng"), className="card-text", ),
            html.P(html.H5(id="date_heading_eng"), className="card-text"),
            html.P("Reported Bugs", style=dict_style_table_caption),
            html.Div(id="table_reported_bugs_engg"),
            html.P("Overall QA Report", style=dict_style_table_caption),
            html.Div(id="table_overall_qa_report_engg"),
            html.P("Component Level Issues Summary", style=dict_style_table_caption),
            html.Div(id="table_comp_summary"),
            html.P("Timing Summary (seconds)", style=dict_style_table_caption),
            html.Div(id="table_timing_summary"),
            html.P("Single Bucket Performance Statistics (Average) using S3Bench",
                   style=dict_style_table_caption),
            html.Div(id="table_detailed_s3_bucket_perf"),
            html.P("Metadata Latencies(captured with 1KB object)", style=dict_style_table_caption),
            html.Div(id="table_metadata_latency"),
            html.P("Multiple Buckets Performance Statistics (Average) using HSBench and COSBench",
                   style=dict_style_table_caption),
            html.Div(id="table_multi_bucket_perf_stats"),
            html.P("Detail Reported Bugs"),
            html.Div(id="table_detail_reported_bugs")
        ]
    ),
    className="flex-sm-fill nav-link active",
)

##--- TAB3: Input for Test Executionwise defects table ==========================================
testPlan_inputs = dbc.Row(
    dbc.Col(dbc.InputGroup([
        dbc.Input(id="test_execution_input",
                  placeholder="Enter , separated test execution IDs", debounce=True),
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
            html.Th("Detailed Test Execution wise Reported Bugs", id='detailed_report_tab3'),

            dcc.Loading((dbc.Row([dbc.Col(html.Div(id='table_test_execution_wise_defect', className='text-center',
                                                   style={'margin': 20, 'margin-top': 10,
                                                          'margin-bottom': 20}))]))),
        ]
    ),
    className="flex-sm-fill nav-link",
)
##---TAB 4 Performance------------------------------------------------------------------------------------------
performance_content = dbc.Card(
    dbc.CardBody(
        [
            html.P(html.U("Performance"),
                   style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),
        ]
    ),
    className="flex-sm-fill nav-link active",
)

##---TAB 5 Query DB--------------------------------------------------------------------------

query_database = dbc.Card(
    dbc.CardBody(
        [
            html.P(html.U("Query database"),
                   style={'text-align': 'center', 'font-size': '30px', 'font-weight': 'bold'}),
        ]
    ),
    className="flex-sm-fill nav-link active",
)

##---Overall layout-------------------------------------------------------------------
dict_style_tab = {'margin-left': 20, 'margin-right': 20}
dict_style_label = {'font-size': '18px', 'color': '#44cc00', 'background-color': '#343a40'}

tabs = dbc.Tabs(
    [
        dbc.Tab(exec_report_content, label="Executive Report", style=dict_style_tab,
                label_style=dict_style_label),
        dbc.Tab(engg_report_content, label="Engineers Report", style=dict_style_tab,
                label_style=dict_style_label),
        dbc.Tab(defect_list_per_tp_content, label='Defect List for Test Execution Plans',
                style=dict_style_tab,
                label_style=dict_style_label),
        dbc.Tab(performance_content, label='Performance', style=dict_style_tab,
                label_style=dict_style_label),
        dbc.Tab(query_database, label='Query Database', style=dict_style_tab,
                label_style=dict_style_label),
    ],
    className="nav nav nav-pills nav-fill nav-pills flex-column flex-sm-row",
    id="tabs",
)

app.layout = html.Div([
    navbar,
    input_options,
    input_optional_options,
    build_report_header,
    tabs,
    dcc.Location(id='url', refresh=False),
    toast,
    html.Link(
        rel='stylesheet',
        href='/static/topography.css'
    )])


##---Main page callbacks-----------------------------------------------------------------
@app.callback(
    [Output('build_no_dropdown', 'options')],
    [Input('version_dropdown', 'value')],
)
def fetch_build_for_dropdown(value):
    if not value:
        raise PreventUpdate
    if value in ["Beta", "Release"]:
        query_input = {"query": {"buildType": value}, "projection": {"buildNo": "true"}}
        query_input.update(credentials)
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            print("Received response")
            json_response = json.loads(response.text)
            s = []
            for each in json_response["result"]:
                s.append(each["buildNo"])
            s = list(set(s))
            output = [
                {'label': build_no, 'value': build_no} for build_no in s
            ]
            print(" result : {}".format(output))
            return [output]
    return None


@app.callback(
    [Output('test_system_dropdown', 'options')],
    [Input('version_dropdown', 'value')],
    [Input('build_no_dropdown', 'value')]
)
def fetch_test_system_for_dropdown(version, build_no):
    if not (version and build_no):
        raise PreventUpdate
    if version in ["Beta", "Release"]:
        # testPlanLabel corresponds to the system type: for ex: isolated, near full system
        query_input = {"query": {"buildType": version, "buildNo": build_no},
                       "projection": {"testPlanLabel": "true"}}
        query_input.update(credentials)
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            s = []
            for each in json_response["result"]:
                if each["testPlanLabel"]:
                    s.append(each["testPlanLabel"])
            s = list(set(s))
            output = [
                {'label': team, 'value': team} for team in s
            ]
            return [output]
    return None


@app.callback(
    [Output('test_team_dropdown', 'options')],
    [Input('version_dropdown', 'value')],
    [Input('build_no_dropdown', 'value')],
    [Input('test_system_dropdown', 'value')]
)
def fetch_team_for_dropdown(version, build_no, system_type):
    if not (version and build_no and system_type):
        raise PreventUpdate
    if version in ["Beta", "Release"]:
        # testPlanLabel corresponds to the system type: for ex: isolated, near full system
        query_input = {
            "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": system_type},
            "projection": {"testTeam": "true"}}
        query_input.update(credentials)
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            s = []
            for each in json_response["result"]:
                s.append(each["testTeam"])
            s = list(set(s))
            output = [
                {'label': team, 'value': team} for team in s
            ]
            return [output]
    return None


##---Tab 1 Executive reports functions--------------------------------------------------------------
# tab headers
@app.callback(
    [Output('product_heading_exe', 'children'), Output('product_heading_eng', 'children'),
     Output('build_heading_exe', 'children'), Output('build_heading_eng', 'children'),
     Output('date_heading_exe', 'children'), Output('date_heading_eng', 'children')],
    [Input('submit_button', 'n_clicks'),
     Input('version_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_tab_headers(n_clicks, version, build_no, test_system, test_team):
    if n_clicks is None or version is None or build_no is None or test_system is None or test_team is None:
        raise PreventUpdate
    else:
        product_heading = "Product : Lyve Rack"
        build_heading = "Build : " + str(build_no)
        date = "Date : "
        start_of_execution = "-"
        query_input = {
            "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                      "testTeam": test_team},
            "projection": {"testStartTime": True},
            "sort": {"testStartTime": 1}
        }
        query_input.update(credentials)
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            if len(json_response["result"]) > 0:
                start_of_execution = json_response["result"][0]["testStartTime"]
        date = date + str(start_of_execution)
        return product_heading, product_heading, build_heading, build_heading, date, date


# Table : Reported bugs
@app.callback(
    [Output('table_reported_bugs_engg', 'children'),
     Output('table_reported_bugs_exe', 'children')],
    [Input('submit_button', 'n_clicks'),
     Input('version_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_table_reported_bugs(n_clicks, version, build_no, test_system, test_team):
    issue_type = ["Total", "Blocker", "Critical", "Major", "Minor", "Trivial"]
    test_infra_issue_dict = {"Total": 0, "Blocker": 0, "Critical": 0, "Major": 0, "Minor": 0,
                             "Trivial": 0}
    cortx_issue_dict = {"Total": 0, "Blocker": 0, "Critical": 0, "Major": 0, "Minor": 0,
                        "Trivial": 0}

    if n_clicks is None or version is None or build_no is None or test_system is None or test_team is None:
        raise PreventUpdate
    else:
        query_input = {
            "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                      "testTeam": test_team},
            "projection": {"issueID": True}}

        query_input.update(credentials)
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            issue_list = []
            for each in json_response["result"]:
                issue_list.append(each["issueID"])
            print(issue_list)
            issue_list = list(set(issue_list))
            print("Unique list : ", issue_list)

            jira_cred = JIRA({'server': "https://jts.seagate.com/"},
                             basic_auth=(jira_username, jira_password))

            # check issue type and priority
            for issue in issue_list:
                issue_details = jira_cred.issue(issue)
                print("Issue Priority:{}".format(issue_details.fields.priority.name))
                if issue_details.fields.components[0].name == "CFT" or \
                        issue_details.fields.components[
                            0].name == "Automation":
                    test_infra_issue_dict["Total"] = test_infra_issue_dict["Total"] + 1
                    test_infra_issue_dict[issue_details.fields.priority.name] = \
                    test_infra_issue_dict[
                        issue_details.fields.priority.name] + 1
                else:
                    cortx_issue_dict["Total"] = cortx_issue_dict["Total"] + 1
                    cortx_issue_dict[issue_details.fields.priority.name] = cortx_issue_dict[
                                                                               issue_details.fields.priority.name] + 1

            test_infra_issue = test_infra_issue_dict.values()
            cortx_issue = cortx_issue_dict.values()
        else:
            print("Error gen table reported bugs : {}".format(response))
            test_infra_issue = ["-", "-", "-", "-", "-", "-"]
            cortx_issue = ["-", "-", "-", "-", "-", "-"]

        data_reported_bugs = {"Priority": issue_type,
                              "Test Infra Issues": test_infra_issue,
                              "Cortx SW Issues": cortx_issue}

        df_reported_bugs = pd.DataFrame(data_reported_bugs)
        reported_bugs = dash_table.DataTable(
            id="reported_bugs",
            columns=[{"name": i, "id": i} for i in df_reported_bugs.columns],
            data=df_reported_bugs.to_dict('records'),
            style_header=dict_style_header,
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                    {'if': {'row_index': 0}, 'color': '#3498DB'},
                                    {'if': {'row_index': 1}, 'color': '#CB4335'},
                                    {'if': {'row_index': 2}, 'color': '#F39C12'},
                                    {'if': {'row_index': 3}, 'color': '#2874A6'},
                                    {'if': {'row_index': 4}, 'color': '#2E4053'},
                                    {'if': {'row_index': 5}, 'color': '#229954'}
                                    ],
            style_cell=dict_style_cell
        )
        return reported_bugs, reported_bugs


# Table : Overall QA Report
@app.callback(
    [Output('table_overall_qa_report_engg', 'children'),
     Output('table_overall_qa_report_exe', 'children')],
    [Input('submit_button', 'n_clicks'),
     Input('version_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_table_overall_qa_report(n_clicks, version, build_no, test_system, test_team):
    if n_clicks is None or version is None or build_no is None or test_system is None or test_team is None:
        raise PreventUpdate
    else:
        category = ["TOTAL", "PASS", "FAIL", "ABORTED", "BLOCKED", "TODO"]
        current_build = []
        previous_build = []

        # Get current build data
        query_input = {
            "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                      "testTeam": test_team},
            "projection": {"testResult": True}}
        query_input.update(credentials)
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            current_build.append(len(json_response))
            for result_type in category[1:]:
                count = 0
                for each in json_response["result"]:
                    if str(each["testResult"]).lower() == result_type.lower():
                        count = count + 1
                current_build.append(count)
            print("Current build {}".format(current_build))
        else:
            print("Error current build received : {}".format(response))
            current_build = ["-", "-", "-", "-", "-", "-"]

        # Get previous build data
        # TODO change build no to previous build
        query_input = {
            "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                      "testTeam": test_team},
            "projection": {"testResult": True}}
        query_input.update(credentials)
        print("Query :{}".format(query_input))
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            previous_build.append(len(json_response))
            for result_type in category[1:]:
                count = 0
                for each in json_response["result"]:
                    if str(each["testResult"]).lower() == result_type.lower():
                        count = count + 1
                previous_build.append(count)
            print("previous build {}".format(previous_build))
        else:
            print("Error previous received : {}".format(response))
            previous_build = ["-", "-", "-", "-", "-", "-"]

        data_overall_qa_report = {"Category": category,
                                  "Current Build": current_build,
                                  "Previous Build": previous_build}
        df_overall_qa_report = pd.DataFrame(data_overall_qa_report)

        overall_qa_report = dash_table.DataTable(
            id="overall_qa_report",
            columns=[{"name": i, "id": i} for i in df_overall_qa_report.columns],
            data=df_overall_qa_report.to_dict('records'),
            style_header=dict_style_header,
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                    {'if': {'row_index': 0}, 'color': '#3498DB'},
                                    {'if': {'row_index': 1}, 'color': '#229954'},
                                    {'if': {'row_index': 2}, 'color': '#CB4335'},
                                    {'if': {'row_index': 3}, 'color': '#2E4053'},
                                    {'if': {'row_index': 4}, 'color': '#F39C12'},
                                    {'if': {'row_index': 5}, 'color': '#a5a5b5'}
                                    ],
            style_cell=dict_style_cell
        )
        return overall_qa_report, overall_qa_report


# Table : Feature Breakdown Summary
@app.callback(
    Output('table_feature_breakdown_summary', 'children'),
    [Input('submit_button', 'n_clicks'),
     Input('version_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_table_feature_breakdown_summary(n_clicks, version, build_no, test_system, test_team):
    if n_clicks is None or version is None or build_no is None or test_system is None or test_team is None:
        raise PreventUpdate
    else:
        query_input = {
            "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                      "testTeam": test_team},
            "projection": {"testResult": True, "feature": True}}
        query_input.update(credentials)
        print("Query :{}".format(query_input))
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            # retrive feature list dynamically
            feature_list = []
            json_response = json.loads(response.text)
            for each in json_response["result"]:
                feature_list.append(each["feature"])
            feature_list = list(set(feature_list))
            pass_count_list = []
            fail_count_list = []
            total_count_list = []
            for feature in feature_list:
                pass_count = 0
                fail_count = 0
                for each in json_response["result"]:
                    if each["feature"] == feature and each["testResult"].lower() == "pass":
                        pass_count = pass_count + 1
                    elif each["feature"] == feature and each["testResult"].lower() == "fail" or \
                            each[
                                "testResult"].lower() == "blocked":
                        fail_count = fail_count + 1
                    else:
                        pass
                pass_count_list.append(pass_count)
                fail_count_list.append(fail_count)
                total_count_list.append(pass_count + fail_count)

            # add total as last row of table
            feature_list.append("Total")
            pass_count_list.append(sum(pass_count_list))
            fail_count_list.append(sum(fail_count_list))
            total_count_list.append(sum(total_count_list))

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
            df_feature_breakdown_summary["% Passed"] = (
                    df_feature_breakdown_summary["Passed"] / df_feature_breakdown_summary[
                "Total"] * 100)
            df_feature_breakdown_summary["% Failed"] = (df_feature_breakdown_summary["Failed"] /
                                                        df_feature_breakdown_summary["Total"] * 100)

            feature_breakdown_summary = dash_table.DataTable(
                id="feature_breakdown_summary",
                columns=[{"name": i, "id": i} for i in df_feature_breakdown_summary.columns],
                data=df_feature_breakdown_summary.to_dict('records'),
                style_header=dict_style_header,
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                        {'if': {'row_index': len(total_count_list)},
                                         'backgroundColor': "#c1c1d6"},
                                        {'if': {'column_id': "Feature"},
                                         'backgroundColor': "#b9b9bd"}
                                        ],
                style_cell=dict_style_cell
            )
            return feature_breakdown_summary


# Table : Code Maturity
@app.callback(
    Output('table_code_maturity', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_code_maturity(n_clicks):
    # TODO query database as per the input
    if n_clicks is None:
        raise PreventUpdate
    data_code_maturity = {"Category": ["Total", "Pass", "Fail", "Aborted", "Blocked"],
                          "Current Build": ["1", "2", "3", "4", "5"],
                          "Prev Build": ["1", "2", "3", "4", "5"],
                          "Prev Build 1": ["1", "2", "3", "4", "5"],
                          "Prev Build 2": ["1", "2", "3", "4", "5"],
                          }
    df_code_maturity = pd.DataFrame(data_code_maturity)
    code_maturity = dash_table.DataTable(
        id="code_maturity",
        columns=[{"name": i, "id": i} for i in df_code_maturity.columns],
        data=df_code_maturity.to_dict('records'),
        style_header=dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Category"}, 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=dict_style_cell
    )
    return code_maturity


# Table : Single Bucket Performance Statistics using S3bencZh
@app.callback(
    Output('table_s3_bucket_perf', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_s3_bucket_perf(n_clicks):
    # TODO query database as per the input

    data_s3_bucket_perf = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)"],
        "4KB Object": ["1", "2", "3", "4"],
        "256MB Object": ["1", "2", "3", "4"],
    }
    df_s3_bucket_perf = pd.DataFrame(data_s3_bucket_perf)
    s3_bucket_perf = dash_table.DataTable(
        id="code_maturity",
        columns=[{"name": i, "id": i} for i in df_s3_bucket_perf.columns],
        data=df_s3_bucket_perf.to_dict('records'),
        style_header=dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Statistics"}, 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=dict_style_cell
    )
    return s3_bucket_perf


##---Tab 2 Engineers Report functions ------------------------------------------------------------------------------------
# Table : Reported Bugs : gen_table_reported_bugs --> Callback same as tab 1
# Table : Overall QA Report : gen_table_overall_qa_report --> Callback same as tab 1

# Table : Component level summary
@app.callback(
    Output('table_comp_summary', 'children'),
    [Input('submit_button', 'n_clicks'),
     Input('version_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_table_comp_summary(n_clicks, version, build_no, test_system, test_team):
    if n_clicks is None or version is None or build_no is None or test_system is None or test_team is None:
        raise PreventUpdate
    else:
        component_list = ["S3", "Provisioner", "CSM", "RAS", "Motr", "HA"]
        cur_build_dict = {"S3": 0, "Provisioner": 0, "CSM": 0, "RAS": 0, "Motr": 0, "HA": 0}
        prev_build_dict = {"S3": 0, "Provisioner": 0, "CSM": 0, "RAS": 0, "Motr": 0, "HA": 0}

        query_input = {
            "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                      "testTeam": test_team},
            "projection": {"issueID": True}}

        query_input.update(credentials)
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            issue_list = []
            for each in json_response["result"]:
                issue_list.append(each["issueID"])
            print(issue_list)
            issue_list = list(set(issue_list))
            print("Unique list : ", issue_list)

            jira_cred = JIRA({'server': "https://jts.seagate.com/"},
                             basic_auth=(jira_username, jira_password))

            # check issue type and priority
            for issue in issue_list:
                issue_details = jira_cred.issue(issue)
                for comp in cur_build_dict:
                    if issue_details.fields.components[0].name == comp:
                        cur_build_dict[comp] = cur_build_dict[comp] + 1

        data_comp_summary = {
            "Component": component_list,
            "Current Build": cur_build_dict.values(),
            "Previous Build": prev_build_dict.values(),
        }
        df_comp_summary = pd.DataFrame(data_comp_summary)
        comp_summary = dash_table.DataTable(
            id="comp_summary",
            columns=[{"name": i, "id": i} for i in df_comp_summary.columns],
            data=df_comp_summary.to_dict('records'),
            merge_duplicate_headers=True,
            style_header=dict_style_header,
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'}
                                    ],
            style_cell=dict_style_cell
        )
        return comp_summary


# Table : Timing Summary
@app.callback(
    Output('table_timing_summary', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_timing_summary(n_clicks):
    # TODO query database as per the input
    data_timing_summary = {
        "Task": ["Update", "Deployment", "Boxing", "Unboxing", "Onboarding", "Firmware Update",
                 "Bucket Creation",
                 "Bucket Deletion"],
        "Current Build": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "Prev Build": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "Prev Build 1": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "Prev Build 2": ["1", "2", "3", "4", "5", "6", "7", "8"],
    }
    df_timing_summary = pd.DataFrame(data_timing_summary)
    timing_summary = dash_table.DataTable(
        id="timing_summary",
        columns=[{"name": i, "id": i} for i in df_timing_summary.columns],
        data=df_timing_summary.to_dict('records'),
        style_header=dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Task"}, 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=dict_style_cell
    )
    return timing_summary


# Table : Single Bucket Performance Statistics (Average) using S3Bench (Detailed)
@app.callback(
    Output('table_detailed_s3_bucket_perf', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_detailed_s3_bucket_perf(n_clicks):
    # TODO query database as per the input
    data_detailed_s3_bucket_perf = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS", "Write TTFB(ms)", "Read TTFB(ms)"],
        "4KB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "100KB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "1MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "5MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "36MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "64MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "128MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
        "256MB": ["1", "2", "3", "4", "5", "6", "7", "8"],
    }
    df_detailed_s3_bucket_perf = pd.DataFrame(data_detailed_s3_bucket_perf)
    detailed_s3_bucket_perf = dash_table.DataTable(
        id="detailed_s3_bucket_perf",
        columns=[{"name": i, "id": i} for i in df_detailed_s3_bucket_perf.columns],
        data=df_detailed_s3_bucket_perf.to_dict('records'),
        style_header=dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Statistics"}, 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=dict_style_cell
    )
    return detailed_s3_bucket_perf


# Table : Metadata Latencies
@app.callback(
    Output('table_metadata_latency', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_metadata_latency(n_clicks):
    # TODO query database as per the input
    data_metadata_latency = {
        "Operation Latency": ["Add/Edit Object Tags", "Read Object Tags", "Read Object Metadata"],
        "Response Time(ms)": ["1", "2", "3"],
        }
    df_metadata_latency = pd.DataFrame(data_metadata_latency)
    metadata_latency = dash_table.DataTable(
        id="metadata_latency",
        columns=[{"name": i, "id": i} for i in df_metadata_latency.columns],
        data=df_metadata_latency.to_dict('records'),
        style_header=dict_style_header,
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'},
                                {'if': {'column_id': "Operation Latency"},
                                 'backgroundColor': "#b9b9bd"}
                                ],
        style_cell=dict_style_cell
    )
    return metadata_latency


##Add rows to table
##As row span feature is not supported in datatable, added different dataframe for each subcomponent(sharing the same row)
def get_df_to_rows(df, row_span_text, no_of_rows_to_span):
    rows = []
    for i in range(len(df)):
        row = []
        if i == 0:
            row.append(html.Td(row_span_text, rowSpan=no_of_rows_to_span))
        for col in df.columns:
            value = df.iloc[i][col]
            row.append(html.Td(children=value))
        rows.append(html.Tr(row))
    return rows


# Table : Multiple Buckets Performance Statistics(Average) using HSBench and COSBench
@app.callback(
    Output('table_multi_bucket_perf_stats', 'children'),
    [Input('submit_button', 'n_clicks')]
)
def gen_table_multi_bucket_perf_stats(n_clicks):
    # TODO query database as per the input

    final_rows = []

    ##HS bench 1 bucket 1000 Objects 100 Sessions
    data_1 = {"Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                             "Read Latency(ms)",
                             "Write IOPS", "Read IOPS"],
              "4KB": ["1", "2", "3", "4", "5", "6"],
              "100KB": ["1", "2", "3", "4", "5", "6"],
              "1MB": ["1", "2", "3", "4", "5", "6"],
              "5MB": ["1", "2", "3", "4", "5", "6"],
              "36MB": ["1", "2", "3", "4", "5", "6"],
              "64MB": ["1", "2", "3", "4", "5", "6"],
              "128MB": ["1", "2", "3", "4", "5", "6"],
              "256MB": ["1", "2", "3", "4", "5", "6"],
              }
    df_1 = pd.DataFrame(data_1)
    text = ["Hsbench", html.Br(), "1 Buckets", html.Br(), "100 Objects", html.Br(), "100 Sessions"]
    final_rows.extend(get_df_to_rows(df_1, text, 6))

    ## HS bench 10 bucket 100 Objects 100 Sessions
    data_2 = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    df_2 = pd.DataFrame(data_2)
    text = ["Hsbench", html.Br(), "10 Buckets", html.Br(), "100 Objects", html.Br(), "100 Sessions"]
    final_rows.extend(get_df_to_rows(df_2, text, 6))

    ## HS bench 50 bucket 100 Objects 100 Sessions
    data_3 = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    df_3 = pd.DataFrame(data_3)
    text = ["Hsbench", html.Br(), "50 Buckets", html.Br(), "100 Objects", html.Br(), "100 Sessions"]
    final_rows.extend(get_df_to_rows(df_3, text, 6))

    ## Cosbench 1 bucket 100 Objects 100 Sessions
    data_4 = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    df_4 = pd.DataFrame(data_4)
    text = ["Cosbench", html.Br(), "1 Buckets", html.Br(), "100 Objects", html.Br(), "100 Sessions"]
    final_rows.extend(get_df_to_rows(df_4, text, 6))

    ## Cosbench 10 bucket 100 Objects 100 Sessions
    data_5 = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    df_5 = pd.DataFrame(data_5)
    text = ["Cosbench", html.Br(), "10 Buckets", html.Br(), "100 Objects", html.Br(),
            "100 Sessions"]
    final_rows.extend(get_df_to_rows(df_5, text, 6))

    ## Cosbench 50 bucket 100 Objects 100 Sessions
    data_6 = {
        "Statistics": ["Write Throughput(MBps)", "Read Throughput(MBps)", "Write Latency(ms)",
                       "Read Latency(ms)",
                       "Write IOPS", "Read IOPS"],
        "4KB": ["1", "2", "3", "4", "5", "6"],
        "100KB": ["1", "2", "3", "4", "5", "6"],
        "1MB": ["1", "2", "3", "4", "5", "6"],
        "5MB": ["1", "2", "3", "4", "5", "6"],
        "36MB": ["1", "2", "3", "4", "5", "6"],
        "64MB": ["1", "2", "3", "4", "5", "6"],
        "128MB": ["1", "2", "3", "4", "5", "6"],
        "256MB": ["1", "2", "3", "4", "5", "6"],
    }
    df_6 = pd.DataFrame(data_6)
    text = ["Cosbench", html.Br(), "50 Buckets", html.Br(), "100 Objects", html.Br(),
            "100 Sessions"]
    final_rows.extend(get_df_to_rows(df_6, text, 6))

    columns = ["Bench"]
    columns.extend(df_1.columns)
    headers = [html.Thead(html.Tr([html.Th(col) for col in columns]))]
    table_body = [html.Tbody(final_rows)]
    table = dbc.Table(headers + table_body, bordered=True,
                      className="caption-Top col-xs-6",
                      hover=True,
                      responsive=True,
                      striped=True,
                      style=dict_style_cell)
    return table


# Table : Detailed Reported Bugs
@app.callback(
    Output('table_detail_reported_bugs', 'children'),
    [Input('submit_button', 'n_clicks'),
     Input('version_dropdown', 'value'),
     Input('build_no_dropdown', 'value'),
     Input('test_system_dropdown', 'value'),
     Input('test_team_dropdown', 'value'),
     ]
)
def gen_table_detail_reported_bugs(n_clicks, version, build_no, test_system, test_team):
    if n_clicks is None or version is None or build_no is None or test_system is None or test_team is None:
        raise PreventUpdate
    else:
        query_input = {
            "query": {"buildType": version, "buildNo": build_no, "testPlanLabel": test_system,
                      "testTeam": test_team},
            "projection": {"issueID": True}}

        query_input.update(credentials)
        response = requests.request("GET", search_endpoint, headers=headers,
                                    data=json.dumps(query_input))
        if response.status_code == HTTPStatus.OK:
            json_response = json.loads(response.text)
            issue_list = []
            for each in json_response["result"]:
                issue_list.append(each["issueID"])
            print(issue_list)
            issue_list = list(set(issue_list))
            print("Unique list : ", issue_list)

            jira_cred = JIRA({'server': "https://jts.seagate.com/"},
                             basic_auth=(jira_username, jira_password))

            issue_component_list = []
            issue_name_list = []
            issue_no_list = []
            # check issue type and priority
            for issue in issue_list:
                issue_details = jira_cred.issue(issue)
                print("Issue Priority:{}".format(issue_details.fields.priority.name))
                issue_component_list.append(issue_details.fields.components[0].name)
                issue_name_list.append(issue_details.fields.summary)
                issue_no_list.append(issue)

            data_detail_reported_bugs = {"Issue Component": issue_component_list,
                                         "Issue No": issue_no_list,
                                         "Issue Name": issue_name_list}

            df_detail_reported_bugs = pd.DataFrame(data_detail_reported_bugs)
            detail_reported_bugs = dash_table.DataTable(
                id="detail_reported_bugs",
                columns=[{"name": i, "id": i} for i in df_detail_reported_bugs.columns],
                data=df_detail_reported_bugs.to_dict('records'),
                style_header=dict_style_header,
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'}
                                        ],
                style_cell=dict_style_cell
            )

            return detail_reported_bugs


##---Tab 3 Defect list for test execution flow ------------------------------------------------------------------------------------
# test execution wise defect list
@app.callback(
    Output('table_test_execution_wise_defect', 'children'),
    [Input('test_execution_submit_button', 'n_clicks'),
     Input('test_execution_input', 'value')]
)
def gen_table_execution_wise_defect(n_clicks, te_ids):
    if n_clicks is None or te_ids is None:
        raise PreventUpdate
    else:
        te_list = te_ids.split(",")
        issue_list = []
        issue_component_list = []
        issue_name_list = []
        issue_no_list = []
        issue_priority_list = []
        issue_te_list = []
        for te in te_list:
            query_input = {
                "query": {"testExecutionID": te,
                          "$or": [{"testResult": "FAIL"}, {"testResult": "BLOCKED"}]},
                "projection": {"issueID": True}}
            query_input.update(credentials)
            response = requests.request("GET", search_endpoint, headers=headers,
                                        data=json.dumps(query_input))
            if response.status_code == HTTPStatus.OK:
                json_response = json.loads(response.text)
                for each in json_response["result"]:
                    issue_list.append(each["issueID"])

            print(issue_list)
            issue_list = list(set(issue_list))
            print("Unique list : ", issue_list)

            jira_cred = JIRA({'server': "https://jts.seagate.com/"},
                             basic_auth=(jira_username, jira_password))

            # check issue type and priority
            for issue in issue_list:
                issue_details = jira_cred.issue(issue)
                issue_priority_list.append(issue_details.fields.priority.name)
                issue_component_list.append(issue_details.fields.components[0].name)
                issue_name_list.append(issue_details.fields.summary)
                issue_no_list.append(issue)
                issue_te_list.append(te)

        data_execution_wise_defect = {"Test Execution": issue_te_list,
                                     "Issue No": issue_no_list,
                                     "Issue Component": issue_component_list,
                                     "Issue Name": issue_name_list,
                                     "Issue Priority": issue_priority_list
                                     }
        df_execution_wise_defect = pd.DataFrame(data_execution_wise_defect)
        execution_wise_defect = dash_table.DataTable(
            id="execution_wise_defect",
            columns=[{"name": i, "id": i} for i in df_execution_wise_defect.columns],
            data=df_execution_wise_defect.to_dict('records'),
            style_header=dict_style_header,
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8F8F8'}
                                    ],
            style_cell=dict_style_cell
        )

        return execution_wise_defect

##---Tab 4 Performance ------------------------------------------------------------------------------------


##---Tab 5 Query database ------------------------------------------------------------------------------------
if __name__ == '__main__':
    # run on port 5002
    # app.run_server(host='0.0.0.0', port=5000, threaded=True, debug=False)
    app.run_server(debug=True)
