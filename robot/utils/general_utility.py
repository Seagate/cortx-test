"""This Utility function is for general python utility required."""


def size_conversion_to_byte(value):
    """
    This function consider string value and convert it to bytes
    :param value: size value in string
    :return: converted bytes value
    """
    convert_variable = {
        "KB": lambda x: x*1024,
        "MB": lambda x: x*1048576,
        "GB": lambda x: x*1073741824,
        "TB": lambda x: x*1099511627776,
    }
    return convert_variable[value[-2:]](float(value[:-2]))
