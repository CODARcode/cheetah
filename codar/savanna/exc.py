"""
Savanna package exceptions.
"""

class SavannaException(Exception):
    """
    Root of Savanna exception hierarchy.
    """
    pass


class ParameterNameException(SavannaException):
    """
    Error related to parameter names.
    """
    pass


class ParameterValueException(SavannaException):
    """
    Error related to parameter values.
    """
    pass
