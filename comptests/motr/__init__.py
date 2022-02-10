import os
import csv

def read_m0crate_tests_csv():
    m0crate_test_csv = os.path.join(os.getcwd(), "config/motr/m0crate_tests.csv")
    with open(m0crate_test_csv) as CSV_FH:
        CSV_DATA = [row for row in csv.DictReader(CSV_FH)]
    return CSV_DATA

CSV_DATA = read_m0crate_tests_csv()
