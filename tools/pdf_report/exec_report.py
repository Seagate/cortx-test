"""Script used to generate executive pdf report"""
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
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, PageBreak

import common


def build_feature_breakdown_table(data):
    """
    Build feature breakdown table
    Args:
        data (list): Table data

    Returns: table
    """
    component_table = Table(data, 6 * [1.26 * inch], 11 * [0.225 * inch],
                            style=common.common_table_style)
    component_table.setStyle(TableStyle([
        ('TEXTCOLOR', (1, 2), (1, -1), colors.HexColor(0x0070c0)),  # Blue for 2nd (Total) column
        ('TEXTCOLOR', (2, 2), (2, -1), colors.HexColor(0x00b050)),  # Green for 3nd (Pass) column
        ('TEXTCOLOR', (3, 2), (3, -1), colors.HexColor(0xff0000)),  # Red for 4nd (Failed) column
    ]))
    return component_table


def build_code_maturity_table(data):
    """
    Build code maturity table
    Args:
        data (list): Table data

    Returns: table
    """
    code_maturity_table = Table(data, 4 * [1.89 * inch], 7 * [0.225 * inch],
                                style=common.common_table_style)
    return code_maturity_table


def build_bucket_perf_stats_table(data):
    """
    Build bucket performance statistics table
    Args:
        data (list): Table data

    Returns: table
    """
    bucket_perf_stats = Table(data, 3 * [2.52 * inch], 6 * [0.25 * inch],
                              style=common.common_table_style)
    return bucket_perf_stats


def main():
    """
    Generate PDF executive report from csv executive report
    """
    all_data = common.get_data_from_csv('../exec_report.csv')

    main_table_data, table2_start = common.get_table_data(all_data, 0)
    reported_bugs_table_data, table3_start = common.get_table_data(all_data, table2_start)
    qa_report_table_data, table4_start = common.get_table_data(all_data, table3_start)
    feature_breakdown_table_data, table5_start = common.get_table_data(all_data, table4_start)
    code_maturity_table_data, table6_start = common.get_table_data(all_data, table5_start)
    bucket_perf_stats_table_data, table7_start = common.get_table_data(all_data, table6_start)
    timing_summary_table_data, _ = common.get_table_data(all_data, table7_start)

    build = main_table_data[2][1]

    main_table = common.build_main_table(main_table_data)

    two_tables = common.build_two_tables(reported_bugs_table_data, qa_report_table_data)

    feature_breakdown_table = build_feature_breakdown_table(feature_breakdown_table_data)

    code_maturity_table = build_code_maturity_table(code_maturity_table_data)

    bucket_perf_stats = build_bucket_perf_stats_table(bucket_perf_stats_table_data)

    timing_summary_table = common.build_timing_summary_table(timing_summary_table_data)

    elements = [main_table, Spacer(15, 15), two_tables, Spacer(15, 15),
                feature_breakdown_table, Spacer(15, 15), code_maturity_table, Spacer(15, 15),
                bucket_perf_stats, PageBreak(), timing_summary_table,
                Paragraph("<em>NA signifies the data is Not Available.</em>")]

    doc = SimpleDocTemplate(f"../Exec_Report_{build}.pdf", pagesize=letter, leftMargin=0.5 * inch,
                            rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    doc.build(elements)


if __name__ == '__main__':
    main()
