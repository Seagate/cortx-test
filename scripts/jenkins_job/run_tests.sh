#!/bin/bash
TGT_NAME=`echo "$HOSTNAME" | sed  's/\..*//'`
echo "Target node entry name: $TGT_NAME"
pytest tests/csm/cli/test_cli_csm_user.py::TestCliCSMUser --local True --target $TGT_NAME
