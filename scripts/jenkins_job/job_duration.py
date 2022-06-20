import argparse
import csv
import os
from commons.utils import web_utils

stages = ['SANITY_TEST_EXECUTION', 'REGRESSION_TEST_EXECUTION', 'IO_PATH_TEST_EXECUTION', 'FAILURE_DOMAIN_TEST_EXECUTION']
STAGE_DURATION_CSV = 'stages_duration.csv'


def convert_duration(duration_millis):
    minutes, ss = divmod(duration_millis / 1000, 60)
    hh, mm = divmod(minutes, 60)
    duration = f'{hh:0>2.0f}:{mm:0>2.0f}:{ss:0>2.0f}'
    return duration


def main():
    """ main function """
    parser = argparse.ArgumentParser(description="Stage Duration")
    parser.add_argument("-bl", help="build url", required=True)
    args = parser.parse_args()
    build_url = args.bl
    resp = web_utils.http_get_request(f"{build_url}wfapi/describe")
    stage = []
    stage.extend(resp.json()["stages"])
    print("********")
    print("stages are: ", stage)
    with open(os.path.join(os.getcwd(), STAGE_DURATION_CSV), 'w', newline='', encoding="utf8") as stage_csv:
        writer = csv.writer(stage_csv)
        total_duration = 0
        for i in stage:
            k = i['name']
            if k in stages:
                v = i['durationMillis']
                total_duration += v
                # minutes, s = divmod(v / 1000, 60)
                # hr, m = divmod(minutes, 60)
                # duration = f'{hr:0>2.0f}:{m:0>2.0f}:{s:0>2.0f}'
                duration = convert_duration(v)
                writer.writerow([k, duration])
        total_duration = convert_duration(total_duration)
        writer.writerow(['Total', total_duration])


if __name__ == "__main__":
    main()
