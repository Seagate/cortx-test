"""Performance tabs integrated UI central file"""
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
from Performance.graphs.graphs_layouts import graphs_perf_tabs, graphs_input_options
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
