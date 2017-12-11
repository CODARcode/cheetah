import os
import stat
import datetime
import numbers


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


def parse_timedelta_seconds(v):
    """
    Parse a time duration. Can be a number of seconds (integer only),
    a timedelta object, or a string in "HH:MM:SS" format. Returns the number
    of seconds in the duration as an int, safe for JSON serialization or
    passing to time.sleep.

    >>> parse_timedelta_seconds('15')
    15
    >>> parse_timedelta_seconds('01:15')
    75
    >>> parse_timedelta_seconds('10:00:05')
    36005
    >>> parse_timedelta_seconds(12345)
    12345
    >>> parse_timedelta_seconds(datetime.timedelta(days=1, seconds=7))
    86407
    >>> parse_timedelta_seconds(1.1)
    Traceback (most recent call last):
        ...
    ValueError: Invalid duration (must be timedelta, int, or 'HH:MM:SS'): 1.1
    >>> parse_timedelta_seconds("12:34:34bad")
    Traceback (most recent call last):
        ...
    ValueError: Invalid duration string, must be HH:MM:SS format
    """
    if isinstance(v, int):
        return v
    if isinstance(v, datetime.timedelta):
        return int(v.total_seconds())
    if isinstance(v, str):
        parts = v.split(":")
        def raise_ve():
            raise ValueError(
                "Invalid duration string, must be HH:MM:SS format")
        try:
            values = [int(x) for x in parts]
        except ValueError:
            raise_ve()
        if len(parts) not in (1, 2, 3):
            raise_ve()
        # pad with zeros
        values = [0] * (3-len(values)) + values
        td = datetime.timedelta(hours=values[0], minutes=values[1],
                                seconds=values[2])
        return int(td.total_seconds())

    raise ValueError(
        "Invalid duration (must be timedelta, int, or 'HH:MM:SS'): %r" % v)


def relative_or_absolute_path(prefix, path):
    """If path is an absolute path, return as is, otherwise pre-pend prefix."""
    if path.startswith("/"):
        return path
    return os.path.join(prefix, path)


def relative_or_absolute_path_list(prefix, path_list):
    return [relative_or_absolute_path(prefix, path) for path in path_list]
