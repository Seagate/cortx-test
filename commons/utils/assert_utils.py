#!/usr/bin/python
# -*- coding: utf-8 -*-

from collections import OrderedDict
from decimal import Decimal
from difflib import unified_diff
from types import GeneratorType
import re
import pytest
from comparison import *


def compare(*argv, **kwargs):
    """

    """
    # case check for str comparison
    case_check = kwargs.get('case_check', False)
    # for comparison of key of dict
    key_check = kwargs.get('key_check', False)
    # for comparison of value of dict
    value_check = kwargs.get('value_check', False)
    # for comparison of element of list/tuple
    sequence_item_check = kwargs.get('sequence_item_check', False)
    # for comparison of order of elements of list/tuple
    sequence_order_check = kwargs.get('sequence_order_check', False)
    # for comparison of text having mixed data types
    compare_text = kwargs.get('compare_text', False)

    dtype = type(argv[0])

    if compare_text:
        assert_compare_text(argv[0], argv[1], kwargs)
    elif dtype is int or dtype is float:
        assert_equals(argv[0], argv[1])
    elif dtype is str:
        if case_check:
            assert_exact_string(argv[0], argv[1])
        else:
            assert_string(argv[0], argv[1])
    elif dtype is dict:
        if key_check:
            assert_dict_equal_key(argv[0], argv[1])
        elif value_check:
            assert_dict_equal_value(argv[0], argv[1])
        else:
            assert_dict_equal(argv[0], argv[1])
    elif dtype is list or dtype is tuple:
        if sequence_order_check:
            assert_list_order(argv[0], argv[1])
        elif sequence_item_check:
            if len(argv[1]) > 1:
                assert_list_items(argv[0], argv[1])
            else:
                assert_list_item(argv[0], argv[1])
        else:
            assert_list_equal(argv[0], argv[1])
