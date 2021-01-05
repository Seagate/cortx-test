#!/usr/bin/python
# -*- coding: utf-8 -*-

from collections import OrderedDict
from decimal import Decimal
from difflib import unified_diff
import pytest
from hamcrest import *
import re


def assert_equals(x, y):
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
    assert_that(x, has_item(*y))


def assert_and(x, y):
    assert_that(x, all_of(y))


def assert_or(x, y):
    assert_that(x, any_of(y))


def assert_compare_text(x, y, context):
    """
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
        message = labelled_x+' != '+labelled_y

    assert labelled_x != labelled_y, message
