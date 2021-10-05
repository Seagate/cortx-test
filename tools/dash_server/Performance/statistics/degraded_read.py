# !/usr/bin/python

from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
from common import app
from Performance.backend import get_dash_table_from_dataframe, get_data_for_degraded_stats

@app.callback(
    Output('statistics_s3bench_degraded_throughput', 'children'),
    Output('statistics_s3bench_degraded_iops', 'children'),
    Output('statistics_s3bench_degraded_latency', 'children'),
    Output('statistics_s3bench_degraded_ttfb', 'children'),
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
def update_degraded_read_s3bench(release, branch, build, nodes, pfull, itrns,
                   custom, n_clicks, sessions, buckets):
    tables = [None, None, None]
    if not (all([release, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        tables = []
        data = {
            'release': release, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'S3bench', 'degraded_cluster': True
        }

        dataframes = get_data_for_degraded_stats(data)
        for dataframe in dataframes:
            table = get_dash_table_from_dataframe(
                dataframe, 's3bench', 'Object Sizes')
            tables.append(table)

    return tables

@app.callback(
    [Output('statistics_hsbench_degraded_throughput', 'children'),
    Output('statistics_hsbench_degraded_iops', 'children'),
    Output('statistics_hsbench_degraded_latency', 'children')],
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
def update_degraded_read_hsbench(release, branch, build, nodes, pfull, itrns,
                   custom, n_clicks, sessions, buckets):
    tables = [None, None, None]
    if not (all([release, branch, build, nodes, itrns, custom, n_clicks, sessions, buckets])) and pfull is None:
        raise PreventUpdate

    if n_clicks > 0:
        tables = []
        data = {
            'release': release, 'build': build, 'branch': branch,
            'nodes': nodes, 'pfull': pfull, 'itrns': itrns, 'custom': custom,
            'buckets': buckets, 'sessions': sessions, 'name': 'Hsbench', 'degraded_cluster': True
        }

        dataframes = get_data_for_degraded_stats(data)
        for dataframe in dataframes:
            table = get_dash_table_from_dataframe(
                dataframe, 'Hsbench', 'Object Sizes')
            tables.append(table)

    return tables