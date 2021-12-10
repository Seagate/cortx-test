#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Function for comparison."""
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import re
from difflib import unified_diff
from hamcrest import assert_that, equal_to, has_length, contains_string, \
    equal_to_ignoring_case, has_entries, has_key, has_value, contains_exactly, \
    contains_inanyorder, has_items, has_item, all_of, any_of


def assert_equals(actual, matcher, reason: str = ""):
    """assert_equals"""
    assert_that(matcher, equal_to(actual), reason)


def assert_length(actual, matcher):
    """assert_length."""
    assert_that(matcher, has_length(len(actual)))


def assert_exact_string(string1, string2, message=None):
    """assert_exact_string."""
    assert_that(string1, contains_string(string2), message)


def assert_string(string1, string2):
    """assert_string."""
    assert_that(string1, equal_to_ignoring_case(string2))


def assert_dict_equal(actual, matcher):
    """assert_dict_equal."""
    assert_that(actual, has_entries(matcher))


def assert_dict_equal_key(actual, matcher):
    """assert_dict_equal_key."""
    assert_that(actual, has_key(matcher))


def assert_dict_equal_value(actual, matcher):
    """assert_dict_equal_value."""
    assert_that(actual, has_value(matcher))


def assert_list_order(actual, matcher):
    """assert_list_order"""
    assert_that(actual, contains_exactly(*matcher))


def assert_list_equal(actual, matcher):
    """assert_list_equal."""
    assert_that(actual, contains_inanyorder(*matcher))


def assert_list_items(actual, matcher):
    """assert_list_items."""
    assert_that(actual, has_items(*matcher))


def assert_list_item(actual, matcher):
    """assert_list_item."""
    assert_that(actual, has_item(matcher))


def assert_and(actual, matcher):
    """assert_and."""
    assert_that(actual, all_of(matcher))


def assert_or(actual, matcher):
    """assert_or."""
    assert_that(actual, any_of(matcher))


def assert_compare_text(actual, matcher, context):
    """
    Function to compare multi-lined test having different data types.

    :param actual: First object to be compared
    :param matcher: Second object to be compared
    :param context: Dict having the flag values
    """
    blanklines = context.get('blanklines', False)
    leading_whitespace = context.get('leading_whitespace', True)
    all_whitespace = context.get('all_whitespace', False)
    trailing_whitespace = context.get('trailing_whitespace', True)

    if not trailing_whitespace:
        actual = re.sub(r"\s+$", "", actual)
        matcher = re.sub(r"\s+$", "", matcher)
    if not leading_whitespace:
        actual = re.sub(r"^\s+", "", actual)
        matcher = re.sub(r"^\s+", "", matcher)
    if not all_whitespace:
        actual = re.sub(r"\s+", "", actual)
        matcher = re.sub(r"\s+", "", matcher)
    if not blanklines:
        actual = re.sub(r'\n\s*\n', '\n', actual, re.MULTILINE)
        matcher = re.sub(r'\n\s*\n', '\n', matcher, re.MULTILINE)

    if actual == matcher:
        return

    labelled_actual = repr(actual)
    labelled_matcher = repr(matcher)
    if len(actual) > 10 or len(matcher) > 10:
        if '\n' in actual or '\n' in matcher:
            message = '\n' + '\n'.join(unified_diff(actual.split('\n'),
                                                    matcher.split('\n'), lineterm=''))
        else:
            message = '\n%s\n!=\n%s' % (labelled_actual, labelled_matcher)
    else:
        message = labelled_actual + ' != ' + labelled_matcher

    assert labelled_actual == labelled_matcher, message


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


def assert_false(matcher, reason=""):
    """AssertEqual Implementation."""
    assert not matcher, reason if reason else matcher


def assert_true(matcher, reason=""):
    """AssertTrue Implementation."""
    assert matcher, reason if reason else matcher


def assert_in(actual, matcher, reason=""):
    """AssertIn implementation."""
    assert actual in matcher, reason if reason else matcher


def assert_not_in(actual, matcher, reason=""):
    """AssertIn implementation."""
    assert actual not in matcher, reason if reason else matcher


def assert_equal(actual, matcher, reason=""):
    """AssertEqual Implementation."""
    assert actual == matcher, reason if reason else matcher


def assert_not_equal(actual, matcher, reason=""):
    """AssertNotEqual Implementation."""
    assert actual != matcher, reason if reason else matcher


def assert_greater_equal(actual, matcher, reason=""):
    """AssertGreaterEqual Implementation"""
    assert actual >= matcher, reason if reason else matcher


def assert_is_not_none(actual,reason=""):
    """ AssertIsNotNone Implementation."""
    assert actual != None, reason
