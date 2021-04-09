from setuptools import setup, find_packages

with open('LICENSE', 'r') as lf:
    license = lf.read()

with open('README.md', 'r') as rf:
    long_description = rf.read()

with open('requirements.txt', 'r') as rf:
    lineiter = (line.strip() for line in rf)
    reqs = [line for line in lineiter if line and not line.startswith("#")]

setup(name="cortxtest",
      version='1.0.0',
      description="Python distribution for cortx-text",
      url="https://github.com/Seagate/cortx-test.git",
      license=license,
      long_description=long_description,
      zip_safe=False,
      packages=find_packages(),
      include_package_data=True,
      python_requires='==3.7',
      scripts=['try.py','commons/try2.py','testrunner.py','drunner.py'],
      install_requires=reqs,
      #package_data={'cortxtest': ['config/common_config.yaml']},
      )
