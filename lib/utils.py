import importlib.util
import sys
import os
import inspect

# Import hacks to avoid managing via python packages


def import_from_file_relative(relative_file_path, member=None):
    frame = inspect.stack()[1][0]
    caller_path = frame.f_locals["__file__"]
    fp = os.path.join(os.path.dirname(caller_path), relative_file_path)
    return import_from_file(fp, member)


def import_from_file(file_path, member=None):
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    if member:
        return getattr(module, member)
    else:
        return module
