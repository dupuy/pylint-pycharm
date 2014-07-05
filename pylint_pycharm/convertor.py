#!/usr/bin/env python

"""
Main module of pylint-pycharm project
"""
import sys
import os
import subprocess
import re

MESSAGE_PATTERN = r"^(?P<filename>[^:]*):(?P<line_number>\d+)(:(?P<column>\d+))?: (?P<description>.*)"
PYCHARM_MESSAGE_FORMAT = "%(full_path)s:%(line_number)s:%(column)s: %(description)s"

HELP_TEXT = "Please read README file for more information"
# HELP_TEXT = open(os.path.join("..", "README")).read()

EXCEPTION_MESSAGE_TEMPLATE = "Error: %(error_message)s\n%(help_text)s"


def convert(args, out_stream):
    """
    Enter point to the program
    """
    try:
        # find module or package name for code checking
        module_name = parse_module_name(args)

        # find directory full path where module or package is
        root_path = os.path.abspath(os.path.dirname(module_name))

        virtualenv_path = pop_arg_from_list(args, "--virtualenv")
        msg_template = pop_arg_from_list(args, "--msg-template")

        # remove non-pylint parameters
        pylint_args = parse_pylint_args(args)

        # add --output-format (or --msg-template) argument
        if msg_template is not None:
            add_arg_to_list(pylint_args, "--msg-template",
                            "{path}:{line}:{column}: [{msg_id}({symbol}), {obj}] {msg}")
        else:
            add_arg_to_list(pylint_args, "--output-format", "parseable")

        # format command to run in subprocess
        command = format_command_for_process(module_name, pylint_args, virtualenv_path)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        pylint_output = process.stdout.read()

        # parse result
        output_text = parse_output(root_path, pylint_output)
        out_stream.write(output_text)
    except PylintPycharmException as ex:
        out_stream.write(EXCEPTION_MESSAGE_TEMPLATE %
                         {"error_message": ex.message, "help_text": HELP_TEXT})


def get_root_path(module_name):
    if os.path.isfile(module_name):
        return os.path.abspath(os.path.dirname(module_name))
    else:
        return os.path.abspath(module_name)


def pop_arg_from_list(args, name):
    new_args = []
    result = None
    i = 0
    for arg in args:
        i += 1
        if arg.startswith(name):
            try:
                result = arg.split("=")[1]
            except IndexError:
                result = args[i]
        else:
            new_args.append(arg)
    return result


def add_arg_to_list(args, name, value):
    idx = -1
    param = '%s="%s"' % (name, value.replace('"', '\\"'))
    for i, arg in enumerate(args):
        if arg.startswith(name):
            idx = i
    if idx > -1:
        args[idx] = param
    else:
        args.append(param)


def parse_module_name(args):
    """
    Search and return module or package name from list of arguments
    """
    module_names = [arg for arg in args[1:] if not arg.startswith("--")]
    if not module_names:
        raise PylintPycharmException("Can not find module or package name for analyse")
    if len(module_names) > 1:
        raise PylintPycharmException("More than one module or package name")
    return module_names[0]


def parse_pylint_args(args):
    """
    remove arguments accepted by this utility and leave only arguments accepted by pylint
    """
    return ['"' + arg.replace('"', '\\"') + '"' for arg in args
            if arg.startswith("--") and (not arg.startswith("--virtualenv"))]


def format_command_for_process(module_name, pylint_args, virtualenv_path=None):
    """
    Format command to run in subprocess.
    """
    program = "pylint"
    if virtualenv_path:
        fp1 = os.path.join(virtualenv_path, "bin", "activate")
        program = ". %s && %s" % (fp1, program)
    args_str = " ".join(pylint_args)
    return "%s %s %s" % (program, module_name, args_str)


def parse_output(root_path, txt):
    """
    Parse output of pylint and change relative paths to absolute paths
    """
    result = []
    lines = txt.split("\n")
    for line in lines:
        ms = re.match(MESSAGE_PATTERN, line)
        if ms:
            full_path = os.path.join(root_path, ms.group(1))
            data = {"full_path": full_path,
                    "line_number": ms.group("line_number"),
                    "column": ms.group("column") or '0',
                    "description": ms.group("description")}
            result.append(PYCHARM_MESSAGE_FORMAT % data)
        else:
            result.append(line)
    return "\n".join(result)


class PylintPycharmException(Exception):
    pass

if __name__ == "__main__":
    convert(sys.argv, sys.stdout)
