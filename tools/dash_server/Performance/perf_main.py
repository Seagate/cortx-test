import dash_html_components as html
from Performance.statistics.statistics_layouts import statistics_perf_tabs, stats_input_options

perf_stats_page = html.Div(
    [
        html.Div(stats_input_options),
        html.Div(statistics_perf_tabs)
    ]
)

from Performance.graphs.graphs_layouts import graphs_input_options, graphs_perf_tabs

perf_graphs_page = html.Div(
    [
        html.Div(graphs_input_options),
        html.Div(graphs_perf_tabs)
    ]
)