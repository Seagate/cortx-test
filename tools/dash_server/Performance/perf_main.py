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

from Performance.graphs.graphs_layouts import graphs_input_options, graphs_perf_tabs
import dash_html_components as html
from Performance.statistics.statistics_layouts import statistics_perf_tabs, stats_input_options

perf_stats_page = html.Div(
    [
        html.Div(stats_input_options),
        html.Div(statistics_perf_tabs)
    ]
)


perf_graphs_page = html.Div(
    [
        html.Div(graphs_input_options),
        html.Div(graphs_perf_tabs)
    ]
)
