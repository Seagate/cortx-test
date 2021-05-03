from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go

from common import app
from threading import Thread

from Performance.graphs.graphs_functions import get_data_for_graphs, get_metrics, get_yaxis_heading,\
    get_structure_trace, get_operations


def graphs_global(fig, fig_all, xfilter, release1, branch1, option1, profile1, bench, config, flag, release2,
                  branch2, option2, profile2, operations, x_axis_heading, y_axis_heading, metric, param):

    for op in operations:
        [x_axis, y_data] = get_data_for_graphs(xfilter, release1, branch1, option1, profile1, bench,
                                               config, op, metric, param)
        trace = get_structure_trace(
            go.Scatter, op, metric, option1, x_axis, y_data)
        fig.add_trace(trace)
        fig_all.add_trace(trace)

        if flag and release2 and branch2 and option2:
            [x_axis, y_data] = get_data_for_graphs(xfilter, release2, branch2, option2, profile2, bench,
                                                   config, op, metric, param)
            trace = get_structure_trace(
                go.Scatter, op, metric, option2, x_axis, y_data)
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
    Input('get_graphs', 'n_clicks'),
    Input('filter_dropdown', 'value'),
    Input('release_dropdown_first', 'value'),
    Input('branch_dropdown_first', 'value'),
    Input('dropdown_first', 'value'),
    Input('profiles_options_first', 'value'),
    Input('benchmark_dropdown_first', 'value'),
    Input('configs_dropdown_first', 'value'),
    Input('operations_dropdown_first', 'value'),
    Input('compare_flag', 'value'),
    Input('release_dropdown_second', 'value'),
    Input('branch_dropdown_second', 'value'),
    Input('dropdown_second', 'value'),
    Input('profiles_options_second', 'value'),
    prevent_initial_call=True
)
def update_graphs(n_clicks, xfilter, release1, branch1, option1, profile1, bench, config, operation,
                  flag, release2, branch2, option2, profile2):
    return_val = [None] * 5
    if n_clicks is None or xfilter is None or branch1 is None:
        raise PreventUpdate

    if bench is None or release1 is None or option1 is None or config is None:
        raise PreventUpdate

    if flag:
        if release2 is None or branch2 is None or option2 is None:
            raise PreventUpdate

    if n_clicks > 0:
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
