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
import csv

from reportlab.lib import colors
from reportlab.lib.pagesizes import inch
from reportlab.platypus import Table, TableStyle

MAIN_TABLE_ENTRIES = 5
REPORTED_BUGS_TABLE_ENTRIES = 8
QA_REPORT_TABLE_ENTRIES = 8

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


def build_main_table(data):
    table = Table(data, 2 * [3.8 * inch], len(data) * [0.23 * inch])
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
    table._argH[0] = 0.32 * inch
    return table


def build_reported_bugs_table(data):
    reported_bugs_table = Table(data, 3 * [1.25 * inch], len(data) * [0.225 * inch],
                                style=common_table_style)

    reported_bugs_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor(0x0070c0)),  # Blue for 2nd row
        ('TEXTCOLOR', (0, 3), (-1, 3), colors.HexColor(0xff0000)),  # Red for 3nd row
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor(0xed7d31)),  # Orange for 4nd row
        ('TEXTCOLOR', (0, 5), (-1, 5), colors.HexColor(0x0070c0)),  # Blue for 5nd row
        ('TEXTCOLOR', (0, 7), (-1, 7), colors.HexColor(0x009933)),  # Green for 7nd row
    ]))
    reported_bugs_table._argH[0] = 0.3 * inch
    return reported_bugs_table


def build_qa_report_table(data):
    qa_report_table = Table(data, 3 * [1.25 * inch], len(data) * [0.225 * inch],
                            style=common_table_style)

    qa_report_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.HexColor(0x0070c0)),  # Blue for 2nd row
        ('TEXTCOLOR', (0, 3), (-1, 3), colors.HexColor(0x009933)),  # Green for 3nd row
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor(0xff0000)),  # Red for 4nd row
    ]))
    qa_report_table._argH[0] = 0.3 * inch
    return qa_report_table


def build_two_tables(reported_bugs_table_data, qa_report_table_data):
    bugs_table = build_reported_bugs_table(reported_bugs_table_data)
    qa_report_table = build_qa_report_table(qa_report_table_data)

    data_comb = [(bugs_table, qa_report_table)]
    t = Table(data_comb, 2 * [3.85 * inch], 1 * [1.8 * inch])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTRE'),
    ]))
    return t


def build_timing_summary_table(data):
    timing_summary_table = Table(data, 6 * [1.26 * inch], len(data) * [0.25 * inch],
                                 style=common_table_style)
    return timing_summary_table


def get_data_from_csv(csv_file):
    with open(csv_file, newline='') as f:
        reader = csv.reader(f)
        data = list(reader)
    for row in data:
        if len(row) > 1 and row[-1] == "":
            del row[-1]
    return data
