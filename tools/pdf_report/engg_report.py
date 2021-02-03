"""Script used to generate engineering pdf report."""
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
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak, Paragraph

import common


def build_component_table(data: List[list]):
    """Build component table."""
    col_width = 10 * [0.71 * inch]
    col_width[0] = 1.25 * inch
    component_table = Table(data, col_width, len(data) * [0.25 * inch],
                            style=common.common_table_style)
    component_table.setStyle(TableStyle([
        ('SPAN', (0, 1), (0, 2)),  # Merge Cells for Component
        ('SPAN', (1, 1), (1, 2)),  # Merge Cells for Total
        ('SPAN', (2, 1), (3, 1)),  # Merge Cells for Build
        ('SPAN', (4, 1), (5, 1)),  # Merge Cells for Build-1
        ('SPAN', (6, 1), (7, 1)),  # Merge Cells for Build-2
        ('SPAN', (8, 1), (9, 1)),  # Merge Cells for Build-3
        ('BACKGROUND', (2, 2), (3, -1), colors.HexColor(0xededed)),  # Grey bg 3rd & 4th column
        ('BACKGROUND', (0, 1), (1, 2), colors.HexColor(0xa5a5a5)),  # Dark Grey bg for 2nd row
        ('BACKGROUND', (0, 3), (0, -1), colors.HexColor(0xededed)),  # Grey bg 1st column
        ('BACKGROUND', (1, 3), (1, -1), colors.HexColor(0xd9e2f3)),  # Blue bg 2nd row

        ('TEXTCOLOR', (1, 3), (1, -1), colors.HexColor(0x0070c0)),  # Blue for 2nd column
        ('TEXTCOLOR', (2, 2), (2, -1), colors.HexColor(0x009933)),  # Green for 3rd column
        ('TEXTCOLOR', (3, 2), (3, -1), colors.HexColor(0xff0000)),  # Red for 4th column
        ('TEXTCOLOR', (4, 2), (4, -1), colors.HexColor(0x009933)),  # Green for 5th column
        ('TEXTCOLOR', (5, 2), (5, -1), colors.HexColor(0xff0000)),  # Red for 6th column
        ('TEXTCOLOR', (6, 2), (6, -1), colors.HexColor(0x009933)),  # Green for 7th column
        ('TEXTCOLOR', (7, 2), (7, -1), colors.HexColor(0xff0000)),  # Red for 8th column
        ('TEXTCOLOR', (8, 2), (8, -1), colors.HexColor(0x009933)),  # Green for 9th column
        ('TEXTCOLOR', (9, 2), (9, -1), colors.HexColor(0xff0000)),  # Red for 10th column
    ]))
    return component_table


def build_single_bucket_perf_stats(data: List[list]):
    """Build single bucket performance table."""
    col_width = 9 * [0.71 * inch]
    col_width[0] = 2 * inch
    single_bucket_perf_stats = Table(data, col_width, 10 * [0.24 * inch],
                                     style=common.common_table_style)
    return single_bucket_perf_stats


def build_multi_bucket_perf_stats(data: List[list]):
    """Build multi bucket performance table."""
    col_width = 10 * [0.71 * inch]
    col_width[0] = 1 * inch
    col_width[1] = 1.25 * inch

    multi_bucket_perf_stats = Table(data, col_width, 38 * [0.24 * inch],
                                    style=common.common_table_style)
    multi_bucket_perf_stats.setStyle(TableStyle([
        ('LINEABOVE', (0, 3), (0, 7), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 9), (0, 13), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 15), (0, 19), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 21), (0, 25), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 27), (0, 31), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 33), (0, 37), 1, colors.HexColor(0xededed)),
    ]))
    return multi_bucket_perf_stats


def build_metadata_latencies_table(data: List[list]):
    """Build metadata latencies table."""
    single_bucket_perf_stats = Table(data, 2 * [3.8 * inch], 5 * [0.25 * inch],
                                     style=common.common_table_style)
    return single_bucket_perf_stats


def build_defect_table(data: List[list]):
    """Build defect table."""
    stylesheet = getSampleStyleSheet()

    # Set wrap text style for 5th column (Bug Description) in table.
    for row in data[2:]:  # Do not apply for first two header rows
        if len(row) >= 5:
            row[5] = Paragraph(row[5], stylesheet['BodyText'])
            row[1] = Paragraph(row[1].replace("/", "<br/>"), stylesheet['BodyText'])

    col_width = 6 * [0.72 * inch]
    col_width[5] = 3.5 * inch
    col_width[0] = 1.25 * inch
    col_width[1] = 1 * inch

    defect_table = Table(data, col_width, None,
                         style=common.common_table_style)
    defect_table.setStyle(TableStyle([
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),  # Font for complete table
        ('FONTSIZE', (0, 2), (-1, -1), 9),  # Font size for table heading
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return defect_table


def main():
    """Generate PDF engineering report from csv executive report."""
    all_data = common.get_data_from_csv('../engg_report.csv')

    main_table_data, table2_start = common.get_table_data(all_data, 0)
    reported_bugs_table_data, table3_start = common.get_table_data(all_data, table2_start)
    qa_report_table_data, table4_start = common.get_table_data(all_data, table3_start)
    component_table_data, table5_start = common.get_table_data(all_data, table4_start)
    single_bucket_perf_stats_data, table6_start = common.get_table_data(all_data, table5_start)
    multi_bucket_perf_stats_data, table7_start = common.get_table_data(all_data, table6_start)
    metadata_latencies_data, table8_start = common.get_table_data(all_data, table7_start)
    timing_summary_table_data, table9_start = common.get_table_data(all_data, table8_start)
    defect_table_data, _ = common.get_table_data(all_data, table9_start)

    main_table = common.build_main_table(main_table_data)

    build = main_table_data[2][1]

    two_tables = common.build_two_tables(reported_bugs_table_data, qa_report_table_data)

    component_table = build_component_table(component_table_data)

    single_bucket_perf_stats = build_single_bucket_perf_stats(single_bucket_perf_stats_data)

    multi_bucket_perf_stats = build_multi_bucket_perf_stats(multi_bucket_perf_stats_data)

    metadata_latencies_table = build_metadata_latencies_table(metadata_latencies_data)

    timing_summary_table = common.build_timing_summary_table(timing_summary_table_data)

    defect_table = build_defect_table(defect_table_data)

    elements = [main_table, Spacer(15, 15), two_tables, Spacer(15, 15),
                component_table, Spacer(15, 15), single_bucket_perf_stats, Spacer(15, 15),
                multi_bucket_perf_stats, PageBreak(), metadata_latencies_table,
                Spacer(15, 15), timing_summary_table,
                Paragraph("<em>NA signifies the data is Not Available.</em>"),
                Spacer(15, 15), defect_table]

    doc = SimpleDocTemplate(f"../Engg_Report_{build}.pdf", pagesize=letter, leftMargin=0.5 * inch,
                            rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    doc.build(elements)


if __name__ == '__main__':
    main()
