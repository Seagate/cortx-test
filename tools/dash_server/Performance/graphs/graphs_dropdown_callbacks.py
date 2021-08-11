from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate

from Performance.global_functions import get_dict_from_array,\
    get_distinct_keys, get_db_details, get_profiles, sort_builds_list, sort_object_sizes_list
from common import app
from Performance.mongodb_api import find_documents
from Performance.styles import dict_style_profiles

# first dropdown


@app.callback(
    Output('graphs_branch_dropdown', 'options'),
    Input('graphs_release_dropdown', 'value'),
    prevent_initial_call=True
)
def update_branches_dropdown(release):
    branches = get_distinct_keys(release, 'Branch', {})
    options = get_dict_from_array(branches, False)
    return options


@app.callback(
    Output('graphs_build_dropdown', 'options'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    prevent_initial_call=True
)

def update_options_dropdown(xfilter, release, branch):
    if release is None or branch is None or xfilter is None:
        raise PreventUpdate

    versions = None
    if release:
        options = get_distinct_keys(release, xfilter, {'Branch': branch})
        if xfilter == 'Build':
            options = sort_builds_list(options)
            versions = get_dict_from_array(options, True)
        else:
            options = sort_object_sizes_list(options)
            versions = get_dict_from_array(options, False)

    return versions


@app.callback(
    Output('graphs_nodes_dropdown', 'options'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('benchmark_dropdown_first', 'value'),
    prevent_initial_call=True
)
def update_configs_first(xfilter, release, branch, option1, bench):
    results = []
    if xfilter is None or release is None or branch is None or option1 is None or bench is None:
        raise PreventUpdate

    else:
        configs = []

        uri, db_name, db_collection = get_db_details(release)
        query = {
            'Branch': branch, xfilter: option1, 'Name': bench,
        }
        cursor = find_documents(query, uri, db_name, db_collection)

        for doc in cursor:
            try:
                pattern = {'Buckets': int(doc['Buckets']), 'Sessions': int(doc['Sessions'])}

                if pattern not in configs:
                    configs.append(pattern)
            except KeyError:
                continue

        for config in configs:
            results.append(
                {
                    'label': "{0} buckets, {1} sessions".format(config['Buckets'], config['Sessions']),
                    'value': "{0}_{1}".format(config['Buckets'], config['Sessions'])
                })

    return results


@app.callback(
    Output('profiles_options_first', 'style'),
    Input('filter_dropdown', 'value'),
)
def update_profile_style_first(xfilter):
    return_val = {'display': 'none'}
    if xfilter is None:
        raise PreventUpdate

    if xfilter == 'Build':
        return_val = dict_style_profiles

    return return_val


@app.callback(
    Output('profiles_options_first', 'options'),
    Input('release_dropdown_first', 'value'),
    Input('branch_dropdown_first', 'value'),
    Input('dropdown_first', 'value'),
    prevent_initial_call=True
)
def update_profiles_first(release, branch, build):
    return_val = None
    if release is None or branch is None or build is None:
        raise PreventUpdate
    else:
        return_val = get_profiles(release, branch, build)

    return return_val


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
        options = get_distinct_keys(release, xfilter, {'Branch': branch})
        if xfilter == 'Build':
            options = sort_builds_list(options)
            versions = get_dict_from_array(options, True)
        else:
            options = sort_object_sizes_list(options)
            versions = get_dict_from_array(options, False)

    return versions


@app.callback(
    Output('profiles_options_second', 'style'),
    Input('filter_dropdown', 'value'),
    Input('compare_flag', 'value'),
)
def update_profile_style_second(xfilter, flag):
    return_val = {'display': 'none'}
    if xfilter is None or flag is None:
        raise PreventUpdate
    elif xfilter == 'Build' and flag:
        return_val = dict_style_profiles

    return return_val


@app.callback(
    Output('profiles_options_second', 'options'),
    Input('release_dropdown_second', 'value'),
    Input('branch_dropdown_second', 'value'),
    Input('dropdown_second', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_profiles_second(release, branch, build, flag):
    return_val = None
    if release is None or branch is None or build is None or flag is None:
        raise PreventUpdate
    elif flag:
        return_val = get_profiles(release, branch, build)

    return return_val
