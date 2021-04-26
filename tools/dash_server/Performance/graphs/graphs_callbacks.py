from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go

from common import app
from threading import Thread

from Performance.graphs.graphs_functions import get_data_for_graphs, get_metrics, get_yaxis_heading,\
    get_structure_trace, get_operations


def graphs_global(fig, fig_all, xfilter, release1, branch1, option1, bench, config, flag, release2,
                  branch2, option2, operations, x_axis_heading, y_axis_heading, metric, param):

    for op in operations:
        [x_axis, y_data] = get_data_for_graphs(xfilter, release1, branch1, option1, bench,
                                               config, op, metric, param)
        trace = get_structure_trace(
            go.Scatter, op, metric, option1, x_axis, y_data)
        fig.add_trace(trace)
        fig_all.add_trace(trace)

        if flag and release2 and branch2 and option2:
            [x_axis, y_data] = get_data_for_graphs(xfilter, release2, branch2, option2, bench,
                                                   config, op, metric, param)
            trace = get_structure_trace(
                go.Scatter, op, metric, option2, x_axis, y_data)
            fig.add_trace(trace)
            fig_all.add_trace(trace)

    fig.update_layout(
        autosize=True,
        height=625,
        showlegend=True,
        title='{} Plot'.format(metric),
        title_font_size=24,
        title_font_color="blue",
        title_font_family="Sans Serif",
        legend_title='Glossary',
        yaxis=dict(
            title_text=y_axis_heading,
            titlefont=dict(size=20, family="Sans Serif")),
        xaxis=dict(
            title_text=x_axis_heading,
            titlefont=dict(size=20, family="Sans Serif")
        ),
    )


@app.callback(
    Output('plot_TTFB', 'style'),
    Input('benchmark_dropdown_first', 'value'),
    prevent_initial_call=True
)
def update_Ttfb_Style(bench):
    if bench != 'S3bench':
        return {'display': 'none'}
    else:
        return None


@app.callback(
    Output('plot_Throughput', 'figure'),
    Output('plot_Latency', 'figure'),
    Output('plot_IOPS', 'figure'),
    Output('plot_TTFB', 'figure'),
    Output('plot_all', 'figure'),
    Input('get_graphs', 'n_clicks'),
    Input('filter_dropdown', 'value'),
    Input('release_dropdown_first', 'value'),
    Input('branch_dropdown_first', 'value'),
    Input('dropdown_first', 'value'),
    Input('benchmark_dropdown_first', 'value'),
    Input('configs_dropdown_first', 'value'),
    Input('operations_dropdown_first', 'value'),
    Input('compare_flag', 'value'),
    Input('release_dropdown_second', 'value'),
    Input('branch_dropdown_second', 'value'),
    Input('dropdown_second', 'value'),
    prevent_initial_call=True
)
def update_graphs(n_clicks, xfilter, release1, branch1, option1, bench, config, operation,
                  flag, release2, branch2, option2):
    if n_clicks is None or xfilter is None or branch1 is None:
        raise PreventUpdate
        return [None] * 5

    if bench is None or release1 is None or option1 is None or (bench != 'S3bench' and config is None):
        raise PreventUpdate
        return [None] * 5

    if flag:
        if release2 is None or branch2 is None or option2 is None:
            raise PreventUpdate
            return [None] * 5

    if n_clicks > 0:
        figs = []
        fig_all = go.Figure()
        param = None
        if xfilter == 'build':
            x_axis_heading = 'Object Sizes'
        else:
            x_axis_heading = 'Builds'

        operations = get_operations(bench, operation)
        metrics = get_metrics(bench)
        if bench == 'S3bench':
            config = None
        threads = []

        for metric in metrics:
            fig = go.Figure()
            y_axis_heading = get_yaxis_heading(metric)

            if metric in ['Latency', 'TTFB'] and bench != 'Hsbench':
                param = 'Avg'
            else:
                param = None

            temp = Thread(target=graphs_global, args=(fig, fig_all, xfilter, release1, branch1, option1, bench, config, flag, release2,
                                                      branch2, option2, operations, x_axis_heading, y_axis_heading, metric, param))
            temp.start()
            threads.append(temp)
            figs.append(fig)

        for thread in threads:
            thread.join()

        fig_all.update_layout(
            autosize=True,
            height=625,
            showlegend=True,
            title='All Plots in One',
            title_font_size=24,
            title_font_color="blue",
            title_font_family="Sans Serif",
            legend_title='Glossary',
            yaxis=dict(
                title_text='Data',
                titlefont=dict(size=20, family="Sans Serif")),
            xaxis=dict(
                title_text=x_axis_heading,
                titlefont=dict(size=20, family="Sans Serif")
            ),
        )

        if bench != 'S3bench':
            figs.append(fig)
        figs.append(fig_all)

        return figs
    else:
        return [None] * 5
