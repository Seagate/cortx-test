"""Script used to generate engineering pdf report."""
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
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak, Paragraph

import common_pdf


def build_component_table(data: List[list]):
    """Build component table."""
    col_width = 5 * [1.3 * inch]
    col_width[0] = 2.4 * inch
    component_table = Table(data, col_width, len(data) * [0.25 * inch],
                            style=common_pdf.common_table_style)
    return component_table


def build_single_bucket_perf_stats(data: List[list]):
    """Build single bucket performance table."""
    col_width = 9 * [0.57 * inch]
    col_width[0] = 2 * inch
    single_bucket_perf_stats = Table(data, col_width, 10 * [0.24 * inch],
                                     style=common_pdf.common_table_style)
    return single_bucket_perf_stats


def build_multi_bucket_perf_stats(data: List[list]):
    """Build multi bucket performance table."""
    col_width = 10 * [0.57 * inch]
    col_width[0] = 1 * inch
    col_width[1] = 1.25 * inch

    multi_bucket_perf_stats = Table(data, col_width, 38 * [0.24 * inch],
                                    style=common_pdf.common_table_style)
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
                                     style=common_pdf.common_table_style)
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
                         style=common_pdf.common_table_style)
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
    build = common_pdf.get_args()
    all_data = common_pdf.get_data_from_csv(f'Engg_Report_{build}.csv')

    main_table_data, table2_start = common_pdf.get_table_data(all_data, 0)
    reported_bugs_table_data, table3_start = common_pdf.get_table_data(all_data, table2_start)
    qa_report_table_data, table4_start = common_pdf.get_table_data(all_data, table3_start)
    component_table_data, table5_start = common_pdf.get_table_data(all_data, table4_start)
    single_bucket_perf_stats_data, table6_start = common_pdf.get_table_data(all_data, table5_start)
    multi_bucket_perf_stats_data, table7_start = common_pdf.get_table_data(all_data, table6_start)
    metadata_latencies_data, table8_start = common_pdf.get_table_data(all_data, table7_start)
    timing_summary_table_data, table9_start = common_pdf.get_table_data(all_data, table8_start)
    defect_table_data, _ = common_pdf.get_table_data(all_data, table9_start)

    main_table = common_pdf.build_main_table(main_table_data)

    two_tables = common_pdf.build_two_tables(reported_bugs_table_data, qa_report_table_data)

    component_table = build_component_table(component_table_data)

    single_bucket_perf_stats = build_single_bucket_perf_stats(single_bucket_perf_stats_data)

    multi_bucket_perf_stats = build_multi_bucket_perf_stats(multi_bucket_perf_stats_data)

    metadata_latencies_table = build_metadata_latencies_table(metadata_latencies_data)

    timing_summary_table = common_pdf.build_timing_summary_table(timing_summary_table_data)

    defect_table = build_defect_table(defect_table_data)

    elements = [main_table, Spacer(15, 15), two_tables, Spacer(15, 15),
                component_table, Spacer(15, 15), single_bucket_perf_stats, PageBreak(),
                multi_bucket_perf_stats, PageBreak(), metadata_latencies_table,
                Spacer(15, 15), timing_summary_table,
                Paragraph("<em>NA signifies the data is Not Available.</em>"),
                Spacer(15, 15), defect_table]

    doc = SimpleDocTemplate(f"Engg_Report_{build}.pdf", pagesize=letter, leftMargin=0.5 * inch,
                            rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    doc.build(elements)


if __name__ == '__main__':
    main()
