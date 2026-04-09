import os
import sys

def to_bool_strict(value):
    if str(value) == "1":
        return True
    if str(value) == "0":
        return False
    if value is None:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def get_app_directory():
    if hasattr(sys, "_MEIPASS"):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource (to be compatible with PyInstaller).
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)