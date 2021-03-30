#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
# -*- coding: utf-8 -*-
# !/usr/bin/python

from dash.dependencies import Output, Input
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go

from common import app

from Performance.global_functions import get_dict_from_array, get_chain
from Performance.statistics.statistics_functions import fetch_configs_from_file
from Performance.global_functions import benchmark_config

from Performance.graphs.graphs_functions import get_data_based_on_filter, \
    get_operations, get_options, get_structure_trace

traces = []

@app.callback(
    Output('option1_dropdown', 'options'),
    [Input('filter_dropdown', 'value'),
    Input('graphs_version_dropdown', 'value')]
)
def option1_callback(Xfilter, release):
    if Xfilter is None or release is None:
        raise PreventUpdate

    if Xfilter == 'build':
        builds = get_chain(release)
        return get_dict_from_array(builds, True)
    elif Xfilter == 'Object Size':
        Objsize_list = fetch_configs_from_file(benchmark_config, 'S3bench', 'object_size')
        return get_dict_from_array(Objsize_list, False, True)

    return None


@app.callback(
    Output('option2_dropdown', 'options'),
    [Input('filter_dropdown', 'value'),
    Input('graphs_version_dropdown', 'value')],
    prevent_initial_call=True
)
def option2_callback(Xfilter, release):
    if Xfilter is None or release is None:
        raise PreventUpdate

    builds = get_chain(release)
    return get_dict_from_array(builds, True)

@app.callback(
    Output('option2_dropdown', 'style'),
    Input('filter_dropdown', 'value'),
    prevent_initial_call=True
)
def option2_style_callback(xfilter):
    if xfilter is None:
        raise PreventUpdate

    if xfilter == 'build':
        return {'display': 'block', 'width': '160px', 'verticalAlign': 'middle',
                    "margin-right": "10px","margin-top":"10px"}
    else:
        return {'display': 'none'}

@app.callback(
    Output('configs_dropdown', 'style'),
    Input('benchmark_dropdown', 'value'),
    prevent_initial_call=True
)
def update_configs_style(bench):
    if bench == 'S3bench':
        return {'display': 'none'}
    else:
       return {'display': 'block', 'width': '250px', 'verticalAlign': 'middle',
                "margin-right": "10px","margin-top":"10px"}


def graphs_global(bench, operation_opt, option1, option2, xfilter,
                release, configs, titleText, y_axis_test, metric, param=None):
    operations = get_operations(bench, operation_opt)
    options = get_options(option1, option2)
    fig = go.Figure()
    if xfilter == 'Object Size' and bench == 'Cosbench':
        option1 = option1[:-2] + " " + option1[-2:].upper()

    for op in operations:
        for option in options:
            [x_axis, y_data] = get_data_based_on_filter(xfilter,
                                release, option, bench, configs, op, metric, param)
            trace = get_structure_trace(go.Scatter, op, metric, option, x_axis, y_data)
            fig.add_trace(trace)

    fig.update_layout(
        autosize=True,
        height=625,
        showlegend = True,
        title = '{} Plot'.format(metric),
        title_font_size=24,
        title_font_color="blue",
        title_font_family="Sans Serif",
        legend_title= 'Glossary',
        yaxis=dict(
            title_text=y_axis_test,
            titlefont=dict(size=20, family="Sans Serif")),
        xaxis=dict(
            title_text=titleText,
            titlefont=dict(size=20, family="Sans Serif")
        ),
    )

    return fig


@app.callback(
    Output('plot_Throughput', 'figure'),
    [Input('perf_submit_button', 'n_clicks'),
    Input('filter_dropdown', 'value'),
    Input('graphs_version_dropdown', 'value'),
    Input('option1_dropdown', 'value'),
    Input('option2_dropdown', 'value'),
    Input('benchmark_dropdown', 'value'),
    Input('configs_dropdown', 'value'),
    Input('operations_dropdown', 'value')],
    prevent_initial_call=True
)
def update_throughput(n_clicks, xfilter, release, option1, option2, bench, configs, operation_opt):
    return_val = None
    if n_clicks is None or xfilter is None or release is None or option1 is None:
        raise PreventUpdate

    if bench != 'S3bench' and configs is None:
        raise PreventUpdate

    else:
        if xfilter == 'build':
            titleText = 'Object Sizes'
        else:
            titleText = 'Builds'
        fig = graphs_global(bench, operation_opt, option1, option2, xfilter,
                            release, configs, titleText, "Data (MBps)", 'Throughput')

        return_val = fig

    return return_val

@app.callback(
    Output('plot_Latency', 'figure'),
    [Input('perf_submit_button', 'n_clicks'),
    Input('filter_dropdown', 'value'),
    Input('graphs_version_dropdown', 'value'),
    Input('option1_dropdown', 'value'),
    Input('option2_dropdown', 'value'),
    Input('benchmark_dropdown', 'value'),
    Input('configs_dropdown', 'value'),
    Input('operations_dropdown', 'value')],
    prevent_initial_call=True
)
def update_latency(n_clicks, xfilter, release, option1, option2, bench, configs, operation_opt):
    return_val = None
    if n_clicks is None or xfilter is None or release is None or option1 is None:
        raise PreventUpdate

    if bench != 'S3bench' and configs is None:
        raise PreventUpdate

    else:
        if xfilter == 'build':
            titleText = 'Object Sizes'
        else:
            titleText = 'Builds'

        fig = graphs_global(bench, operation_opt, option1, option2, xfilter,
                            release, configs, titleText, "Data (ms)", 'Latency', 'Avg')
        return_val = fig

    return return_val

@app.callback(
    Output('plot_IOPS', 'figure'),
    [Input('perf_submit_button', 'n_clicks'),
    Input('filter_dropdown', 'value'),
    Input('graphs_version_dropdown', 'value'),
    Input('option1_dropdown', 'value'),
    Input('option2_dropdown', 'value'),
    Input('benchmark_dropdown', 'value'),
    Input('configs_dropdown', 'value'),
    Input('operations_dropdown', 'value')],
    prevent_initial_call=True
)
def update_IOPS(n_clicks, xfilter, release, option1, option2, bench, configs, operation_opt):
    return_val = None
    if n_clicks is None or xfilter is None or release is None or option1 is None:
        raise PreventUpdate

    if bench != 'S3bench' and configs is None:
        raise PreventUpdate

    else:
        if xfilter == 'build':
            titleText = 'Object Sizes'
        else:
            titleText = 'Builds'

        fig = graphs_global(bench, operation_opt, option1, option2,
                            xfilter, release, configs, titleText, "Data", 'IOPS')
        return_val = fig

    return return_val

@app.callback(
    Output('plot_TTFB', 'figure'),
    [Input('perf_submit_button', 'n_clicks'),
    Input('filter_dropdown', 'value'),
    Input('graphs_version_dropdown', 'value'),
    Input('option1_dropdown', 'value'),
    Input('option2_dropdown', 'value'),
    Input('benchmark_dropdown', 'value'),
    Input('configs_dropdown', 'value'),
    Input('operations_dropdown', 'value')],
    prevent_initial_call=True
)
def update_TTFB(n_clicks, xfilter, release, option1, option2, bench, configs, operation_opt):
    return_val = None
    if n_clicks is None or xfilter is None or release is None or option1 is None:
        raise PreventUpdate

    if bench != 'S3bench':
        raise PreventUpdate

    else:
        if xfilter == 'build':
            titleText = 'Object Sizes'
        else:
            titleText = 'Builds'

        fig = graphs_global(bench, operation_opt, option1, option2,
                    xfilter, release, configs, titleText, "Data (ms)", 'TTFB', 'Avg')
        return_val = fig

    return return_val

@app.callback(
    Output('plot_all', 'figure'),
    [Input('perf_submit_button', 'n_clicks'),
    Input('filter_dropdown', 'value'),
    Input('graphs_version_dropdown', 'value'),
    Input('option1_dropdown', 'value'),
    Input('option2_dropdown', 'value'),
    Input('benchmark_dropdown', 'value'),
    Input('configs_dropdown', 'value'),
    Input('operations_dropdown', 'value')],
    prevent_initial_call=True
)
def update_all(n_clicks, xfilter, release, option1, option2, bench, configs, operation_opt):
    return_val = None

    if n_clicks is None or xfilter is None or release is None or option1 is None:
        raise PreventUpdate

    else:
        fig = go.Figure()

        operations = get_operations(bench, operation_opt)
        options = get_options(option1, option2)

        if xfilter == 'build':
            titleText = 'Object Sizes'
        else:
            titleText = 'Builds'

        if xfilter == 'Object Size' and bench == 'Cosbench':
            option1 = option1[:-2] + " " + option1[-2:].upper()

        if bench == 'S3bench':
            metrics = ['Throughput', 'Latency', 'IOPS', 'TTFB']
        else:
            metrics = ['Throughput', 'Latency', 'IOPS']

        for metric in metrics:
            if metric in ['Latency', 'TTFB']:
                param = 'Avg'
            else:
                param = None
            for op in operations:
                for option in options:
                    [x_axis, y_data] = get_data_based_on_filter(xfilter,
                                    release, option, bench, configs, op, metric, param)
                    trace = get_structure_trace(go.Scatter, op, metric, option, x_axis, y_data)
                    fig.add_trace(trace)

        fig.update_layout(
            autosize=True,
            height=625,
            showlegend = True,
            title = 'All Plots in One',
            title_font_size=24,
            title_font_color="blue",
            title_font_family="Sans Serif",
            legend_title= 'Glossary',
            yaxis=dict(
                title_text="Data",
                titlefont=dict(size=20, family="Sans Serif")),
            xaxis=dict(
                title_text=titleText,
                titlefont=dict(size=20, family="Sans Serif")
            ),
        )
        return_val = fig

    return return_val
