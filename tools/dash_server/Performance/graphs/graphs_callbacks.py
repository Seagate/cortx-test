from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go

from common import app
from threading import Thread

from Performance.graphs.graphs_functions import get_data_for_graphs, get_metrics, get_yaxis_heading,\
    get_structure_trace, get_operations


def graphs_global(fig, fig_all, xfilter, release1, branch1, option1, profile1, bench, config, flag, release2,
                  branch2, option2, profile2, operations, x_axis_heading, y_axis_heading, metric, param):
    yet_to_plot_traces = True

    for op in operations:
        [x_axis_first, y_data_first] = get_data_for_graphs(xfilter, release1, branch1, option1, profile1, bench,
                                                           config, op, metric, param)

        if flag and release2 and branch2 and option2:
            [x_axis_second, y_data_second] = get_data_for_graphs(xfilter, release2, branch2, option2, profile2, bench,
                                                                 config, op, metric, param)

            if len(x_axis_first) > len(x_axis_second):
                trace = get_structure_trace(
                    go.Scatter, op, metric, option1, x_axis_first, y_data_first)
                fig.add_trace(trace)
                fig_all.add_trace(trace)

                trace = get_structure_trace(
                    go.Scatter, op, metric, option2, x_axis_second, y_data_second)
                fig.add_trace(trace)
                fig_all.add_trace(trace)
            else:
                trace = get_structure_trace(
                    go.Scatter, op, metric, option2, x_axis_second, y_data_second)
                fig.add_trace(trace)
                fig_all.add_trace(trace)

                trace = get_structure_trace(
                    go.Scatter, op, metric, option1, x_axis_first, y_data_first)
                fig.add_trace(trace)
                fig_all.add_trace(trace)

            yet_to_plot_traces = False

        if yet_to_plot_traces:
            trace = get_structure_trace(
                        go.Scatter, op, metric, option1, x_axis_first, y_data_first)
            fig.add_trace(trace)
            fig_all.add_trace(trace)

    fig.update_layout(
        autosize=True,
        height=625,
        showlegend=True,
        title='<b>{} Plot</b>'.format(metric),
        title_font_size=25,
        title_font_color='#343a40',
        legend_title='Glossary',
        yaxis=dict(
            title_text=y_axis_heading,
            titlefont=dict(size=23)),
        xaxis=dict(
            title_text=x_axis_heading,
            titlefont=dict(size=23)
        ),
    )


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
        data = {
            'release': release1, xfilter: option1, 'branch': branch1,
            'nodes': nodes1, 'pfull': pfull1, 'itrns': itrns1, 'custom': custom1,
            'buckets': buckets1, 'sessions': sessions1, 'name': bench
        }

        dataframe = get_data_from_database(data)
        figs = []
        fig_all = go.Figure()
        param = None
        if xfilter == 'Build':
            x_axis_heading = 'Object Sizes'
        else:
            x_axis_heading = 'Builds'

        operations = get_operations(bench, operation)
        metrics = get_metrics(bench)
        threads = []

        for metric in metrics:
            fig = go.Figure()
            y_axis_heading = get_yaxis_heading(metric)

            if metric in ['Latency', 'TTFB'] and bench != 'Hsbench':
                param = 'Avg'
            else:
                param = None

            temp = Thread(target=graphs_global, args=(fig, fig_all, xfilter, release1, branch1, option1, profile1, bench, config, flag, release2,
                                                      branch2, option2, profile2, operations, x_axis_heading, y_axis_heading, metric, param))

            temp.start()
            threads.append(temp)
            figs.append(fig)

        for thread in threads:
            thread.join()

        fig_all.update_layout(
            autosize=True,
            height=625,
            showlegend=True,
            title='<b>All Plots in One</b>',
            title_font_size=25,
            title_font_color='#343a40',
            legend_title='Glossary',
            yaxis=dict(
                title_text='Data',
                titlefont=dict(size=23)),
            xaxis=dict(
                title_text=x_axis_heading,
                titlefont=dict(size=23)
            ),
        )

        if bench != 'S3bench':
            figs.append(fig)
        figs.append(fig_all)

        return_val = figs

    return return_val
