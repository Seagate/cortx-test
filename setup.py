from setuptools import setup, find_packages

setup(name="cortxtest",
      version='1.0.0',
      description="Python distribution for cortx-text",
      url="https://github.com/Seagate/cortx-test.git",
      license="Seagate",
      author="Seagate",
      author_email="seagate.com",
      long_description="Cortx-test automation test installation package",
      packages=find_packages(),
      include_package_data=True,
      python_requires='==3.7',
      entry_points={
        'console_scripts': [
            'testrunner=testrunner__main__:main',
        ],},


      )
