import logging
from pprint import pformat

import commons.errorcodes as errcodes

log = logging.getLogger(__name__)


class CTException(Exception):
    """
    Exception class for CTP failures.
    """

    def __init__(self, ct_error, msg, **kwargs) -> None:
        """
        Create an CTException.

        :param ctp_error: CTPError object.
        :param msg      : String error message from user.
        :param **kwargs : All other keyword arguments will be stored in self.kwargs.
        :raises TypeError: If ctp_error is not a CTPError object.
        """
        if not isinstance(ct_error, errcodes.CTError):
            raise TypeError("'ctp_error' has to be of type 'CTPError'!")

        self.ct_error = ct_error
        self.message = msg
        self.kwargs = kwargs  # Dictionary of 'other' information

    def __str__(self):
        """
        Return human-readable string representation of this exception
        """
        return "CTException: EC({})\nError Desc: {}\nError Message: {}\nOther info:\n{}".format(self.ct_error.code,
                                                                                                 self.ct_error.desc,
                                                                                                 self.message,
                                                                                                 pformat(self.kwargs))

