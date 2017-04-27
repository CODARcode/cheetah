import os
import stat


def make_executable(path):
    current_mode = os.stat(path).st_mode
    os.chmod(path, current_mode | stat.S_IEXEC)
