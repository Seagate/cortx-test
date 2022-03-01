"""Script used to generate executive pdf report."""
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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

import common_pdf


def build_feature_breakdown_table(data: List[list]):
    """Build feature breakdown table."""
    stylesheet = getSampleStyleSheet()

    # Set wrap text style for 5th column (Bug Description) in table.
    for row in data[2:]:  # Do not apply for first two header rows
        row[0] = Paragraph(f'''<b>{row[0]}</b>''', stylesheet['BodyText'])

    col_width = 6 * [0.86 * inch]
    col_width[0] = 3.25 * inch

    component_table = Table(data, col_width, None,
                            style=common_pdf.common_table_style)
    component_table.setStyle(TableStyle([
        ('TEXTCOLOR', (1, 2), (1, -1), colors.HexColor(0x00b050)),  # Green for 2nd (Total) column
        ('TEXTCOLOR', (2, 2), (2, -1), colors.HexColor(0xff0000)),  # Red for 3nd (Pass) column
        ('TEXTCOLOR', (3, 2), (3, -1), colors.HexColor(0x0070c0)),  # Blue for 4nd (Failed) column
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return component_table


def build_code_maturity_table(data: List[list]):
    """Build code maturity table."""
    code_maturity_table = Table(data, 4 * [1.89 * inch], len(data) * [0.225 * inch],
                                style=common_pdf.common_table_style)
    return code_maturity_table


def build_bucket_perf_stats_table(data: List[list]):
    """Build bucket performance statistics table."""
    bucket_perf_stats = Table(data, 3 * [2.52 * inch], len(data) * [0.25 * inch],
                              style=common_pdf.common_table_style)
    return bucket_perf_stats


def main():
    """Generate PDF executive report from csv executive report."""
    build = common_pdf.get_args()
    all_data = common_pdf.get_data_from_csv(f'Exec_Report_{build}.csv')

    main_table_data, table2_start = common_pdf.get_table_data(all_data, 0)
    reported_bugs_table_data, table3_start = common_pdf.get_table_data(all_data, table2_start)
    qa_report_table_data, table4_start = common_pdf.get_table_data(all_data, table3_start)
    feature_breakdown_table_data, table5_start = common_pdf.get_table_data(all_data, table4_start)
    code_maturity_table_data, table6_start = common_pdf.get_table_data(all_data, table5_start)
    bucket_perf_stats_table_data, table7_start = common_pdf.get_table_data(all_data, table6_start)
    timing_summary_table_data, _ = common_pdf.get_table_data(all_data, table7_start)

    main_table = common_pdf.build_main_table(main_table_data)

    two_tables = common_pdf.build_two_tables(reported_bugs_table_data, qa_report_table_data)

    feature_breakdown_table = build_feature_breakdown_table(feature_breakdown_table_data)

    code_maturity_table = build_code_maturity_table(code_maturity_table_data)

    bucket_perf_stats = build_bucket_perf_stats_table(bucket_perf_stats_table_data)

    timing_summary_table = common_pdf.build_timing_summary_table(timing_summary_table_data)

    elements = [main_table, Spacer(15, 15), two_tables, Spacer(15, 15),
                feature_breakdown_table, PageBreak(), code_maturity_table, Spacer(15, 15),
                bucket_perf_stats, Spacer(15, 15), timing_summary_table,
                Paragraph("<em>NA signifies the data is Not Available.</em>")]

    doc = SimpleDocTemplate(f"Exec_Report_{build}.pdf", pagesize=letter, leftMargin=0.5 * inch,
                            rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    doc.build(elements)


if __name__ == '__main__':
    main()
