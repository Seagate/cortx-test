from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from common import app

from Performance.global_functions import get_dict_from_array, get_distinct_keys, sort_builds_list, get_profiles

@app.callback(
    Output('perf_branch_dropdown', 'options'),
    Input('perf_release_dropdown', 'value'),
    prevent_initial_call=True
)
def update_branches_dropdown(release):
    options = None
    if release is None:
        raise PreventUpdate
    else:
        branches = get_distinct_keys(release, 'Branch', {})
        options = get_dict_from_array(branches, False)
    return options


@app.callback(
    Output('perf_build_dropdown', 'options'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    prevent_initial_call=True
)
def update_builds_dropdown(release, branch):
    versions = None
    if release is None or branch is None:
        raise PreventUpdate
    else:
        builds = get_distinct_keys(release, 'Build', {'Branch': branch})
        builds = sort_builds_list(builds)
        versions = get_dict_from_array(builds, True)

    return versions


@app.callback(
    Output('profiles_options', 'options'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    prevent_initial_call=True
)
def update_unique_profiles(release, branch, build):
    options = None
    if release is None or branch is None or build is None:
        raise PreventUpdate
    else:
        options = get_profiles(release, branch, build)
    
    return options
