from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from Performance.global_functions import get_dict_from_array, get_distinct_keys, get_db_details
from common import app
from Performance.mongodb_api import find_documents

# first dropdown


@app.callback(
    Output('branch_dropdown_first', 'options'),
    Input('release_dropdown_first', 'value'),
    prevent_initial_call=True
)
def update_branches_dropdown(release):
    branches = get_distinct_keys(release, 'Branch', {})
    options = get_dict_from_array(branches, False)
    return options


@app.callback(
    Output('dropdown_first', 'options'),
    Input('filter_dropdown', 'value'),
    Input('release_dropdown_first', 'value'),
    Input('branch_dropdown_first', 'value'),
    prevent_initial_call=True
)
def update_builds_dropdown(xfilter, release, branch):
    if release is None or branch is None or xfilter is None:
        raise PreventUpdate

    versions = None
    if release:
        builds = get_distinct_keys(release, xfilter, {'Branch': branch})
        versions = get_dict_from_array(builds, False)

    return versions


@app.callback(
    Output('configs_dropdown_first', 'options'),
    Output('configs_dropdown_first', 'style'),
    Input('filter_dropdown', 'value'),
    Input('release_dropdown_first', 'value'),
    Input('branch_dropdown_first', 'value'),
    Input('dropdown_first', 'value'),
    Input('benchmark_dropdown_first', 'value'),
    prevent_initial_call=True
)
def update_configs_first(xfilter, release, branch, option1, bench):
    results = []
    style = {'display': 'none'}
    if xfilter is None or release is None or branch is None or option1 is None or bench is None:
        raise PreventUpdate

    elif bench != 'S3bench':
        configs = []

        uri, db_name, db_collection = get_db_details(release)
        query = {
            'Branch': branch, xfilter: option1, 'Name': bench,
        }
        cursor = find_documents(query, uri, db_name, db_collection)

        for doc in cursor:
            pattern = {'Buckets': doc['Buckets'], 'Sessions': doc['Sessions']}
            if pattern not in configs:
                configs.append(pattern)

        for config in configs:
            results.append(
                {
                    'label': "{0} buckets, {1} sessions".format(config['Buckets'], config['Sessions']),
                    'value': "{0}_{1}".format(config['Buckets'], config['Sessions'])
                })
        style = {'display': 'block', 'width': '250px', 'verticalAlign': 'middle',
                 "margin-right": "10px", "margin-top": "10px"}

    else:
        style = {'display': 'none'}

    return results, style

# second dropdown


@app.callback(
    [Output('release_dropdown_second', 'style'),
     Output('branch_dropdown_second', 'style'),
     Output('dropdown_second', 'style')],
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def return_States(value):
    style = [{'display': 'none'}] * 3
    if value:
        style = [{'width': '200px', 'verticalAlign': 'middle',
                  "margin-right": "10px", "margin-top": "10px"}] * 3

    return style


@app.callback(
    Output('branch_dropdown_second', 'options'),
    Input('release_dropdown_second', 'value'),
    Input('compare_flag', 'value')
)
def update_second_branch_dropdown(release, flag):
    options = None
    if release is None or not flag:
        raise PreventUpdate

    if flag:
        branches = get_distinct_keys(release, 'Branch', {})
        options = get_dict_from_array(branches, False)

    return options


@app.callback(
    Output('dropdown_second', 'options'),
    Input('filter_dropdown', 'value'),
    Input('release_dropdown_second', 'value'),
    Input('branch_dropdown_second', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_second_builds_dropdown(xfilter, release, branch, flag):
    versions = None
    if release is None or branch is None or xfilter is None or not flag:
        raise PreventUpdate

    if flag and release:
        builds = get_distinct_keys(release, xfilter, {'Branch': branch})
        versions = get_dict_from_array(builds, False)

    return versions
