from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from common import app

from Performance.global_functions import get_dict_from_array, get_distinct_keys, get_db_details, sort_builds_list
from Performance.mongodb_api import find_documents


@app.callback(
    Output('perf_branch_dropdown', 'options'),
    Input('perf_release_dropdown', 'value')
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
    Input('perf_branch_dropdown', 'value')
)
def update_builds_dropdown(release, branch):
    versions = None
    if release is None or branch is None:
        raise PreventUpdate
    else:
        builds = get_distinct_keys(release, 'Build', {'Branch': branch})
        versions = get_dict_from_array(
            builds, True)  # sort_builds_list(builds)

    return versions


@app.callback(
    Output('profiles_options', 'options'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value')
)
def update_unique_profiles(release, branch, build):
    # Version_Branch_Build_Iteration_NodeCount_ClientCount_PercentFull_Benchmark_ObjSize_NoOfBuckets_Operation_Sessions
    if release is None or branch is None or build is None:
        raise PreventUpdate
        return {}

    else:
        uri, db_name, db_collection = get_db_details(release)
        pkeys = get_distinct_keys(release, 'PKey', {
            'Branch': branch, 'Build': build
        })

        reference = ('ITR1', '2N', '1C', '0PC', 'NA')
        pkey_split = {}

        for key in pkeys:
            pkey_split[key] = key.split("_")[3:]

        options = []

        for profile_list in list(pkey_split.values()):
            tag = 'Nodes {}, '.format(profile_list[1][:-1])

            if profile_list[2] != reference[2]:
                tag = tag + 'Clients {}, '.format(profile_list[2][:-1])

            tag = tag + 'Filled {}%, '.format(profile_list[3][:-2])
            tag = tag + 'Iteration {}'.format(profile_list[0][3:])
            if profile_list[4] != reference[4]:
                tag = tag + ', {}'.format(profile_list[4])

            option = {'label': tag, 'value': '_'.join(
                [profile_list[0], profile_list[1], profile_list[2], profile_list[3], profile_list[4]])}
            if option not in options:
                options.append(option)

        return options
