from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, PageBreak

import common

FEATURE_BREAKDOWN_TABLE_ENTRIES = 11
CODE_MATURITY_TABLE_ENTRIES = 7
BUCKET_PERF_STATS_TABLE_ENTRIES = 6
TIMING_SUMMARY_TABLE_ENTRIES = 17

MAIN_TABLE_START = 0
MAIN_TABLE_END = MAIN_TABLE_START + common.MAIN_TABLE_ENTRIES
REPORTED_BUGS_TABLE_START = MAIN_TABLE_END + 1
REPORTED_BUGS_TABLE_END = REPORTED_BUGS_TABLE_START + common.REPORTED_BUGS_TABLE_ENTRIES
QA_REPORT_TABLE_START = REPORTED_BUGS_TABLE_END + 1
QA_REPORT_TABLE_END = QA_REPORT_TABLE_START + common.QA_REPORT_TABLE_ENTRIES
FEATURE_BREAKDOWN_TABLE_START = QA_REPORT_TABLE_END + 1
FEATURE_BREAKDOWN_TABLE_END = FEATURE_BREAKDOWN_TABLE_START + FEATURE_BREAKDOWN_TABLE_ENTRIES
CODE_MATURITY_TABLE_START = FEATURE_BREAKDOWN_TABLE_END + 1
CODE_MATURITY_TABLE_END = CODE_MATURITY_TABLE_START + CODE_MATURITY_TABLE_ENTRIES
BUCKET_PERF_STATS_TABLE_START = CODE_MATURITY_TABLE_END + 1
BUCKET_PERF_STATS_TABLE_END = BUCKET_PERF_STATS_TABLE_START + BUCKET_PERF_STATS_TABLE_ENTRIES
TIMING_SUMMARY_TABLE_START = BUCKET_PERF_STATS_TABLE_END + 1
TIMING_SUMMARY_TABLE_END = TIMING_SUMMARY_TABLE_START + TIMING_SUMMARY_TABLE_ENTRIES


def build_feature_breakdown_table(data):
    component_table = Table(data, 6 * [1.26 * inch], 11 * [0.225 * inch],
                            style=common.common_table_style)
    component_table.setStyle(TableStyle([
        ('TEXTCOLOR', (1, 2), (1, -1), colors.HexColor(0x0070c0)),  # Blue for 2nd (Total) column
        ('TEXTCOLOR', (2, 2), (2, -1), colors.HexColor(0x00b050)),  # Green for 3nd (Pass) column
        ('TEXTCOLOR', (3, 2), (3, -1), colors.HexColor(0xff0000)),  # Red for 4nd (Failed) column
    ]))
    return component_table


def build_code_maturity_table(data):
    code_maturity_table = Table(data, 4 * [1.89 * inch], 7 * [0.225 * inch],
                                style=common.common_table_style)
    return code_maturity_table


def build_bucket_perf_stats_table(data):
    bucket_perf_stats = Table(data, 3 * [2.52 * inch], 6 * [0.25 * inch],
                              style=common.common_table_style)
    return bucket_perf_stats


def main():
    doc = SimpleDocTemplate("Exec_Report.pdf", pagesize=letter, leftMargin=0.5 * inch,
                            rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)

    data = common.get_data_from_csv('exec_report.csv')

    main_table_data = [data[i] for i in range(MAIN_TABLE_START, MAIN_TABLE_END)]
    main_table = common.build_main_table(main_table_data)

    reported_bugs_table_data = [
        data[i] for i in range(REPORTED_BUGS_TABLE_START, REPORTED_BUGS_TABLE_END)]
    qa_report_table_data = [data[i] for i in range(QA_REPORT_TABLE_START, QA_REPORT_TABLE_END)]
    two_tables = common.build_two_tables(reported_bugs_table_data, qa_report_table_data)

    feature_breakdown_table_data = [
        data[i] for i in range(FEATURE_BREAKDOWN_TABLE_START, FEATURE_BREAKDOWN_TABLE_END)]
    feature_breakdown_table = build_feature_breakdown_table(feature_breakdown_table_data)

    code_maturity_table_data = [
        data[i] for i in range(CODE_MATURITY_TABLE_START, CODE_MATURITY_TABLE_END)]
    code_maturity_table = build_code_maturity_table(code_maturity_table_data)

    bucket_perf_stats_table_data = [
        data[i] for i in range(BUCKET_PERF_STATS_TABLE_START, BUCKET_PERF_STATS_TABLE_END)]
    bucket_perf_stats = build_bucket_perf_stats_table(bucket_perf_stats_table_data)

    timing_summary_table_data = [
        data[i] for i in range(TIMING_SUMMARY_TABLE_START, TIMING_SUMMARY_TABLE_END)]
    timing_summary_table = common.build_timing_summary_table(timing_summary_table_data)

    elements = [main_table, Spacer(15, 15), two_tables, Spacer(15, 15),
                feature_breakdown_table, Spacer(15, 15), code_maturity_table, Spacer(15, 15),
                bucket_perf_stats, PageBreak(), timing_summary_table,
                Paragraph("<em>NA signifies the data is Not Available.</em>")]
    doc.build(elements)


if __name__ == '__main__':
    main()
