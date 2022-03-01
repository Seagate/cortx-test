"""Backend functions for Performance tabs"""
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# 
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
# -*- coding: utf-8 -*-
# !/usr/bin/python

from __future__ import absolute_import
import pandas as pd
import dash_table
import dash_html_components as html
import plotly.graph_objs as go

from Performance.schemas import *
from Performance.global_functions import get_distinct_keys, sort_object_sizes_list, \
    sort_builds_list, get_db_details, keys_exists, round_off, check_empty_list, \
    sort_sessions
from Performance.mongodb_api import find_documents, count_documents, get_aggregate
from Performance.styles import style_dashtable_header, style_table_cell


def get_average_data(count, data, stat, subparam, multiplier):
    """
    Returns subparam value (avg/min/max) from passed cursor by multiplying
    with multiplier

    Args:
        count: count of documents available in database
        data: cursor containing queried data
        stat: perf metric to look after
        subparam: to fetch avg/min/max param
        multiplier: multiplies the datapoint with this value

    returns:
        rounded off value
    """
    try:
        if count > 0 and keys_exists(data[0], stat):
            return round_off(data[0][stat][subparam] * multiplier)
        else:
            return "NA"
    except KeyError:
        return "NA"


def get_data(count, data, stat, multiplier):
    """
    returns metric data without subparam

    Args:
        count: count of documents available in database
        data: cursor containing queried data
        stat: perf metric to look after
        multiplier: multiplies the datapoint with this value

    returns:
        rounded off value
    """
    if count > 0 and keys_exists(data[0], stat):
        return round_off(data[0][stat] * multiplier)
    else:
        return "NA"


def get_data_for_stats(data):
    """
    function for statistics tab to get data from database

    Args:
        data: dictionary needed for the query

    Returns:
        dataframe: Pandas dataframe with queried data
    """
    data_needed_for_query = data.copy()
    query = get_statistics_schema(data_needed_for_query)
    objects = get_distinct_keys(
        data_needed_for_query['release'], 'Object_Size', query)
    objects = sort_object_sizes_list(objects)

    if data_needed_for_query['name'] == 'S3bench':
        # stats_headings = statistics_column_headings.copy()
        results = {
            'Object Sizes': statistics_column_headings
        }
    else:
        # mult_headings = multiple_buckets_headings.copy()
        results = {
            'Object Sizes': multiple_buckets_headings
        }

    run_state_list = []
    for obj in objects:
        data_needed_for_query['objsize'] = obj
        temp_data, run_state = get_benchmark_data(data_needed_for_query)
        if not check_empty_list(temp_data):
            run_state_list.append(run_state)
            results[obj] = temp_data

    df = pd.DataFrame(results)
    df = df.T
    df.reset_index(inplace=True)
    df.columns = df.iloc[0]
    df = df[1:]

    return df, run_state_list


def get_data_for_degraded_stats(data):
    """
    function for degraded read tab to get data from database
    Args:
        data: dictionary needed for the query
    Returns:
        dataframe: list of Pandas dataframe with queried data
    """
    data_needed_for_query = data.copy()
    query = get_statistics_schema(data_needed_for_query)
    objects = get_distinct_keys(
        data_needed_for_query['release'], 'Object_Size', query)
    objects = sort_object_sizes_list(objects)
    results = {
        'Throughput':
            {
                'Object Sizes': statistics_column_headings
            },
        'IOPS':
            {
                'Object Sizes': statistics_column_headings
            },
        'Latency':
            {
                'Object Sizes': statistics_column_headings
            },
        'TTFB':
            {
                'Object Sizes': statistics_column_headings
            }
    }
    if data_needed_for_query['name'] != 'S3bench':
        del results['TTFB']

    for obj in objects:
        data_needed_for_query['objsize'] = obj

        if keys_exists(data_needed_for_query, 'degraded_cluster'):
            temp_data = get_degraded_cluster_data(data_needed_for_query)
            if not check_empty_list(temp_data):
                for stat in temp_data:
                    results[stat][obj] = temp_data

    dataframes = []
    for stat in results:
        dataframe = pd.DataFrame(results[stat])
        dataframe = dataframe.T
        dataframe.reset_index(inplace=True)
        dataframe.columns = dataframe.iloc[0]
        dataframe = dataframe[1:]
        dataframes.append(dataframe)

    return dataframes


def get_degraded_cluster_data(data_needed_for_query):
    """
    function to organise and get data required for degraded cluster view

    Args:
        data: dictionary needed for the query

    Returns:
        results: dictionary with data for this particular instance
    """
    temp_data = {}
    data_needed_for_query['operation'] = 'Read'
    cluster_states = ['normal-read', 'degraded-read', 'recovered-read']

    if data_needed_for_query["name"] == 'S3bench':
        stats = ["Throughput", "IOPS", "Latency", "TTFB"]
    else:
        stats = ["Throughput", "IOPS", "Latency"]

    for stat in stats:
        temp_data[stat] = []

    uri, db_name, db_collection = get_db_details(
        data_needed_for_query['release'])

    for state in cluster_states:
        data_needed_for_query['cluster_state'] = state
        query = get_degraded_schema(data_needed_for_query)
        count = count_documents(query=query, uri=uri, db_name=db_name,
                                collection=db_collection)
        db_data = find_documents(query=query, uri=uri, db_name=db_name,
                                 collection=db_collection)

        for stat in stats:
            if data_needed_for_query["name"] == 'S3bench' and stat in ["Latency", "TTFB"]:
                temp_data[stat].append(get_average_data(
                    count, db_data, stat, "Avg", 1000))
            elif data_needed_for_query["name"] == 'S3bench':
                temp_data[stat].append(get_data(count, db_data, stat, 1))
            else:
                try:
                    temp_data[stat].append(get_data(count, db_data, stat, 1))
                except TypeError:
                    temp_data[stat].append(get_average_data(
                        count, db_data, stat, "Avg", 1))

    return temp_data


def get_data_for_graphs(data, xfilter, xfilter_tag):
    """
    function for graphs tab to get data from database

    Args:
        data: dictionary needed for the query
        xfilter: filter provided
        xfilter_tag: internal tag needed for xfilter for data query

    Returns:
        dataframe: Pandas dataframe with queried data
    """
    data_needed_for_query = data.copy()

    if data_needed_for_query['sessions'] == 'all' or data_needed_for_query['all_sessions_plot']:
        query = get_multi_concurrency_schema(data, xfilter, xfilter_tag)
        sessions = get_distinct_keys(
            data_needed_for_query['release'], 'Sessions', query)
        sessions = sort_sessions(sessions)

        if data_needed_for_query['name'] == 'S3bench':
            results = {
                'Concurrency': statistics_column_headings
            }
        else:
            results = {
                'Concurrency': multiple_buckets_headings
            }

        for session in sessions:
            data_needed_for_query['sessions'] = session
            temp_data, _ = get_benchmark_data(data_needed_for_query)
            if not check_empty_list(temp_data):
                results[session] = temp_data

    elif xfilter == 'Build':
        query = get_graphs_schema(data_needed_for_query, xfilter, xfilter_tag)
        objects = get_distinct_keys(
            data_needed_for_query['release'], 'Object_Size', query)
        objects = sort_object_sizes_list(objects)

        if data_needed_for_query['name'] == 'S3bench':
            results = {
                'Object Sizes': statistics_column_headings
            }
        else:
            results = {
                'Object Sizes': multiple_buckets_headings
            }

        for obj in objects:
            data_needed_for_query['objsize'] = obj
            temp_data, _ = get_benchmark_data(data_needed_for_query)
            if not check_empty_list(temp_data):
                results[obj] = temp_data
    else:
        query = get_graphs_schema(data_needed_for_query, xfilter, xfilter_tag)
        builds = get_distinct_keys(
            data_needed_for_query['release'], 'Build', query)
        builds = sort_builds_list(builds)

        if data_needed_for_query['name'] == 'S3bench':
            results = {
                'Builds': statistics_column_headings
            }
        else:
            results = {
                'Builds': multiple_buckets_headings
            }
        for build in builds:
            data_needed_for_query['build'] = build
            temp_data, _ = get_benchmark_data(data_needed_for_query)
            if not check_empty_list(temp_data):
                results[build] = temp_data

    dataframe = pd.DataFrame(results)
    dataframe = dataframe.T
    dataframe.reset_index(inplace=True)
    dataframe.columns = dataframe.iloc[0]
    dataframe = dataframe[1:]
    return dataframe


def get_benchmark_data(data_needed_for_query):  # pylint: disable=too-many-branches
    """
    Granularized function to query data from database for perf metrics

    Args:
        data: dictionary needed for the query

    Returns:
        results: dictionary to with appended data for this particular instance
    """
    temp_data = []
    run_state = "successful"
    added_objects = "NA"
    skipttfb = True
    operations = ["Read", "Write"]


    uri, db_name, db_collection = get_db_details(
        data_needed_for_query['release'])

    for operation in operations:
        data_needed_for_query['operation'] = operation

        query = get_complete_schema(data_needed_for_query)
        group_query = {
            "_id": "null",
            "total_objs": { "$sum": "$Objects"},
            "sum_throughput": {"$sum": "$Throughput"},
            "sum_iops": {"$sum": "$IOPS"},
            "avg_lat": {"$avg": "$Latency"},
            "avg_lat_avg": {"$avg": "$Latency.Avg"},
            "run_state": { "$addToSet": "$Run_State"},
            "avg_ttfb_avg": {"$avg": "$TTFB.Avg"},
            "avg_ttfb_99p": {"$avg": "$TTFB.Avg"},
            }

        cursor = get_aggregate(query=query, group_query=group_query, uri=uri, db_name=db_name,
                        collection=db_collection)
        if not cursor:
            cursor = {
            "_id": "null", "total_objs": "NA", "sum_throughput": "NA", "sum_iops": "NA",
            "avg_lat": "NA", "avg_lat_avg": "NA", "run_state": "NA", "avg_ttfb_avg": "NA",
            "avg_ttfb_99p": "NA"}

        if cursor['total_objs'] != "NA":
            added_objects = cursor['total_objs']
        if 'failed' in cursor['run_state']:
            run_state = 'failed'

        temp_data.append(round_off(cursor['sum_throughput']))
        temp_data.append(round_off(cursor['sum_iops']))
        if data_needed_for_query["name"] == 'Hsbench':
            temp_data.append(round_off(cursor['avg_lat']))
        elif data_needed_for_query["name"] == 'S3bench':
            temp_data.append(round_off(cursor['avg_lat_avg']*1000))
            if skipttfb:
                temp_data.append(round_off(cursor['avg_ttfb_avg']*1000))
                temp_data.append(round_off(cursor['avg_ttfb_99p']*1000))
        else:
            temp_data.append(round_off(cursor['avg_lat']))

        skipttfb = False

    temp_data.insert(0, added_objects)
    return temp_data, run_state


def get_dash_table_from_dataframe(dataframe, bench, column_id, states=None):
    """
    functional to get dash table to show stats from dataframe

    Args:
        dataframe: pandas dataframe containing data
        bench: bench for which the data is
        column_id: column id needed for the column to plot

    Returns:
        figure: dashtable figure with plotted plots
    """
    def style_conditiona_func(states):
        if states:
            style_set = []
            for i, state in enumerate(states):
                if state == 'failed':
                    style_set.append(
                        {'if': {'row_index': i}, 'backgroundColor': '#FADBD8'
                         })
                elif i % 2 != 0:
                    style_set.append(
                        {'if': {'row_index': i}, 'backgroundColor': '#E5E4E2'})
            style_set.append({'if': {'column_id': column_id},
                             'backgroundColor': '#D8D8D8'})

        else:
            style_set = [
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#E5E4E2'},
                {'if': {'column_id': column_id}, 'backgroundColor': '#D8D8D8'}
            ]
        return style_set

    if len(dataframe) < 1:
        benchmark = html.P("Data is not Available.")
    else:
        if bench == 'metadata_s3bench':
            headings = [{'name': 'Operations', 'id': 'Statistics'},
                        {'name': 'Latency (ms)', 'id': '1KB'}
                        ]
        elif bench == 'bucketops_hsbench':
            headings = [
                {'name': 'Operations', 'id': 'Operations'},
                {'name': 'Average Latency', 'id': 'AvgLat'},
                {'name': 'Minimum Latency', 'id': 'MinLat'},
                {'name': 'Maximum Latency', 'id': 'MaxLat'},
                {'name': 'IOPS', 'id': 'Iops'},
                {'name': 'Throughput', 'id': 'Mbps'},
                {'name': 'Operations', 'id': 'Ops'},
                {'name': 'Execution Time', 'id': 'Seconds'},
            ]
        else:
            headings = [
                {'name': column, 'id': column} for column in list(dataframe.columns)
            ]

        benchmark = dash_table.DataTable(
            id=f"{bench}_table",
            columns=headings,
            data=dataframe.to_dict('records'),
            merge_duplicate_headers=True,
            sort_action="native",
            style_header=style_dashtable_header,
            style_data_conditional=style_conditiona_func(states),
            style_cell=style_table_cell
        )

    return benchmark


def get_workload_headings(data):
    """
    function to get workload headings

    Args:
        data: data dict with dropdown values

    Returns:
        H5: heading with workload string
    """
    return html.H5(f"Data for {data['build']} build with {data['OS']} OS\
        on branch {data['branch']} with {data['nodes']} nodes, \
        {data['pfull']}% utilization having workload of {data['buckets']} \
        bucket(s) and {data['sessions']} session(s).")


def get_metadata_latencies(data_needed_for_query):
    """
    function to get metadata latencies for stats

    Args:
        data: datadict with data needed for the query

    Returns:
        dataframe: padas dataframe with fetched data
    """
    objects = ['1KB']

    results = {
        'Statistics': ['Add / Edit Object Tags', 'Read Object Tags',
                       'Read Object Metadata']
    }

    run_state_list = []
    for obj in objects:
        temp_data = []
        operations = ["PutObjTag", "GetObjTag", "HeadObj"]

        uri, db_name, db_collection = get_db_details(
            data_needed_for_query['release'])

        for operation in operations:
            run_state = "successful"
            data_needed_for_query['operation'] = operation
            data_needed_for_query['objsize'] = obj
            query = get_complete_schema(data_needed_for_query)
            count = count_documents(query=query, uri=uri, db_name=db_name,
                                    collection=db_collection)
            db_data = find_documents(query=query, uri=uri, db_name=db_name,
                                     collection=db_collection)

            try:
                if "Run_State" in db_data[0].keys():
                    run_state = db_data[0]['Run_State']
            except IndexError:
                run_state = "successful"

            temp_data.append(get_average_data(
                count, db_data, "Latency", "Avg", 1000))

            run_state_list.append(run_state)

        if not check_empty_list(temp_data):
            results[obj] = temp_data

    if len(results) > 1:
        data_frame = pd.DataFrame(results)
    else:
        data_frame = pd.DataFrame()

    return data_frame, run_state_list


def get_bucktops(data_needed_for_query):
    """
    function to get bucketops table for stats

    Args:
        data: datadict with data needed for the query

    Returns:
        dataframe: padas dataframe with fetched data
    """
    ops_modes = get_bucketops_modes()
    mode_indices = list(ops_modes.keys())

    bucket_ops = ['AvgLat', 'MinLat', 'MaxLat',
                  'Iops', 'Mbps', 'Ops', 'Seconds']
    data = {
        'Operations': bucketops_headings
    }
    uri, db_name, db_collection = get_db_details(
        data_needed_for_query['release'])

    data_needed_for_query['operation'] = 'Write'
    query = get_complete_schema(data_needed_for_query)
    count = count_documents(query=query, uri=uri, db_name=db_name,
                            collection=db_collection)
    db_data = find_documents(query=query, uri=uri, db_name=db_name,
                             collection=db_collection)
    run_state_list = ["successful"] * len(bucket_ops)

    try:
        results = db_data[0]["Bucket_Ops"]

        try:
            if "Run_State" in db_data[0].keys():
                run_state_list = [db_data[0]['Run_State']] * len(bucket_ops)
        except IndexError:
            run_state_list = ["successful"] * len(bucket_ops)

        for bucket_operation in bucket_ops:
            temp_data = []
            for mode in mode_indices:
                if count > 0 and keys_exists(results[int(mode)], bucket_operation):
                    temp_data.append(
                        round_off(results[int(mode)][bucket_operation]))
                else:
                    temp_data.append("NA")

            if not check_empty_list(temp_data):
                data[bucket_operation] = temp_data
    except IndexError:
        return pd.DataFrame(), run_state_list
    except KeyError:
        return pd.DataFrame(), run_state_list

    if len(data) > 1:
        data_frame = pd.DataFrame(data)
    else:
        data_frame = pd.DataFrame()

    return data_frame, run_state_list


def plot_graphs_with_given_data(fig, fig_all, x_data, y_data, plot_data):
    """
    function to plot graphs

    Args:
        fig: plotly figure to add trace on it
        fig_all: plotly figure to also add same trace on it
        x_data: data to be plotted on x axis
        y_data: data to be plotted on y axis
        plot_data: data dict storing info related to graph
        color: color to be given to the plot
    """
    trace = go.Scatter(
        name='{} - {}'.format(
            plot_data['operation'], plot_data['name']),
        x=x_data,
        y=y_data,
        hovertemplate='<br>%{x}, %{y}<br>' + '<b>{} - {} {}</b><extra></extra>'.format(
            plot_data['operation'], plot_data['option'], plot_data['custom']),
        connectgaps=True,
        # line={'color': plot_data['pallete'][plot_data['operation']]}
    )

    fig.add_trace(trace)
    trace.update(
        name=f"{plot_data['operation']} {plot_data['metric']} - {plot_data['name']}")
    fig_all.add_trace(trace)


def get_graph_layout(plot_data):
    """
    function to create a graph with predefined format

    Args:
        plot_data: data dict storing info related to graph

    Returns:
        figure: plotly figure with layout configured
    """
    if plot_data['metric'] != 'all':
        title_string = '<b>{} Plot</b>'.format(plot_data['metric'])
    else:
        title_string = '<b>All Plots in One</b>'

    fig = go.Figure()
    fig.update_layout(
        autosize=True,
        height=625,
        showlegend=True,
        title=title_string,
        title_font_size=25,
        title_font_color='#343a40',
        font_size=17,
        legend_font_size=13,
        legend_title='Legend',
        xaxis=dict(
            title_text=plot_data['x_heading'],
            titlefont=dict(size=23),

        ),
        yaxis=dict(
            title_text=plot_data['y_heading'],
            titlefont=dict(size=23)),
    )

    return fig
