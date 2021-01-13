from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, PageBreak, Paragraph

import common

COMPONENT_LEVEL_SUMMARY_ENTRIES = 15
SINGLE_BUCKET_PERF_STATS_ENTRIES = 10
MULTI_BUCKET_PERF_STATS_ENTRIES = 38
METADATA_LATENCIES_TABLE_ENTRIES = 5
TIMING_SUMMARY_TABLE_ENTRIES = 17

MAIN_TABLE_START = 0
MAIN_TABLE_END = MAIN_TABLE_START + common.MAIN_TABLE_ENTRIES
REPORTED_BUGS_TABLE_START = MAIN_TABLE_END + 1
REPORTED_BUGS_TABLE_END = REPORTED_BUGS_TABLE_START + common.REPORTED_BUGS_TABLE_ENTRIES
QA_REPORT_TABLE_START = REPORTED_BUGS_TABLE_END + 1
QA_REPORT_TABLE_END = QA_REPORT_TABLE_START + common.QA_REPORT_TABLE_ENTRIES
COMPONENT_LEVEL_SUMMARY_START = QA_REPORT_TABLE_END + 1
COMPONENT_LEVEL_SUMMARY_END = COMPONENT_LEVEL_SUMMARY_START + COMPONENT_LEVEL_SUMMARY_ENTRIES
SINGLE_BUCKET_PERF_STATS_START = COMPONENT_LEVEL_SUMMARY_END + 1
SINGLE_BUCKET_PERF_STATS_END = SINGLE_BUCKET_PERF_STATS_START + SINGLE_BUCKET_PERF_STATS_ENTRIES
MULTI_BUCKET_PERF_STATS_START = SINGLE_BUCKET_PERF_STATS_END + 1
MULTI_BUCKET_PERF_STATS_END = MULTI_BUCKET_PERF_STATS_START + MULTI_BUCKET_PERF_STATS_ENTRIES
METADATA_LATENCIES_TABLE_START = MULTI_BUCKET_PERF_STATS_END + 1
METADATA_LATENCIES_TABLE_END = METADATA_LATENCIES_TABLE_START + METADATA_LATENCIES_TABLE_ENTRIES
TIMING_SUMMARY_TABLE_START = METADATA_LATENCIES_TABLE_END + 1
TIMING_SUMMARY_TABLE_END = TIMING_SUMMARY_TABLE_START + TIMING_SUMMARY_TABLE_ENTRIES
DEFECT_TABLE_START = TIMING_SUMMARY_TABLE_END + 1


def build_component_table(data):
    component_table = Table(data, 10 * [0.71 * inch], 15 * [0.25 * inch],
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
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor(0x0070c0)),  # Blue for last row
    ]))
    component_table._argW[0] = 1.25 * inch
    return component_table


def build_single_bucket_perf_stats(data):
    single_bucket_perf_stats = Table(data, 9 * [0.71 * inch], 10 * [0.24 * inch],
                                     style=common.common_table_style)
    single_bucket_perf_stats._argW[0] = 2 * inch
    return single_bucket_perf_stats


def build_multi_bucket_perf_stats(data):
    multi_bucket_perf_stats = Table(data, 10 * [0.71 * inch], 38 * [0.24 * inch],
                                    style=common.common_table_style)
    multi_bucket_perf_stats.setStyle(TableStyle([
        ('LINEABOVE', (0, 3), (0, 7), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 9), (0, 13), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 15), (0, 19), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 21), (0, 25), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 27), (0, 31), 1, colors.HexColor(0xededed)),
        ('LINEABOVE', (0, 33), (0, 37), 1, colors.HexColor(0xededed)),
    ]))
    multi_bucket_perf_stats._argW[0] = 1 * inch
    multi_bucket_perf_stats._argW[1] = 1.25 * inch
    return multi_bucket_perf_stats


def build_metadata_latencies_table(data):
    single_bucket_perf_stats = Table(data, 2 * [3.8 * inch], 5 * [0.25 * inch],
                                     style=common.common_table_style)
    return single_bucket_perf_stats


def build_defect_table(data):
    stylesheet = getSampleStyleSheet()

    # Set wrap text style for 5th column (Bug Description) in table.
    for row in data[2:]:   # Do not apply for first two header rows
        if len(row) >= 5:
            row[5] = Paragraph(row[5], stylesheet['BodyText'])

    defect_table = Table(data, 6 * [0.72 * inch], None,
                         style=common.common_table_style)
    defect_table.setStyle(TableStyle([
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),  # Font for complete table
        ('FONTSIZE', (0, 2), (-1, -1), 9),  # Font size for table heading
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    defect_table._argW[5] = 3.5 * inch
    defect_table._argW[0] = 1.25 * inch
    defect_table._argH[1] = 0.25 * inch
    defect_table._argH[0] = 0.25 * inch
    return defect_table


def main():
    doc = SimpleDocTemplate("Engg_Report.pdf", pagesize=letter, leftMargin=0.5 * inch,
                            rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)

    data = common.get_data_from_csv('engg_report.csv')

    main_table_data = [data[i] for i in range(MAIN_TABLE_START, MAIN_TABLE_END)]
    main_table = common.build_main_table(main_table_data)

    reported_bugs_table_data = [
        data[i] for i in range(REPORTED_BUGS_TABLE_START, REPORTED_BUGS_TABLE_END)]
    qa_report_table_data = [data[i] for i in range(QA_REPORT_TABLE_START, QA_REPORT_TABLE_END)]
    two_tables = common.build_two_tables(reported_bugs_table_data, qa_report_table_data)

    component_table_data = [
        data[i] for i in range(COMPONENT_LEVEL_SUMMARY_START, COMPONENT_LEVEL_SUMMARY_END)]
    component_table = build_component_table(component_table_data)

    single_bucket_perf_stats_data = [
        data[i] for i in range(SINGLE_BUCKET_PERF_STATS_START, SINGLE_BUCKET_PERF_STATS_END)]
    single_bucket_perf_stats = build_single_bucket_perf_stats(single_bucket_perf_stats_data)

    multi_bucket_perf_stats_data = [
        data[i] for i in range(MULTI_BUCKET_PERF_STATS_START, MULTI_BUCKET_PERF_STATS_END)]
    multi_bucket_perf_stats = build_multi_bucket_perf_stats(multi_bucket_perf_stats_data)

    metadata_latencies_data = [
        data[i] for i in range(METADATA_LATENCIES_TABLE_START, METADATA_LATENCIES_TABLE_END)]
    metadata_latencies_table = build_metadata_latencies_table(metadata_latencies_data)

    timing_summary_table_data = [
        data[i] for i in range(TIMING_SUMMARY_TABLE_START, TIMING_SUMMARY_TABLE_END)]
    timing_summary_table = common.build_timing_summary_table(timing_summary_table_data)

    defect_table_data = [data[i] for i in range(DEFECT_TABLE_START, len(data))]
    defect_table = build_defect_table(defect_table_data)

    elements = [main_table, Spacer(15, 15), two_tables, Spacer(15, 15),
                component_table, Spacer(15, 15), single_bucket_perf_stats, Spacer(15, 15),
                multi_bucket_perf_stats, PageBreak(), metadata_latencies_table, Spacer(15, 15),
                timing_summary_table, Paragraph("<em>NA signifies the data is Not Available.</em>"),
                Spacer(15, 15), defect_table]
    doc.build(elements)


if __name__ == '__main__':
    main()
