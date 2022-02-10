import os
import csv

M0CRATE_TEST_CSV = os.path.join(os.getcwd(), "config/motr/m0crate_tests.csv")

def read_csv():
    with open(M0CRATE_TEST_CSV) as CSV_FH:
        CSV_DATA = [row for row in csv.DictReader(CSV_FH)]
    return CSV_DATA

CSV_DATA = read_csv()
