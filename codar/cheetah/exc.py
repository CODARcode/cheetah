"""
Exceptions.
"""


class CheetahException(Exception):
    pass


class MachineNotFound(CheetahException):
    def __init__(self, machine_name):
        Exception.__init__(self, "No machine found with name '%s'" %
                           machine_name)


class CampaignParseError(CheetahException):
    pass
