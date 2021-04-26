#!/bin/bash
TGT_NAME=`echo "$HOSTNAME" | sed  's/\..*//'`
echo "Target node entry name: $TGT_NAME"
pytest tests/blackbox/test_cortxcli.py::TestCortxcli::test_2394 --local True --target $TGT_NAME
pytest tests/blackbox/test_cortxcli.py::TestCortxcli::test_2396 --local True --target $TGT_NAME

