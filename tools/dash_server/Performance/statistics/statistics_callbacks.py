from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from common import app
from Performance.backend import *


@app.callback(
    Output('statistics_workload', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
)
def update_workload(release, branch, build, nodes,
                    pfull, itrns, custom, n_clicks, sessions, buckets):
    workload = None
    if not (all([release, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        data = {
            'release': release, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'S3bench'
        }

        workload = get_workload_headings(data)

    return workload


@app.callback(
    Output('statistics_s3bench_table', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_s3bench(release, branch, build, nodes, pfull, itrns,
                   custom, n_clicks, sessions, buckets):
    table = None
    if not (all([release, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        data = {
            'release': release, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'S3bench'
        }

        dataframe = get_data_from_database(data)
        table = get_dash_table_from_dataframe(
            dataframe, 's3bench', 'Object Sizes')

    return table


@app.callback(
    Output('statistics_metadata_table', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_metadata(release, branch, build, nodes,
                    pfull, itrns, custom, n_clicks, sessions, buckets):
    table = None
    if not (all([release, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        data = {
            'release': release, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'S3bench',
        }
        dataframe = get_metadata_latencies(data)
        table = get_dash_table_from_dataframe(
            dataframe, 'metadata_s3bench', 'Statistics')

    return table


@app.callback(
    Output('statistics_hsbench_table', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_hsbench(release, branch, build, nodes,
                   pfull, itrns, custom, n_clicks, sessions, buckets):
    table = None
    if not (all([release, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        data = {
            'release': release, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'Hsbench'
        }
        dataframe = get_data_from_database(data)
        table = get_dash_table_from_dataframe(
            dataframe, 'hsbench', 'Object Sizes')

    return table


@app.callback(
    Output('statistics_bucketops_table', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    Input('perf_bucketops_dropdown', 'value'),
    prevent_initial_call=True
)
def update_bucketops(release, branch, build, nodes,
                     pfull, itrns, custom, n_clicks, sessions, buckets, objsize):
    table = None
    if not (all([release, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        data = {
            'release': release, 'build': build, 'branch': branch, 'nodes': nodes,
            'pfull': pfull, 'itrns': itrns, 'custom': custom, 'buckets': buckets,
            'sessions': sessions, 'name': 'Hsbench', 'objsize': objsize
        }
        dataframe = get_bucktops(data)
        table = get_dash_table_from_dataframe(
            dataframe, 'bucketops_hsbench', 'Operations')

    return table


@app.callback(
    Output('statistics_cosbench_table', 'children'),
    Input('perf_release_dropdown', 'value'),
    Input('perf_branch_dropdown', 'value'),
    Input('perf_build_dropdown', 'value'),
    Input('perf_nodes_dropdown', 'value'),
    Input('perf_pfull_dropdown', 'value'),
    Input('perf_iteration_dropdown', 'value'),
    Input('perf_custom_dropdown', 'value'),
    Input('perf_submit_button', 'n_clicks'),
    Input('perf_sessions_dropdown', 'value'),
    Input('perf_buckets_dropdown', 'value'),
    prevent_initial_call=True
)
def update_cosbench(release, branch, build, nodes,
                    pfull, itrns, custom, n_clicks, sessions, buckets):
    table = None
    if not (all([release, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        data = {
            'release': release, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'Cosbench'
        }
        dataframe = get_data_from_database(data)
        table = get_dash_table_from_dataframe(
            dataframe, 'cosbench', 'Object Sizes')

    return table
