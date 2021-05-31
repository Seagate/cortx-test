#!/usr/bin/env python3

import os
import sys
import pathlib
import argparse
import logging
import datetime
from subprocess import Popen




LOGGER = logging.getLogger(__name__)


class CsmGuiTest:
	def __init__(self):
		self.log_file_name=\
			f"/tmp/csm_test_results_{datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d-%H:%M:%S')}.log"
		self.csmtestdir = "/opt/seagate/cortx/csm/csm_test/"
		
	def arg_parser(self):
		parser = argparse.ArgumentParser()
		parser.add_argument("-l", "--csm_url", type=str, default="https://localhost:28100/#/",
							help="CSM GUI URL")
		parser.add_argument("-b", "--browser", type=str, default="chrome",
							help="browser")
		parser.add_argument("-u", "--csm_user", type=str,
							help="username")
		parser.add_argument("-p", "--csm_pass", type=str,
							help="password")
		parser.add_argument("-m", "--headless", type=str, default="True",
							help="headless")
		parser.add_argument("-t", "--test_tags", type=str, default="Sanity_test",
							help="test_tags")
		return parser.parse_args()

	def run_cmd_test(self, args):
		"""
		This method build, run and return robot test results.
		:param args: arguments to build and run csm test.
		:return: Returns the test/test suite status after execution.
		"""
		if os.path.exists(self.log_file_name):
			os.remove(self.log_file_name)
		self.build_csm_test_cmd(args, logFile=self.log_file_name)
		test_status, test_output, test_log, test_report = self.getCsmTestStatus(logFile=self.log_file_name)
		print(test_status)
		return test_status

	def getCsmTestStatus(self, logFile=None):
		"""
		Parse csm_test_results.log file to get
		a) TestStatus: Pass/Fail
		b) Output filepath: XML
		c) Log filepath: xml/html
		d) Report filepath: xml/html
		:param logFile: Log file to update the test result logs.
		:return: Returns the test status after execution.
		"""
		outputfilepath = ''
		logfilepath = ''
		reportfilepath = ''
		TestStatus = "FAIL"
		if logFile is None:
			logFile = self.log_file_name
		with open(logFile, 'r') as file:

			for line in file:
				# For each line, check if line contains the string
				if 'FAIL' in line:
					TestStatus = 'FAIL'
				elif 'PASS' in line:
					TestStatus = 'PASS'

				if "Output: " in line:
					outputfilepath = line.split()[-1]
				if "Log: " in line:
					logfilepath = line.split()[-1]
				if "Report:" in line:
					reportfilepath = line.split()[-1]
		return TestStatus, outputfilepath, logfilepath, reportfilepath

	def build_csm_test_cmd(self, args, logFile=None):
		"""Build a robot command for execution."""
		if logFile is None:
			logFile = self.log_file_name
		headless = " -v headless:" + str(args.headless)
		url = " -v url:"+ str(args.csm_url)
		browser = " -v browser:" + str(args.browser)
		username = " -v username:" + str(args.csm_user)
		password = " -v password:" + str(args.csm_pass)
		RESOURCES = " -v RESOURCES:" + self.csmtestdir
		tag = " -i " + str(args.test_tags)
		directory = " " + self.csmtestdir +"testsuites/."
		reports = " -d " + self.csmtestdir + "reports"

		cmd_line = "robot --timestampoutputs"+reports+url+browser+\
				   username+headless+password+RESOURCES+tag+directory+";cd .."
		log = open(logFile, "w+")
		prc = Popen(cmd_line, shell=True, stdout=log, stderr=log)
		prc.communicate()
		log.close()


def main():
	"""
    Main Entry function using argument parser to parse options and forming robot command.
    and triggers csm test on the target machine.
    """
	obj = CsmGuiTest()
	args = obj.arg_parser()
	obj.run_cmd_test(args)


if __name__ == '__main__':
	sys.path.append(os.path.join(os.path.dirname(pathlib.Path(__file__)), '..', '..'))
	sys.path.append(os.path.join(os.path.dirname(pathlib.Path(os.path.realpath(__file__))), '..', '..'))
	main()

