from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate

from common import app
from Performance.backend import get_graph_layout, plot_graphs_with_given_data, get_data_for_graphs
from Performance.global_functions import sort_object_sizes_list, sort_builds_list

pallete = {
    '1': ['#0277BD', '#29B6F6'],
    '2': ['#EF6C00', '#FFA726']
}


def get_yaxis_heading(metric):
    """
    function to get y axis heading

    Args:
        metric: performance metric

    Returns:
        string: heading string
    """
    return_val = ""
    if metric == "Throughput":
        return_val = "{} (MBps)".format(metric)
    elif metric == "IOPS":
        return_val = "{}".format(metric)
    else:
        return_val = "{} (ms)".format(metric)

    return return_val


def get_graphs(fig, fig_all, data_frame, operations, plot_data, data,
               metric, x_data_combined, x_actual_data, xfilter_tag, color):
    """
    wrapper function to get graphs plotted

    Args:
        fig: plotly fig to plot graphs on
        fig_all: plotly fig to all plot graphs on
        data_frame: pandas dataframe containing data
        operations: operation list with perf operations
        plot_data: data needed for plotting graphs
        data: data needed for query (from dropdowns)
        metric: performance metric specific to the graph
        x_data_combined: list of combined x axis data with comparison plot
        x_actual_data: current trace specific actual x axis list
        x_filter_tag: internal tag to identify xfilter
        color: trace color
    """
    plot_data['option'] = data[xfilter_tag]
    plot_data['custom'] = data['custom']
    i = 0

    for operation in operations:
        y_data = []
        plot_data['operation'] = operation
        for col in data_frame.columns:
            if col.startswith(" ".join([operation, metric])):
                y_actual_data = data_frame[col]
                break
        data = dict(zip(x_actual_data, y_actual_data))
        for item in x_data_combined:
            try:
                y_data.append(data[item])
            except KeyError:
                y_data.append(None)

        plot_data['color'] = color[i]
        plot_graphs_with_given_data(
            fig, fig_all, x_data_combined, y_data, plot_data)
        i += 1


@app.callback(
    Output('plot_TTFB', 'style'),
    Input('graphs_benchmark_dropdown', 'value'),
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
def update_graphs(n_clicks, xfilter, bench, operation, release1, branch1, option1,
                  nodes1, pfull1, itrns1, custom1, sessions1, buckets1, release2,
                  branch2, option2, nodes2, pfull2, itrns2, custom2, sessions2, buckets2, flag):
    return_val = [None] * 5
    if not n_clicks:
        raise PreventUpdate
    if not all([xfilter, bench, operation]):
        raise PreventUpdate
    if not all([
            branch1, option1, nodes1, itrns1, custom1, sessions1, buckets1]) and pfull1 is None:
        raise PreventUpdate
    if flag:
        if not all([
                branch2, option2, nodes2, itrns2, custom2, sessions2, buckets2]) and pfull2 is None:
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
            data_frame = get_data_for_graphs(data, xfilter, xfilter_tag)
            x_data = list(data_frame.iloc[:, 0])

            if flag:
                df_optional = get_data_for_graphs(
                    data_optional, xfilter, xfilter_tag)
                x_data_optional = list(df_optional.iloc[:, 0])
                x_data_final = x_data + x_data_optional

                if xfilter == 'Build':
                    x_data_final = sort_object_sizes_list(x_data_final)
                else:
                    x_data_final = sort_builds_list(x_data_final)

                get_graphs(fig, fig_all, data_frame, operations,
                           plot_data, data, metric, x_data_final, x_data, xfilter_tag, pallete['1'])
                get_graphs(fig, fig_all, df_optional, operations, plot_data, data_optional, metric,
                           x_data_final, x_data_optional, xfilter_tag, pallete['2'])
                not_plotted = False

            if not_plotted:
                get_graphs(fig, fig_all, data_frame, operations,
                           plot_data, data, metric, x_data, x_data, xfilter_tag, pallete['1'])

            figs.append(fig)

        if bench != 'S3bench':
            figs.append(fig)
        figs.append(fig_all)
        return_val = figs

    return return_val
