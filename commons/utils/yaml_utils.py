"""
Generic YAML files utilities
"""

# Standard library
import logging
import os
import yaml

import commons.errorcodes as cterr
from commons.exceptions import CTException

log = logging.getLogger(__name__)


def read_yaml(fpath):
    """Read yaml file and return dictionary/list of the content"""
    if os.path.isfile(fpath):
        with open(fpath) as fin:
            try:
                data = yaml.safe_load(fin)
            except yaml.YAMLError as exc:
                err_msg = "Failed to parse: {}\n{}".format(fpath, str(exc))
                raise CTException(cterr.YAML_SYNTAX_ERROR, err_msg)

    else:
        err_msg = "Specified file doesn't exist: {}".format(fpath)
        raise CTException(cterr.FILE_MISSING, err_msg)

    return data