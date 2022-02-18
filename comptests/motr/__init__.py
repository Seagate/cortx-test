""" Generating test data after reading the m0crate tests CSV """
import os
import csv

def read_m0crate_tests_csv():
    """
    To read the m0crate test csv and return the list of dicts
    return: list of dicts containing the csv key-value pairs
    rtype: list
    """
    m0crate_test_csv = os.path.join(os.getcwd(), "config/motr/m0crate_tests.csv")
    with open(m0crate_test_csv) as csv_fh:
        csv_data = list(csv.DictReader(csv_fh))
    return csv_data

CSV_DATA = read_m0crate_tests_csv()
