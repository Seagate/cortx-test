# -*- coding: utf-8 -*-
# !/usr/bin/python

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

"""Common functions used while generating engineering and executive pdf reports."""

import argparse
import csv
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import inch
from reportlab.platypus import Table, TableStyle

common_table_style = [
    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),  # Font for complete table
    ('FONTSIZE', (0, 0), (0, 0), 12),  # Font size for table heading
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center text in cell
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Center text in cell
    ('BOX', (0, 0), (-1, -1), 0.5, colors.black),  # Table outline
    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),  # Table inside grid
    ('LEFTPADDING', (0, 0), (-1, -1), 0),  # No padding
    ('TOPPADDING', (0, 0), (-1, -1), 0),  # No padding
    ('RIGHTPADDING', (0, 0), (-1, -1), 0),  # No padding
    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),  # No padding
    ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor(0x002060)),  # Blue for heading
    ('SPAN', (0, 0), (-1, 0)),  # Merge Cells in row 1
    ('BACKGROUND', (0, 2), (0, -1), colors.HexColor(0xededed)),  # Grey bg 1st column
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(0xededed)),  # Lite grey bg 1st row
    ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor(0xa5a5a5)),  # Dark grey bg for 2nd row
]


def build_main_table(data: List[list]):
    """Build Header table."""
    row_heights = len(data) * [0.23 * inch]
    row_heights[0] = 0.32 * inch
    table = Table(data, 2 * [3.8 * inch], row_heights)
    table.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),  # Merge Cells in row 1
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),  # Table outline
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),  # Table inside grid
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Center text in cell
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),  # Center text in cell
        ('BACKGROUND', (0, 1), (1, -1), colors.HexColor(0xededed)),  # Grey bg for all but 1st row
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),  # Font for complete table
        ('FONTSIZE', (0, 1), (-1, -1), 11),  # Font size for non header rows
        ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor(0x0070c0)),  # Blue for table header
        ('FONTSIZE', (0, 0), (0, 0), 14),  # Font size for table header
        # ('LEFTPADDING', (0, 0), (-1, -1), 0),  # No padding
        ('TOPPADDING', (0, 0), (-1, -1), 0),  # No padding
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),  # No padding
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),  # No padding
    ]))
    return table


def build_reported_bugs_table(data: List[list]):
    """Build reported bugs table."""
    row_heights = len(data) * [0.225 * inch]
    row_heights[0] = 0.3 * inch
    reported_bugs_table = Table(data, 3 * [1.25 * inch], row_heights,
                                style=common_table_style)

    reported_bugs_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor(0x0070c0)),  # Blue for 2nd row
        ('TEXTCOLOR', (0, 3), (-1, 3), colors.HexColor(0xff0000)),  # Red for 3nd row
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor(0xed7d31)),  # Orange for 4nd row
        ('TEXTCOLOR', (0, 5), (-1, 5), colors.HexColor(0x0070c0)),  # Blue for 5nd row
        ('TEXTCOLOR', (0, 7), (-1, 7), colors.HexColor(0x009933)),  # Green for 7nd row
    ]))

    return reported_bugs_table


def build_qa_report_table(data: List[list]):
    """Build qa report table."""
    row_heights = len(data) * [0.225 * inch]
    row_heights[0] = 0.3 * inch
    qa_report_table = Table(data, 3 * [1.25 * inch], row_heights,
                            style=common_table_style)

    qa_report_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor(0x0070c0)),  # Blue for 2nd row
        ('TEXTCOLOR', (0, 3), (-1, 3), colors.HexColor(0x009933)),  # Green for 3nd row
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor(0xff0000)),  # Red for 4nd row
    ]))
    return qa_report_table


def build_two_tables(reported_bugs_table_data: List[list], qa_report_table_data: List[list]):
    """Build Reported bugs & QA Report tables."""
    bugs_table = build_reported_bugs_table(reported_bugs_table_data)
    qa_report_table = build_qa_report_table(qa_report_table_data)

    data_comb = [(bugs_table, qa_report_table)]
    table = Table(data_comb, 2 * [3.85 * inch], 1 * [1.8 * inch])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
    ]))
    return table


def build_timing_summary_table(data: List[list]):
    """Build timings summary table."""
    timing_summary_table = Table(data, 6 * [1.26 * inch], len(data) * [0.25 * inch],
                                 style=common_table_style)
    return timing_summary_table


def get_data_from_csv(csv_file: str) -> List[List]:
    """Read report data from csv file."""
    with open(csv_file, newline='') as report_file:
        reader = csv.reader(report_file)
        data = list(reader)
    for row in data:
        if len(row) > 1 and row[-1] == "":
            del row[-1]
    return data


def get_table_data(data: List[list], start: int = 0):
    """Read report data from csv file."""
    table_data = []
    end = 0
    for idx, _ in enumerate(data, start=start):
        if not data[idx]:
            end = idx + 1
            break
        table_data.append(data[idx])
    return table_data, end


def get_args():
    """Parse arguments and collect database information"""
    parser = argparse.ArgumentParser()
    parser.add_argument('build', help='Build number')

    args = parser.parse_args()
    return args.build
