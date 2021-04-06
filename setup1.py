import os
import sys
from setuptools import setup
from setuptools import setup, find_packages

with open('LICENSE', 'r') as lf:
    license = lf.read()

with open('README.md', 'r') as rf:
    long_description = rf.read()

def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]

reqs = parse_requirements('requirements.txt')

setup(name='cortx-test',
      version='1.0.0',
      url='https://github.com/Seagate/cortx-py-utils',
      license='Seagate',
      author='Divya Kachhwaha',
      author_email='divya.kachhwaha@seagate.com',
      description='Common Python tests for CORTX',
      package_dir={'cortxtest': '../cortx-test',},
      packages=['cortxtest.ci_tools',
                'cortxtest.core',
                'cortxtest.config',
                'cortxtest.commons',
                'cortxtest.libs',
                'cortxtest.docs',
                'cortxtest.robot',
                'cortxtest.scripts',
                'cortxtest.templates',
                'cortxtest.tests',
                ],
      #packages=find_packages(),
      entry_points={
        'console_scripts': [
            'testrunner=testrunner__main__:main',
        ],},
      include_package_data=True,
      package_data={'cortxtest': ['*.txt']},
      long_description=long_description,
      zip_safe=False,
      python_requires='>=3.7',
      install_requires=reqs)