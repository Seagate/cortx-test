# -------------------------------------------------------------------------------
# Name:        run_locust
# Purpose:     Run locust tool with given number of users for given
#              amount of time and collect logs.
# Author:      Sunil Khamkar
#
# Created:     12/03/2019
# -------------------------------------------------------------------------------

import os
import argparse
import subprocess
import configparser

locust_cfg = configparser.ConfigParser()
locust_cfg.read('scripts/Locust/locust_config.ini')
stdout = int(locust_cfg['default']['stdout'])


def run_cmd(cmd):
    """
    Execute Shell command
    :param str cmd: cmd to be executed
    :return: output of command from console
    :rtype: str
    """
    os.write(stdout, str.encode(cmd))
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    result = str(proc.communicate())
    return result


if __name__ == '__main__':
    # Default values for optional arguments if not provided.
    host_url = locust_cfg['default']['host_url']
    user_count = int(locust_cfg['default']['user_count'])
    hatch_rate = int(locust_cfg['default']['hatch_rate'])
    duration = locust_cfg['default']['duration']  # e.g. (300s, 20m, 3h, 1h30m, etc.)
    log_file = locust_cfg['default']['log_file']

    parser = argparse.ArgumentParser(description='Run locust tool.')
    parser.add_argument('file_path', help='locust.py file path')
    parser.add_argument('--h', dest='host_url', help='host URL', nargs='?', const=host_url,
                        type=str, default=host_url)
    parser.add_argument('--u', dest='user_count', help='number of Locust users to spawn', nargs='?',
                        const=user_count, type=int, default=user_count)
    parser.add_argument('--r', dest='hatch_rate', help='specifies the hatch rate (number of users to spawn per second)',
                        nargs='?', const=hatch_rate, type=int, default=hatch_rate)
    parser.add_argument('--t', dest='duration', help='specify the run time for a test, eg:1h30m', nargs='?',
                        const=duration, type=str, default=duration)
    parser.add_argument('--l', dest='log_file', help='specify the path to store logs', nargs='?',
                        const=log_file, type=str, default=log_file)

    args = parser.parse_args()

    os.write(stdout, str.encode("Setting ulimit for locust\n"))
    ulimit_command = locust_cfg['default']['ulimit_cmd']
    locust_command = locust_cfg['default']['locust_cmd'].format(args.host_url, args.file_path, args.user_count, args.hatch_rate, args.duration, args.log_file)
    cmd = "{}; {}\n".format(ulimit_command, locust_command)
    run_cmd(cmd)
