from setuptools import setup, find_packages
import pathlib
import os

with open('LICENSE', 'r') as lf:
    license = lf.read()

with open("README.md", 'r') as rf:
    long_description = rf.read()

with open('requirements.txt', 'r') as rf:
    lineiter = (line.strip() for line in rf)
    reqs = [line for line in lineiter if line and not line.startswith("#")]

setup(name='cortxtest',
      version='1.0',
      # list folders, not files
      #packages=find_packages(),
      packages=['cortxtest.commons',
                'cortxtest.tests'],
      scripts=['cortxtest/try.py','cortxtest/commons/try2.py'],
      package_data={'cortxtest': ['config/common_config.yaml']},
      )
