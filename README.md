# cortx-test

Test Automation project for LDR R2 and future versions.

Steps to run test automation locally:

1. Setup virtual environment with Python 3.7. 
   Install all required packages from requirements.txt file.
2. Run one of the following commands as per your needs.

Running Test locally in distributed mode:

pytest  --capture=no --log-cli-level=10 --local=True -d --tx 3*popen -rA unittests\test_reporting_and_logging_hooks.py

Running test plans or Test execution in dev environment
pytest  --capture=no --log-cli-level=10 --te_tkt TEST-17412 -d --tx 3*popen -rA unittests\test_reporting_and_logging_hooks.py

pytest  --capture=no --log-cli-level=10 --te_tkt TEST-17412 -rA unittests\test_reporting_and_logging_hooks.py


When you wan to run test and updated JIRA and Report DB
with results

Use Test runner command
python testrunner.py -te TEST-17412


