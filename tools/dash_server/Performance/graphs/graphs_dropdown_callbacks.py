from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate

from Performance.global_functions import get_dict_from_array,\
    get_distinct_keys, sort_builds_list, sort_object_sizes_list
from common import app
from Performance.styles import style_dropdown_small, style_dropdown_small_2, style_dropdown_medium

# first dropdown


@app.callback(
    Output('graphs_branch_dropdown', 'options'),
    Output('graphs_branch_dropdown', 'value'),
    Output('graphs_branch_dropdown', 'disabled'),
    Input('graphs_release_dropdown', 'value'),
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
    Output('graphs_build_dropdown', 'options'),
    Output('graphs_build_dropdown', 'value'),
    Output('graphs_build_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    prevent_initial_call=True
)
def update_options_dropdown(xfilter, release, branch):
    versions = None
    value = None
    disabled = False
    if not all([xfilter, branch, release]): # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        options = get_distinct_keys(release, xfilter, {'Branch': branch})
        if options:
            if xfilter == 'Build':
                builds = sort_builds_list(options)
                versions = get_dict_from_array(builds, True)
                value = versions[0]['value']
            else:
                obj_sizes = sort_object_sizes_list(options)
                versions = get_dict_from_array(obj_sizes, False)
                value = versions[0]['value']

            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return versions, value, disabled


@app.callback(
    Output('graphs_nodes_dropdown', 'options'),
    Output('graphs_nodes_dropdown', 'value'),
    Output('graphs_nodes_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    prevent_initial_call=True
)
def update_nodes_first(xfilter, release, branch, option1, bench):
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench]): # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        nodes = get_distinct_keys(release, 'Count_of_Servers', {
                                  'Branch': branch, xfilter: option1, 'Name': bench})
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
    Output('graphs_pfull_dropdown', 'options'),
    Output('graphs_pfull_dropdown', 'value'),
    Output('graphs_pfull_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    prevent_initial_call=True
)
def update_percentfill_dropdown(xfilter, release, branch, option1, bench, nodes):
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes]): # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        pfulls = get_distinct_keys(release, 'Percentage_full', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes})
        if pfulls:
            options = get_dict_from_array(pfulls, False, 'pfill')
            value = options[0]['value']
            if len(pfulls) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_iteration_dropdown', 'options'),
    Output('graphs_iteration_dropdown', 'value'),
    Output('graphs_iteration_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    Input('graphs_pfull_dropdown', 'value'),
    prevent_initial_call=True
)
def update_iterations_dropdown(xfilter, release, branch, option1, bench, nodes, pfill):
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes]) and pfill is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        iterations = get_distinct_keys(release, 'Iteration', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes, 'Percentage_full': pfill})
        if iterations:
            options = get_dict_from_array(iterations, False, 'itrns')
            value = options[0]['value']
            if len(iterations) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_custom_dropdown', 'options'),
    Output('graphs_custom_dropdown', 'value'),
    Output('graphs_custom_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    Input('graphs_pfull_dropdown', 'value'),
    Input('graphs_iteration_dropdown', 'value'),
    prevent_initial_call=True
)
def update_custom_dropdown(xfilter, release, branch, option1, bench, nodes, pfill, itrns):
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes, itrns]) and pfill is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        custom = get_distinct_keys(release, 'Custom', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes, 'Percentage_full': pfill, 'Iteration': itrns})
        if custom:
            options = get_dict_from_array(custom, False)
            value = options[0]['value']
            if len(custom) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_sessions_dropdown', 'options'),
    Output('graphs_sessions_dropdown', 'value'),
    Output('graphs_sessions_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    Input('graphs_pfull_dropdown', 'value'),
    Input('graphs_iteration_dropdown', 'value'),
    Input('graphs_custom_dropdown', 'value'),
    prevent_initial_call=True
)
def update_sessions_dropdown(xfilter, release, branch, option1, bench, nodes, pfill, itrns, custom):
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes, itrns, custom]) and pfill is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        sessions = get_distinct_keys(release, 'Sessions', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes, 'Percentage_full': pfill, 'Iteration': itrns, 'Custom': custom})
        if sessions:
            options = get_dict_from_array(sessions, False, 'sessions')
            value = options[0]['value']
            options.append({'label': 'All', 'value': 'all'})
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_buckets_dropdown', 'options'),
    Output('graphs_buckets_dropdown', 'value'),
    Output('graphs_buckets_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    Input('graphs_pfull_dropdown', 'value'),
    Input('graphs_iteration_dropdown', 'value'),
    Input('graphs_custom_dropdown', 'value'),
    Input('graphs_sessions_dropdown', 'value'),
    prevent_initial_call=True
)
def update_buckets_dropdown(xfilter, release, branch, option1, bench, nodes, pfill, itrns, custom, sessions):
    options = None
    value = None
    disabled = False
    if not all([xfilter, branch, option1, bench, nodes, itrns, custom, sessions]) and pfill is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        buckets = get_distinct_keys(release, 'Buckets', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes, 'Percentage_full': pfill, 'Iteration': itrns, 'Custom': custom, 'Sessions': sessions})
        if buckets:
            options = get_dict_from_array(buckets, False, 'buckets')
            value = options[0]['value']
            if len(buckets) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


# second dropdown


@app.callback(
    [Output('graphs_release_compare_dropdown', 'style'),
    Output('graphs_branch_compare_dropdown', 'style'),
    Output('graphs_build_compare_dropdown', 'style'),
    Output('graphs_nodes_compare_dropdown', 'style'),
    Output('graphs_pfull_compare_dropdown', 'style'),
    Output('graphs_iteration_compare_dropdown', 'style'),
    Output('graphs_custom_compare_dropdown', 'style'),
    Output('graphs_sessions_compare_dropdown', 'style'),
    Output('graphs_buckets_compare_dropdown', 'style')],
    Input('compare_flag', 'value'),
)
def update_compare_dropdown_styles(flag):
    if flag:
        return [
                style_dropdown_small, style_dropdown_small_2, style_dropdown_medium,
                style_dropdown_small, style_dropdown_small_2, style_dropdown_small_2,
                style_dropdown_medium, style_dropdown_medium, style_dropdown_medium
        ]
    else:
        return [ {'display': 'None'}]*9

@app.callback(
    Output('graphs_branch_compare_dropdown', 'options'),
    Output('graphs_branch_compare_dropdown', 'value'),
    Output('graphs_branch_compare_dropdown', 'disabled'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_branches_dropdown_2(release, flag):
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
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
    Output('graphs_build_compare_dropdown', 'options'),
    Output('graphs_build_compare_dropdown', 'value'),
    Output('graphs_build_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_options_dropdown(xfilter, release, branch, flag):
    versions = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, release]): # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        options = get_distinct_keys(release, xfilter, {'Branch': branch})
        if options:
            if xfilter == 'Build':
                builds = sort_builds_list(options)
                versions = get_dict_from_array(builds, True)
                value = versions[0]['value']
            else:
                obj_sizes = sort_object_sizes_list(options)
                versions = get_dict_from_array(obj_sizes, False)
                value = versions[0]['value']

            if len(options) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return versions, value, disabled


@app.callback(
    Output('graphs_nodes_compare_dropdown', 'options'),
    Output('graphs_nodes_compare_dropdown', 'value'),
    Output('graphs_nodes_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_nodes_first(xfilter, release, branch, option1, bench, flag):
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench]): # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        nodes = get_distinct_keys(release, 'Count_of_Servers', {
                                  'Branch': branch, xfilter: option1, 'Name': bench})
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
    Output('graphs_pfull_compare_dropdown', 'options'),
    Output('graphs_pfull_compare_dropdown', 'value'),
    Output('graphs_pfull_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_percentfill_dropdown(xfilter, release, branch, option1, bench, nodes, flag):
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes]): # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        pfulls = get_distinct_keys(release, 'Percentage_full', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes})
        if pfulls:
            options = get_dict_from_array(pfulls, False, 'pfill')
            value = options[0]['value']
            if len(pfulls) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_iteration_compare_dropdown', 'options'),
    Output('graphs_iteration_compare_dropdown', 'value'),
    Output('graphs_iteration_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('graphs_pfull_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_iterations_dropdown(xfilter, release, branch, option1, bench, nodes, pfill, flag):
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes]) and pfill is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        iterations = get_distinct_keys(release, 'Iteration', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes, 'Percentage_full': pfill})
        if iterations:
            options = get_dict_from_array(iterations, False, 'itrns')
            value = options[0]['value']
            if len(iterations) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_custom_compare_dropdown', 'options'),
    Output('graphs_custom_compare_dropdown', 'value'),
    Output('graphs_custom_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('graphs_pfull_compare_dropdown', 'value'),
    Input('graphs_iteration_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_custom_dropdown(xfilter, release, branch, option1, bench, nodes, pfill, itrns, flag):
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes, itrns]) and pfill is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        custom = get_distinct_keys(release, 'Custom', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes, 'Percentage_full': pfill, 'Iteration': itrns})
        if custom:
            options = get_dict_from_array(custom, False)
            value = options[0]['value']
            if len(custom) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_sessions_compare_dropdown', 'options'),
    Output('graphs_sessions_compare_dropdown', 'value'),
    Output('graphs_sessions_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('graphs_pfull_compare_dropdown', 'value'),
    Input('graphs_iteration_compare_dropdown', 'value'),
    Input('graphs_custom_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_sessions_dropdown(xfilter, release, branch, option1, bench, nodes, pfill, itrns, custom, flag):
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes, itrns, custom]) and pfill is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        sessions = get_distinct_keys(release, 'Sessions', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes, 'Percentage_full': pfill, 'Iteration': itrns, 'Custom': custom})
        if sessions:
            options = get_dict_from_array(sessions, False, 'sessions')
            value = options[0]['value']
            options.append({'label': 'All', 'value': 'all'})
        else:
            raise PreventUpdate

    return options, value, disabled


@app.callback(
    Output('graphs_buckets_compare_dropdown', 'options'),
    Output('graphs_buckets_compare_dropdown', 'value'),
    Output('graphs_buckets_compare_dropdown', 'disabled'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('graphs_pfull_compare_dropdown', 'value'),
    Input('graphs_iteration_compare_dropdown', 'value'),
    Input('graphs_custom_compare_dropdown', 'value'),
    Input('graphs_sessions_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_buckets_dropdown(xfilter, release, branch, option1, bench, nodes, pfill, itrns, custom, sessions, flag):
    options = None
    value = None
    disabled = False
    if not flag:
        raise PreventUpdate
    if not all([xfilter, branch, option1, bench, nodes, itrns, custom, sessions]) and pfill is None: # pylint: disable=no-else-raise
        raise PreventUpdate
    else:
        buckets = get_distinct_keys(release, 'Buckets', {
                                  'Branch': branch, xfilter: option1, 'Name': bench, 'Count_of_Servers': nodes, 'Percentage_full': pfill, 'Iteration': itrns, 'Custom': custom, 'Sessions': sessions})
        if buckets:
            options = get_dict_from_array(buckets, False, 'buckets')
            value = options[0]['value']
            if len(buckets) == 1:
                disabled = True
        else:
            raise PreventUpdate

    return options, value, disabled

