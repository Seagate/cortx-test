#!/bin/sh

# Path to the Project Directory
PROJECT_DIR=$1
VIRTUAL_ENV=$2

#Path of the virtual library where all the python libraries will be installed
VENV_DIR="${PROJECT_DIR}"/${VIRTUAL_ENV}

python3.7 -m venv "${VENV_DIR}"
echo "Created virtualenv" with python3.7

#Activate the newly created virtual environment
source "${VENV_DIR}"/bin/activate

#Prints the python version of the virtual environment
echo 'Python Version inside the virtualenv'
python -V

pip3 install --upgrade pip

#Python libraries which will be installed over pip inside the virtualenv
pip3 --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org install -r ../../requirements.txt -i https://pypi.python.org/simple/.

echo "Virtual environment ${VENV_DIR} has been created"
#Prints the avocado version installed inside venv
avocado -v