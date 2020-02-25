import os
import sys
import json
import shlex
import subprocess
from functools import partial
from datetime import datetime


def now_ts():
    """
    get timestamps of now

    :return: float, timestamps
    """
    return datetime.now().timestamp()


def ts2str(ts):
    """
    transform timestamp to corresponding formatted string

    :param ts: int, timestamps.
    :return: str, eg. "2020-02-02, 02:02:20"
    """
    do = datetime.fromtimestamp(ts)
    return do.strftime("%Y-%m-%d, %H:%M:%S")


def load_json(conf_file):
    """
    load json file and return dict

    :param conf_file: str, absolute json file path
    :return: Dict.
    """
    with open(conf_file, "r") as fp:
        conf_dict = json.load(fp)
    return conf_dict


def print_json(json_dict, indent=2):
    """
    print python dict with pretty indent

    :param json_dict: Dict.
    :param indent: Optional[int], default 2.
    :return: None.
    """
    print(json.dumps(json_dict, indent=indent))


def simple_template_render(template, output, var_dict):
    """
    render template file to output file
    with variable substitution defined by var_dict.
    template file vars are defined within {var}.

    :param template: str. Absolute file name for template file.
    :param output: str. Absolute file name for output file (create or overwrite).
    :param var_dict: Dict[str, str].
    :return: None.
    """
    # jinja is of course better but again no external dependence is required
    with open(template, "r") as f:
        l = f.read()
    nl = l.format(**var_dict)
    with open(output, "w") as f:
        f.writelines([nl])


def _replace(replace_func, s):
    """
    inner function for :py:function:`replace_wildcard`

    :param replace_func: Callable[[char], char].
        Char to char function. eg f(a) = A, indicates %a should be replaced by A.
    :param s: str, that match r"[\%]+[^\%]*"
    :return: str, transformed after wildcard substitution
    """

    if len(s) <= 1:
        return s
    if s[0] != "%":
        return s
    if s[-1] == "%":
        return s
    if s[1] == "%":
        return s[1:]
    if s[1] != "%":
        return replace_func(s[1]) + s[2:]


def replace_wildcard(replace_func, s):
    """
    replace %a type wildcard in the string based on customized function replace_func.

    :param replace_func: Callable[[char], char].
        Char to char function. eg f(a) = A, indicates %a should be replaced by A.
    :param s: str, the string possibly with %a type wildcards, eg. "bc%de%%a"
    :return: str, the string with %a type wildcards all replaced
    """
    state = 0
    # 0: the last one in normal 1: the last one is %
    rl = []
    r = ""
    for c in s:
        if c == "%" and state == 0:
            rl.append(r)
            r = c
            state = 1
        elif c == "%" and state == 1:
            r += c
            state = 1
        else:
            r += c
            state = 0
    rl.append(r)
    rl = [r for r in rl if r]
    _preplace = partial(_replace, replace_func)
    return "".join(list(map(_preplace, rl)))


# editors to try if VISUAL and EDITOR are not set
_default_editors = ["vim", "vi", "emacs", "nano"]


def which(binary, path=None):
    """
    Like `which` in linux.
    Find absolute binary path given command shortcut binary.

    :param binary: str. name for binary command.
    :param path: Optional[str], default None. If None, `PATH` is searched
    :return: Optional[str], absolute path for binary.
        None if binary not found in path.
    """
    if not path:
        path = os.environ.get("PATH", "")

    if isinstance(path, str):
        path = path.split(os.pathsep)

    for directory in path:
        exe = os.path.join(directory, binary)
        if os.path.isfile(exe) and os.access(exe, os.X_OK):
            return exe

    return None


def editor(path, **kwargs):
    """
    Invoke the user's editor.
    This will try to execute the following, in order:
    1. $VISUAL <args>    # the "visual" editor (per POSIX)
    2. $EDITOR <args>    # the regular editor (per POSIX)
    3. some default editor (see ``_default_editors``) with <args>
    If an environment variable isn't defined, it is skipped.  If it
    points to something that can't be executed, we'll print a
    warning. And if we can't find anything that can be executed after
    searching the full list above, we'll raise an error.

    :param path: str. Absolute path for file to be opened by editor.
    :return: bool. True if editor is found and open.
    """
    # allow this to be customized for testing
    _run = kwargs.get("_run", subprocess.run)

    def try_exec(exe):
        """
        Try to execute an editor with ``subprocess.run``, and warn if it fails.

        :return: (bool) False if the editor failed, ideally does not
            return if ``run`` succeeds, and ``True`` if the
            ``run`` does return successfully.
        """
        try:
            _run(exe)
            return True

        except OSError as e:
            # Show variable we were trying to use, if it's from one
            print("Could not execute %s due to error:" % exe, str(e), file=sys.stderr)
            return False

    def try_env_var(var):
        """
        Find an editor from an environment variable and try to exec it.
        This will warn if the variable points to something is not
        executable, or if there is an error when trying to exec it.
        """
        if var not in os.environ:
            return False

        return try_exec(shlex.split(os.environ[var] + " " + path))

    # try standard environment variables
    if try_env_var("VISUAL"):
        return
    if try_env_var("EDITOR"):
        return

    # nothing worked -- try the default we can find
    for exe in _default_editors:
        if try_exec(shlex.split(which(exe) + " " + path)):
            return

    # Fail if nothing could be found
    print(
        "No text editor found! Please set the VISUAL and/or EDITOR "
        "environment variable(s) to your preferred text editor."
    )
