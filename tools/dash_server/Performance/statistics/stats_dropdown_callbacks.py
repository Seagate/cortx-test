from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from common import app

from Performance.global_functions import get_dict_from_array, get_distinct_keys, sort_builds_list, sort_object_sizes_list


@app.callback(
    Output('perf_branch_dropdown', 'options'),
    Output('perf_branch_dropdown', 'value'),
    Output('perf_branch_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    prevent_initial_call=True
)
def update_branches_dropdown(release):
    options = None
    value = None
    disabled = False
    if release is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        branches = get_distinct_keys(release, 'Branch', {})
        if branches:
            options = get_dict_from_array(branches, False)
            if 'Release' in branches:
                value = 'Release'
            elif 'stable' in branches:
                value = 'stable'
            elif 'custom' in branches:
                value = 'custom'
            else:
                value = options[0]['value']
            if len(options) == 1:
                disabled = True

        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_build_dropdown', 'options'),
    Output('perf_build_dropdown', 'value'),
    Output('perf_build_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    prevent_initial_call=True
)
def update_builds_dropdown(release, branch):
    versions = None
    value = None
    disabled = False
    if not all([branch, release]): # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        builds = get_distinct_keys(release, 'Build', {'Branch': branch})
        if builds:
            builds = sort_builds_list(builds)
            versions = get_dict_from_array(builds, True)
            value = versions[0]['value']
            if len(builds) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return versions, value, disabled


@app.callback(
    Output('perf_nodes_dropdown', 'options'),
    Output('perf_nodes_dropdown', 'value'),
    Output('perf_nodes_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    prevent_initial_call=True
)
def update_nodes_dropdown(release, branch, build):
    options = None
    value = None
    disabled = False
    if not all([branch, build]): # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        nodes = get_distinct_keys(release, 'Count_of_Servers', {
                                  'Branch': branch, 'Build': build})
        nodes = list(map(int, nodes))
        if nodes:
            options = get_dict_from_array(nodes, False, 'nodes')
            value = options[0]['value']
            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_pfull_dropdown', 'options'),
    Output('perf_pfull_dropdown', 'value'),
    Output('perf_pfull_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    prevent_initial_call=True
)
def update_percentfill_dropdown(release, branch, build, nodes):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes]): # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        pfulls = get_distinct_keys(release, 'Percentage_full', {
                                   'Branch': branch, 'Build': build, 'Count_of_Servers': nodes})
        if pfulls:
            options = get_dict_from_array(pfulls, False, 'pfill')
            value = options[0]['value']
            if len(pfulls) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_iteration_dropdown', 'options'),
    Output('perf_iteration_dropdown', 'value'),
    Output('perf_iteration_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    prevent_initial_call=True
)
def update_iteration_dropdown(release, branch, build, nodes, pfull):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes]) and pfull is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        iterations = get_distinct_keys(release, 'Iteration', {
                                       'Branch': branch, 'Build': build, 'Count_of_Servers': nodes, 'Percentage_full': pfull})
        if iterations:
            options = get_dict_from_array(iterations, False, 'itrns')
            value = options[0]['value']
            if len(iterations) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_custom_dropdown', 'options'),
    Output('perf_custom_dropdown', 'value'),
    Output('perf_custom_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    prevent_initial_call=True
)
def update_custom_dropdown(release, branch, build, nodes, pfull, itrns):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes, itrns]) and pfull is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        custom = get_distinct_keys(release, 'Custom', {
                                   'Branch': branch, 'Build': build, 'Count_of_Servers': nodes, 'Percentage_full': pfull, 'Iteration': itrns})
        if custom:
            options = get_dict_from_array(custom, False)
            value = options[0]['value']
            if len(custom) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_sessions_dropdown', 'options'),
    Output('perf_sessions_dropdown', 'value'),
    Output('perf_sessions_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    prevent_initial_call=True
)
def update_sessions_dropdown(release, branch, build, nodes, pfull, itrns, custom):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes, itrns]) and pfull is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        sessions = get_distinct_keys(release, 'Sessions', {
            'Branch': branch, 'Build': build, 'Count_of_Servers': nodes,
            'Percentage_full': pfull, 'Iteration': itrns, 'Custom': custom
        })
        if sessions:
            options = get_dict_from_array(sessions, False, 'sessions')
            value = options[0]['value']
            if len(sessions) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_buckets_dropdown', 'options'),
    Output('perf_buckets_dropdown', 'value'),
    Output('perf_buckets_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_sessions_dropdown', 'value'),
    prevent_initial_call=True
)
def update_buckets_dropdown(release, branch, build, nodes, pfull, itrns, custom, sessions):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes, itrns, sessions]) and pfull is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        buckets = get_distinct_keys(release, 'Buckets', {
            'Branch': branch, 'Build': build, 'Count_of_Servers': nodes,
            'Percentage_full': pfull, 'Iteration': itrns, 'Custom': custom, 'Sessions': sessions
        })
        if buckets:
            options = get_dict_from_array(buckets, False, 'buckets')
            value = options[0]['value']
            if len(buckets) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('perf_bucketops_dropdown', 'options'),
    Output('perf_bucketops_dropdown', 'value'),
    Output('perf_bucketops_dropdown', 'disabled'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_bucketops_dropdown(release, branch, build, nodes, pfull, itrns, custom, sessions, buckets):
    options = None
    value = None
    disabled = False
    if not all([branch, build, nodes, itrns, sessions, buckets]) and pfull is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        objsizes = get_distinct_keys(release, 'Object_Size', {
            'Branch': branch, 'Build': build, 'Count_of_Servers': nodes, 'Percentage_full': pfull,
            'Iteration': itrns, 'Custom': custom, 'Name': 'Hsbench', 'Buckets': buckets, 'Sessions': sessions
        })
        if objsizes:
            objsizes = sort_object_sizes_list(objsizes)
            options = get_dict_from_array(objsizes, False)
            value = options[0]['value']
            if len(objsizes) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled
