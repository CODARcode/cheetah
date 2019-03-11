"""
Exceptions.
"""


class SavannaException(Exception):
    pass


class MachineNotFound(SavannaException):
    def __init__(self, machine_name):
        Exception.__init__(self, "No machine found with name '%s'" %
                           machine_name)
