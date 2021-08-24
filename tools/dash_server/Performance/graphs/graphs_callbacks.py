from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate

from common import app
from Performance.backend import get_graph_layout, plot_graphs_with_given_data, get_data_for_graphs


def get_yaxis_heading(metric):
    if metric == "Throughput":
        return "{} (MBps)".format(metric)
    elif metric == "IOPS":
        return "{}".format(metric)
    else:
        return "{} (ms)".format(metric)


def get_graphs(fig, fig_all, df, operations, plot_data, data, metric, x_data, xfilter_tag):
    plot_data['option'] = data[xfilter_tag]
    plot_data['custom'] = data['custom']
    for operation in operations:
        plot_data['operation'] = operation
        for col in df.columns:
            if col.startswith(" ".join([operation, metric])):
                y_data = df[col]
                break
        plot_graphs_with_given_data(fig, fig_all, x_data, y_data, plot_data)


@app.callback(
    Output('plot_TTFB', 'style'),
    Input('benchmark_dropdown_first', 'value'),
    prevent_initial_call=True
)
def update_Ttfb_Style(bench):
    style = None
    if bench != 'S3bench':
        style = {'display': 'none'}

    return style


@app.callback(
    Output('plot_Throughput', 'figure'),
    Output('plot_Latency', 'figure'),
    Output('plot_IOPS', 'figure'),
    Output('plot_TTFB', 'figure'),
    Output('plot_all', 'figure'),
    Input('graphs_submit_button', 'n_clicks'),
    Input('graphs_filter_dropdown', 'value'),
    Input('graphs_benchmark_dropdown', 'value'),
    Input('graphs_operations_dropdown', 'value'),
    Input('graphs_release_dropdown', 'value'),
    Input('graphs_branch_dropdown', 'value'),
    Input('graphs_build_dropdown', 'value'),
    Input('graphs_nodes_dropdown', 'value'),
    Input('graphs_pfull_dropdown', 'value'),
    Input('graphs_iteration_dropdown', 'value'),
    Input('graphs_custom_dropdown', 'value'),
    Input('graphs_sessions_dropdown', 'value'),
    Input('graphs_buckets_dropdown', 'value'),
    Input('graphs_release_compare_dropdown', 'value'),
    Input('graphs_branch_compare_dropdown', 'value'),
    Input('graphs_build_compare_dropdown', 'value'),
    Input('graphs_nodes_compare_dropdown', 'value'),
    Input('graphs_pfull_compare_dropdown', 'value'),
    Input('graphs_iteration_compare_dropdown', 'value'),
    Input('graphs_custom_compare_dropdown', 'value'),
    Input('graphs_sessions_compare_dropdown', 'value'),
    Input('graphs_buckets_compare_dropdown', 'value'),
    Input('compare_flag', 'value'),
    prevent_initial_call=True
)
def update_graphs(n_clicks, xfilter, bench, operation, release1, branch1, option1, nodes1, pfull1, itrns1, custom1, sessions1, buckets1,
                  release2, branch2, option2, nodes2, pfull2, itrns2, custom2, sessions2, buckets2, flag):
    return_val = [None] * 5
    if not n_clicks:
        raise PreventUpdate
    if not all([xfilter, bench, operation]):
        raise PreventUpdate
    if not all([branch1, option1, nodes1, itrns1, custom1, sessions1, buckets1]) and pfull1 is None:
        raise PreventUpdate
    if flag:
        if not all([branch2, option2, nodes2, itrns2, custom2, sessions2, buckets2]) and pfull2 is None:
            raise PreventUpdate

    if n_clicks > 0:
        plot_data = {}
        figs = []

        if xfilter == 'Build':
            plot_data['x_heading'] = 'Object Sizes'
            xfilter_tag = 'build'
        else:
            plot_data['x_heading'] = 'Builds'
            xfilter_tag = 'objsize'

        data = {
            'release': release1, 'xfilter': xfilter, xfilter_tag: option1, 'branch': branch1,
            'nodes': nodes1, 'pfull': pfull1, 'itrns': itrns1, 'custom': custom1,
            'buckets': buckets1, 'sessions': sessions1, 'name': bench
        }
        if flag:
            data_optional = {
                'release': release2, 'xfilter': xfilter, xfilter_tag: option2, 'branch': branch2,
                'nodes': nodes2, 'pfull': pfull2, 'itrns': itrns2, 'custom': custom2,
                'buckets': buckets2, 'sessions': sessions2, 'name': bench
            }

        if operation == 'both':
            operations = ['Read', 'Write']
        else:
            operations = [operation]

        if bench == 'S3bench':
            stats = ["Throughput", "IOPS", "Latency", "TTFB"]
        else:
            stats = ["Throughput", "IOPS", "Latency"]

        plot_data['metric'] = 'all'
        plot_data['y_heading'] = 'Data'
        fig_all = get_graph_layout(plot_data)

        for metric in stats:
            not_plotted = True
            plot_data['metric'] = metric
            plot_data['y_heading'] = get_yaxis_heading(metric)

            fig = get_graph_layout(plot_data)
            df = get_data_for_graphs(data, xfilter, xfilter_tag)
            x_data = df.iloc[:, 0]

            if flag:
                df_optional = get_data_for_graphs(data_optional, xfilter, xfilter_tag)
                x_data_optional = df_optional.iloc[:, 0]

                if len(x_data) >= len(x_data_optional):
                    get_graphs(fig, fig_all, df, operations,
                                plot_data, data, metric, x_data, xfilter_tag)
                    get_graphs(fig, fig_all, df_optional, operations, plot_data,
                                data_optional, metric, x_data_optional, xfilter_tag)
                    not_plotted = False
                else:
                    get_graphs(fig, fig_all, df_optional, operations, plot_data,
                                data_optional, metric, x_data_optional, xfilter_tag)
                    get_graphs(fig, fig_all, df, operations,
                                plot_data, data, metric, x_data, xfilter_tag)
                    not_plotted = False

            if not_plotted:
                get_graphs(fig, fig_all, df, operations,
                           plot_data, data, metric, x_data, xfilter_tag)

            figs.append(fig)

        figs.append(fig_all)
        return_val = figs

    return return_val
