import os
import datetime
import numbers
import shutil
import stat
import glob
import json
from pathlib import Path


from codar.cheetah import exc


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


def copy_to_dir(source_file, dest_dir, follow_symlinks=True):
    """Wrapper around copyfile with directory destination and more
    control over permissions."""

    # source_file could contain a wildcard. e.g. '*.in' 
    # glob to fetch individual files
    source_files = glob.glob(source_file)
    assert len(source_files) > 0, "Could not find required input file " \
                                  "{0}".format(source_file)
    for file in source_files:
        dest_file = os.path.join(dest_dir, os.path.basename(file))
        copy_to_path(file, dest_file, follow_symlinks)


def copy_to_path(source_file, dest_file, follow_symlinks=True):
    """Wrapper around copyfile that respects umask and preserves
    executability."""
    assert os.path.exists(source_file), "Required input file {0} does not " \
                                        "exist".format(source_file)
    shutil.copyfile(source_file, dest_file, follow_symlinks=follow_symlinks)
    if is_executable(source_file):
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o777 - umask
        os.chmod(dest_file, mode)


def is_executable(fpath):
    stat_result = os.stat(fpath)
    return bool(stat_result.st_mode & stat.S_IXUSR)


def copytree_to_dir(source_dir, dest_dir, follow_symlinks=True):
    """Custom version of copytree that does not preserve permissions, but
    does preserve executability. The goal is to respect the current umask
    but keep executable files executable."""
    names = os.listdir(source_dir)
    os.mkdir(dest_dir)
    for name in names:
        sname = os.path.join(source_dir, name)
        dname = os.path.join(dest_dir, name)
        if not follow_symlinks and os.path.islink(sname):
            linkto = os.readlink(sname)
            os.symlink(linkto, dname)
        elif os.path.isdir(sname):
            copytree_to_dir(sname, dname, follow_symlinks)
        else:
            copy_to_path(sname, dname, follow_symlinks)


def relative_or_absolute_path(prefix, path):
    """If path is an absolute path, return as is, otherwise pre-pend prefix."""
    if path.startswith("/"):
        return path
    return os.path.join(prefix, path)


def relative_or_absolute_path_list(prefix, path_list):
    return [relative_or_absolute_path(prefix, path) for path in path_list]


def get_immediate_subdirs(dir_path):
    """
    Get a list of top-level subdirectories.
    :param dir_path: Directory path to search
    :return: list of subdirectory names
    """
    return [name for name in os.listdir(dir_path) if
            os.path.isdir(os.path.join(dir_path, name))]


def dir_size(path):
    """
    Get the size of the directory represented by path recursively.
    :param path: Path to the dir whose size needs to be calculated
    :return: size in bytes of the dir
    """
    # Closure for recursiveness
    def get_dir_size(path):
        size = 0
        for entry in os.scandir(path):
            if entry.is_file():
                size += entry.stat(follow_symlinks=False).st_size
            elif entry.is_dir():
                size += get_dir_size(entry.path)
        return size

    return get_dir_size(path)


def get_file_size(dir_entry):
    """
    Get size of the file or directory pointed to by path.
    Directory size is recursive; it includes sizes of enclosing files/dirs.
    :param dir_entry: path to the file or directory. Should not contain wildcards.
                      Must be of type DirEntry.
    :return: size in bytes
    """
    #if type(path) is str:
    #    path = Path(path)
    if dir_entry.is_file():
        return os.path.getsize(dir_entry.path)
    elif dir_entry.is_dir():
        return dir_size(dir_entry.path)


def is_campaign_directory(path):
    """Return True if the specified path exists, is a directory, and has a
    .campaign file to indicate it's a top level campaign directory."""
    return (os.path.isdir(path)
            and os.path.isfile(os.path.join(path, '.campaign')))


def require_campaign_directory(path):
    """Raise CheetahException if the specified path is not a top-level
    campaign directory."""
    if not is_campaign_directory(path):
        raise exc.CheetahException("Path '%s' is not a " \
                                   "top-level campaign directory" % path)


def json_config_set_option (filename, key, value):
    with open(filename, "r") as f:
        json_dict = json.load(f)
    assert(key in json_dict)
    json_dict[key] = value

    with open(filename, 'w') as f:
        json.dump(json_dict, f, indent=4)


def find_subdir_path(where, what):
    files_found = glob.glob("{}**/**{}".format(where, what))
    if len(files_found) > 0:
        return files_found[0]
    return None
