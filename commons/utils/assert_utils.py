#!/usr/bin/python
# -*- coding: utf-8 -*-

import pytest
from commons.utils.comparison import *


def compare(*argv, **kwargs):
    """
    Function to compare objects of any data type.
    Optional parameters:
    case_check: Case check for str comparison (True: Check case, False:
    Ignore case)
    key_check: For comparison of key of dict (True: Check if dict contains
    the given key)
    value_check: For comparison of value of dict (True: Check if dict contains
    the given value)
    sequence_item_check: For comparison of element of list/tuple (True: Check if
    list/tuple contains given element/s)
    sequence_order_check: For comparison of order of elements of list/tuple
    (True: Check order of elements of given lists)
    compare_text: For comparison of text having mixed data types (True:
    Compare multiline texts having mixed data types)
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

    if len(argv) != 2:
        assert len(argv) == 2, "Please provide correct number of operands. " \
                               "Two operands are supported"
    else:
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
