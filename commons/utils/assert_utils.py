#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
from difflib import unified_diff
from hamcrest import *


def assert_equals(x, y, reason):
    assert_that(y, equal_to(x))


def assert_length(x, y):
    assert_that(y, has_length(len(x)))


def assert_exact_string(string1, string2):
    assert_that(string1, contains_string(string2))


def assert_string(string1, string2):
    assert_that(string1, equal_to_ignoring_case(string2))


def assert_dict_equal(x, y):
    assert_that(x, has_entries(y))


def assert_dict_equal_key(x, y):
    assert_that(x, has_key(y))


def assert_dict_equal_value(x, y):
    assert_that(x, has_value(y))


def assert_list_order(x, y):
    assert_that(x, contains_exactly(*y))


def assert_list_equal(x, y):
    assert_that(x, contains_inanyorder(*y))


def assert_list_items(x, y):
    assert_that(x, has_items(*y))


def assert_list_item(x, y):
    assert_that(x, has_item(y))


def assert_and(x, y):
    assert_that(x, all_of(y))


def assert_or(x, y):
    assert_that(x, any_of(y))


def assert_compare_text(x, y, context):
    """
    Function to compare multi-lined test having different datatypes.
    :param x: First object to be compared
    :param y: Second object to be compared
    :param context: Dict having the flag values
    """
    blanklines = context.get('blanklines', False)
    leading_whitespace = context.get('leading_whitespace', True)
    all_whitespace = context.get('all_whitespace', False)
    trailing_whitespace = context.get('trailing_whitespace', True)

    if not trailing_whitespace:
        x = re.sub(r"\s+$", "", x)
        y = re.sub(r"\s+$", "", y)
    if not leading_whitespace:
        x = re.sub(r"^\s+", "", x)
        y = re.sub(r"^\s+", "", y)
    if not all_whitespace:
        x = re.sub(r"\s+", "", x)
        y = re.sub(r"\s+", "", y)
    if not blanklines:
        x = re.sub(r'\n\s*\n', '\n', x, re.MULTILINE)
        y = re.sub(r'\n\s*\n', '\n', y, re.MULTILINE)

    if x == y:
        return

    labelled_x = repr(x)
    labelled_y = repr(y)
    if len(x) > 10 or len(y) > 10:
        if '\n' in x or '\n' in y:
            message = '\n' + '\n'.join(unified_diff(x.split('\n'),
                                                    y.split('\n'), lineterm=''))
        else:
            message = '\n%s\n!=\n%s' % (labelled_x, labelled_y)
    else:
        message = labelled_x + ' != ' + labelled_y

    assert labelled_x == labelled_y, message


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
