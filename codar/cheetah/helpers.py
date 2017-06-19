import os
import stat


def make_executable(path):
    current_mode = os.stat(path).st_mode
    os.chmod(path, current_mode | stat.S_IEXEC)


def swift_escape_string(s):
    """
    Escape backslashes and double quotes in string, so it can be
    embedded in a literal swift string when generatig swift source code.
    """
    s = s.replace("\\", "\\\\")
    s = s.replace("\"", "\\\"")
    return s
