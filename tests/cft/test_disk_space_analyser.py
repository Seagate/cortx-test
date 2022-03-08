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
import time
import signal
import os
import sys
import argparse
#import getpass
import logging
#import socket
import re
import base64
import paramiko
import yaml
import traceback
import smtplib
import datetime
from unittest import TestCase
from fabric import Connection
from fabric import Config
from fabric import ThreadingGroup, SerialGroup
from fabric import runners
from fabric.exceptions import GroupException

#TODO: Part of automation and script validation is covered in
# EOS-24721

"""Disk Space Analyser test script"""
def parse_args():
    """
    Argument parser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-ll", "--log_level", type=int, default=10,
                        help="log level value")
    parser.add_argument("-hs", "--hosts", type=str,
                        help="host list")
    parser.add_argument("-np", "--node_pass", type=str,
                        default='', help="node password")
    return parser.parse_args()

def read_yaml(fpath):
    """Read yaml file and return dictionary/list of the content"""
    cwd = os.getcwd()
    fpath = os.path.join(cwd, fpath)
    if os.path.isfile(fpath):
        with open(fpath) as fin:
            try:
                data = yaml.safe_load(fin)
            except yaml.YAMLError as exc:
                try:
                    data = yaml.safe_load(fin.read(), Loader=yaml.Loader)
                except yaml.YAMLError as exc:
                    err_msg = "Failed to parse: {}\n{}".format(fpath, str(exc))
                    raise YamlError(fpath, 'YAML file syntax error')

    else:
        #err_msg = "Specified file doesn't exist: {}".format(fpath)
        raise YamlError(fpath, 'YAML file missing')
    return data


BASE_DIR = "/var"
log = logging.getLogger("LogAnalyzer")
LOG_CFG = read_yaml("config/cft/test_logrotation.yaml")
USER = LOG_CFG["username"]
passwords = {}  # args.node_pass
vm_machines = {}  # args.hosts.split(',')
core_hosts = list()
# for host in vm_machines:
#     core_hosts.append('.'.join([host.strip(), suffix]))
# core_hosts = ["%s.%s" % (node, LOG_CFG["host_domain"]) 
#              if not re.match("^\d{1,3}(?:\.\d{1,3}){3}$", node) 
#              else node
#              for node in core_hosts]
# password = LOG_CFG["password"]
# password = base64.b64decode(bytes(password, 'utf-8'))
# config = Config(overrides={'sudo': {'password': password}})
services = LOG_CFG['logs']
level = {"DEBUG": logging.DEBUG, "ERROR": logging.ERROR, "INFO": logging.INFO}

Max_Size = {"/var/log/hare/consul-watch-service.log": 100,
            "/var/log/hare/consul-elect-rc-leader.log": 100,
            "/var/log/hare/consul-proto-rc.log": 100,
            "/var/log/hare/consul-watch-handler.log": 100,
            "/var/log/hare": 400,
            "/var/log/elasticsearch/elasticsearch_cluster.log": 20,
            "/var/log/elasticsearch/elasticsearch_cluster_index_search_slowlog.log": -1,
            "/var/log/elasticsearch/elasticsearch_cluster_index_indexing_slowlog.log": -1,
            "/var/log/seagate/csm/csm_agent.log": 50,
            "/var/log/seagate/csm/csm_cli.log": 100,
            "/var/log/seagate/support_bundle": -1,
            "/var/log/seagate/csm/csm_middleware.log": 100,
            "/var/log/seagate/cortx/ha/cortxha.log": 300,
            "/var/log/seagate/cortx/ha/resource_agent.log": 300,
            "/var/log/seagate/cortx/ha/ha_setup.log": 300,
            "/var/log/seagate/cortx/ha": 300,
            "/var/log/messages": -1,
            "/var/mero": 650,
            "/var/motr": 4325,
            "/var/log/crash": -1,
            "/var/log/secure": -1,
            "/var/log/dmesg": -1,
            "/opt/seagate/cortx/provisioner": -1,
            "/var/log/seagate/provisioner": 600,
            "/var/log/seagate/s3/audit/audit.log": 100,
            "/var/log/seagate/s3": 16896,
            "/var/log/haproxy": 200,
            "/var/log/seagate/auth/server/app.log": 20,
            "/var/log/slapd.log": 100,
            "/var/log/rabbitmq": 140,
            "/var/log/cortx/sspl": 200,
            }

Max_Size_Component = {"consul": 400,
                      "elasticsearch": 20,
                      "csm_agent": 50,
                      "csm_cli": 100,
                      "csm_web_server": 100,
                      "ha_lib": 300,
                      "motr": 4975,
                      "provisioner": 600,
                      "s3": 16996,
                      "haproxy": 200,
                      "s3auth": 20,
                      "ldap": 100,
                      "rabbitmq": 140,
                      "sspl": 200,
                      }


def init_loghandler(log):
    """Initialize logger handler"""
    log.setLevel(level.get(LOG_CFG['logging_Level']))
    fh = logging.FileHandler('diskspace_analyser.log', mode='w')
    fh.setLevel(level.get(LOG_CFG['logging_Level']))
    ch = logging.StreamHandler()
    ch.setLevel(level.get(LOG_CFG['logging_Level']))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    log.addHandler(fh)
    log.addHandler(ch)


def sigint_handler(signum, frame):
    """Initialize  sigint handler"""
    print('SIGINT handler called with signal ', signum)
    log.info('Signal handler called with signal {}, exiting process'.format(signum))
    sys.exit(0)


class YamlError(Exception):
    """Check for yaml file format"""
    def __init__(self, name, message=""):
        self.message = message
        self.name = name
        super().__init__(self.message)

    def __str__(self):
        return '{} has an invalid yaml syntax'.format(self.name)


class StatsException(Exception):
    """Exception handler"""
    def __init__(self, message=""):
        self.message = message
        super().__init__(self.message)


class LogAnalyser(TestCase):
    """Analysis Log on shared POD container"""
    logdir = "/shared/var/log" #shared POD address /shared

    def __init__(self):
        """Initialize variables"""
        self.stats = dict()
        #processes = LOG_CFG.keys()
        self.szmap = dict()
        self.svc_log_sz = dict()
        self.series = dict()

    def init_Connections(self):
        """Connection Initialization"""
        global USER

        self.connections = [Connection(host, user=USER, connect_kwargs={'password': passwords[host]},
                            config=Config(overrides={'sudo': {'password': passwords[host]}}))
                            for host in core_hosts]
        self.connections[:] = [c for c in self.connections if 'Linux' in c.run('uname -s', pty=False).stdout]
        self.ctg = SerialGroup.from_connections(self.connections)

    def build_command(self, path=None):
        """Build command """
        command = ''
        if path:
            command = "df -h " + path + " | tail -n1 | awk '{print $5}'"
        else:
            command = "df -h " + LogAnalyser.logdir + " | tail -n1 | awk '{print $5}'"

        return command

    def collect_basedir_usage(self, command=None):
        """Collect log directory log-file size information"""
        stats = dict()
        try:
            if not command:
                command = self.build_command()
            results = self.ctg.run(command, hide=True)
            for res in results.values():
                stats.update({res.connection.host: res.stdout})
            return stats
        except GroupException as ge:
            for cd, runner in ge.result.items():
                if isinstance(runner, runners.Result):
                    log.info("Successfully executed cmd on {} and output is {}"
                                    .format(cd.host, runner.stdout.strip()))
                    if cd.host not in stats:
                        stats.update({cd.host: runner.stdout})
                elif isinstance(runner, OSError):
                    log.error("Error in executing cmd on {}, output is {}"
                                 .format(cd.host, runner.stdout.strip()))
                elif isinstance(runner, paramiko.ssh_exception.AuthenticationException):
                    log.error("Authentication exception on {}".format(cd.host, ))
                else:
                    log.error("Exception occurred while running df command on {}".format(cd.host))
        finally:
            return stats

    def analyse(self, conn):
        """Analyse log collected from shared POD container"""
        cmd = "find /shared/var/log -type f -exec du -s {} + | sort -nr"
        output = conn.run(cmd, hide=True)
        lines = output.stdout.split("\n")
        host = output.connection.host
        szmap = dict()
        self.szmap.update({host: szmap})
        for line in lines:
            log.info(line)
            tokens = line.split("\t")
            if len(tokens) == 2:
                szmap.update({tokens[1].strip(): int(tokens[0].strip())})

        total_sz = 0
        svc_log_sz = dict()
        self.svc_log_sz.update({host: svc_log_sz})
        svcs = LOG_CFG['logs']
        for svc in svcs.keys():
            if isinstance(svcs[svc], list):
                for log_file in svcs[svc]:
                    # soft assert
                    try:
                        msg = "Log file/dir {} is not present in szmap".format(log_file)
                        self.assertTrue(log_file in szmap, msg)
                    except AssertionError:
                        _, ig, tb = sys.exc_info()
                        tb_info = traceback.extract_tb(tb)
                        filename, line, func, text = tb_info[-1]
                        log.debug("Assertion Error occurred on line {} in statement {}".format(line, text))

                    total_sz += szmap.get(log_file, 0)
                    if szmap.get(log_file) is None:
                        continue
                    svc_log_sz.update({svc: svc_log_sz.get(svc, 0) + szmap.get(log_file)})
            elif isinstance(svcs[svc], str):
                try:
                    msg = "Log file/dir {} is not present in szmap".format(svcs[svc])
                    self.assertTrue(svcs[svc] in szmap, msg)
                except AssertionError:
                    pass
                    _, ig, tb = sys.exc_info()
                    tb_info = traceback.extract_tb(tb)
                    filename, line, func, text = tb_info[-1]
                    log.debug("Assertion Error occured on line {} in statement {}".format(line, text))
                total_sz += szmap.get(log_file, 0)
                if szmap.get(log_file) is None:
                    continue
                svc_log_sz.update({svc: svc_log_sz.get(svc, 0) + szmap.get(log_file)})
        log.info("For Host {} Cortx Logs size in MBs group by service are:".format(host))
        self.roundoff_MB(svc_log_sz)
        log.info(svc_log_sz)
        log.info("For node {}, Total size of component log files is {} MB".format(host, str(total_sz / 1024)))

    def roundoff_MB(self, svc_log_sz):
        for svc in svc_log_sz:
            svc_log_sz[svc] = round(svc_log_sz[svc] / 1024, 2)

    def create_du_header(self):
        with open('du_nodes_trend', mode='w') as fd:
            fd.write('Var/log FS Node wise Usage\n')
            fd.write('Node(s)                  Size (MBs)      TimeStamp\n')
            log.info('Disk Space Node wise Summary')

    def plot_series(self):
        ts = self.collect_basedir_usage("date")
        # In LDR1 both nodes in same timezone
        for k, v in ts.items():
            try:
                v = v[:-1] if v.endswith('\n') else v[:]
                break
            except Exception as fault:
                log.error("Exception {}".format(str(sys.exc_info())))
        now = v
        with open('du_nodes_trend', mode='a') as fd:
            ul = self.collect_basedir_usage("df -m /var/log  | tail -n1 | awk '{print $3}'")
            for k, v in ul.items():
                if k in core_hosts:
                    try:
                        v = v[:-1] if v.endswith('\n') else v[:]
                        line = k + ' ' * (27 - len(k)) + \
                               v + ' ' * (16 - len(v)) + \
                               now
                        fd.write(line + '\n')
                        log.info(line)
                    except Exception as fault:
                        log.error("Exception {}".format(str(sys.exc_info())))

    def plog_stats(self):
        """Component wise log size summary"""
        now = str(datetime.datetime.now())
        with open('diskspace_summary', mode='w') as hndl:
            hndl.write('Disk Space Summary\n')
            log.info('Disk Space Summary')
            for host in self.svc_log_sz:
                hndl.write('Host {} \n\n'.format(host))
                log.info('Host {} '.format(host))
                # component 27 and Size 16 max size 11
                hndl.write('Component                  Size (MBs)      Max Size   TimeStamp\n')
                log.info('Component                  Size (MBs)      Max Size   TimeStamp')
                for svc in self.svc_log_sz[host]:
                    sz = str(self.svc_log_sz[host][svc])
                    s = svc + ' ' * (27 - len(svc)) + \
                        sz + ' ' * (16 - len(sz)) + \
                        str(Max_Size_Component.get(svc)) + ' ' * (11 - len(str(Max_Size_Component.get(svc)))) + \
                        now
                    hndl.write(s + '\n')
                    log.info(s)

    def _run(self):
        st = self.collect_basedir_usage()
        if not st:
            raise StatsException('Stats not collected due to an exception')
        ul = self.collect_basedir_usage("df -h " + LogAnalyser.logdir + " | tail -n1 | awk '{print $3}'")
        assertions = list()
        for k, v in st.items():
            if k in core_hosts:
                # soft assert
                try:
                    v = v[:-2] if v.endswith('\n') else v[:-1]
                    msg = "/shared/var/log disk usage percent limit exceeded on POD container {}".format(k)
                    self.assertTrue(int(v) < LOG_CFG['limits']['total_per_limit'], msg)
                    log.info("/shared/var/log disk usage is {} %".format(str(v)))
                except AssertionError as fault:
                    log.error("Exception {}".format(str(sys.exc_info())))
                    assertions.append((k, str(fault)))

        # decide to exit now in case of /var/log usage limit exceeded
        if assertions:
            m = "/var/log disk usage percent exceeded specified limit"
            nodes = list()
            for h, f in assertions:
                nodes.append(h)
            h = ';'.join(nodes)
            send_mail(LOG_CFG['smtp']['smtpserver'], LOG_CFG['smtp']['from_list'],
                      LOG_CFG['smtp']['to_list'], m, h)
            j = [v1 + " " + v2 for v1, v2 in assertions]
            raise AssertionError(" ".join(j))

        for k, v in ul.items():
            if k in core_hosts:
                try:
                    unit, v = v[-2], v[:-2]
                    if unit == 'G':
                        v = float(v) * 1024 * 1024 * 1024
                    elif unit == 'M':
                        v = float(v) * 1024 * 1024

                    msg = "/var/log disk space usage limit exceeded on node {}".format(k)
                    self.assertTrue(float(v) < LOG_CFG['limits']['total_usage_limit'], msg)

                    log.info("Var/log disk usage is {} Bytes".format(str(v)))
                except AssertionError as fault:
                    log.error("Exception {}".format(str(sys.exc_info())))
                    assertions.append((k, str(fault)))

        if assertions:
            nodes = list()
            for h, f in assertions:
                nodes.append(h)
            h = ';'.join(nodes)
            m = "/var/log disk space usage size exceeded specified limit"
            send_mail(LOG_CFG['smtp']['smtpserver'], LOG_CFG['smtp']['from_list'],
                      LOG_CFG['smtp']['to_list'], m, h)
            log.error("/var/log Disk usage limit specified in config exceeded")
            j = [v1 + " " + v2 for v1, v2 in assertions]
            raise AssertionError(" ".join(j))

        for conn in self.connections:
            self.analyse(conn)
        log.info("Disk Usage Report")
        self.plog_stats()
        self.plot_series()

    def run(self):
        """Class Run function"""
        global log
        signal.signal(signal.SIGINT, sigint_handler)
        init_loghandler(log)
        self.init_Connections()
        self.create_du_header()
        interval = LOG_CFG['interval']
        _retries = LOG_CFG['retries']
        retries = _retries
        retry_exceeded = False
        while True:
            if retry_exceeded:
                log.error("The Nodes can't be connected after 10 retries exiting the script")
                break
            retries = _retries
            time.sleep(interval)
            try:
                [c for c in self.connections if 'Linux' in c.run('uname -s', pty=False).stdout]
            except Exception as fault:
                # reinit connections and try for 10 retries if not connected
                log.warning("Connections to nodes were broken. Retrying...")
                while True:
                    try:
                        if retries <= 0:
                            retry_exceeded = True
                            break
                        self.init_Connections()
                        break
                    except Exception as e:
                        log.warning("The Nodes can't be connected, they might be restarting or halted")
                        retries -= 1
                        time.sleep(60)

            try:
                self._run()
            except Exception as fault:
                log.exception("Exception occurred while running script")
                log.info('Continue running...')


def send_mail(smtpsrv, fromlist, tolist, msg, hosts):
    """Email configuration when Log Size Limit exceeds"""
    try:
        smtpserver = smtplib.SMTP(smtpsrv, 25)
        passwd = base64.b64decode(bytes(LOG_CFG['smtp']['passwd'], 'utf-8'))
        smtpserver.login(fromlist, passwd.decode("utf-8"))
        subject = "Alert: /var/log size exceeded limit for nodes {}".format(hosts)
        header = "To: %s\nFrom: %s\nSubject:%s \n\n" % (tolist, fromlist, subject)
        msg = '%s \n %s  \n' % (header, msg)
        smtpserver.sendmail(fromlist, tolist, msg)
        smtpserver.quit()
        log.info("Alert email sent to users {}".format(tolist))
    except Exception as fault:
        log.info("failed to send the log analyser mail to intended recipient: {}".format(fault))


# if __name__ == "__main__":
#     la = LogAnalyser()
#     la.run()
