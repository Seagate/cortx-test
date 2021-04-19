#!/bin/bash
TGT_NAME=`echo "$HOSTNAME" | sed  's/\..*//'`
echo "Target node entry name: $TGT_NAME"
pytest tests/s3/test_object_tagging.py::TestObjectTagging --local True --target $TGT_NAME