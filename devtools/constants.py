from __future__ import annotations

import os
import platform
import pwd
import sys
import typing

CI = os.getenv("CI")
SYSTEM = platform.system().lower()
MACHINE = platform.machine()
DARWIN = SYSTEM == "darwin"
INTEL_MAC = DARWIN and (MACHINE == "x86_64")
SHELL_UNSET = "(SHELL unset)"

# for matching to download urls in repo config
SYSTEM_MACHINE = f"{SYSTEM}_{MACHINE}"

APP_NAME = "devtools"
APP_DIR = f".{APP_NAME}"

try:
    _term_width = os.get_terminal_size()[0]
except OSError:
    _term_width = 78

TERM_WIDTH = int(os.getenv("COLUMNS", _term_width))
os.environ["COLUMNS"] = str(TERM_WIDTH)

INTERACTIVE = sys.stdout.isatty() and sys.stdin.isatty()

struct_passwd = pwd.getpwuid(os.getuid())
shell_path = os.getenv("SHELL", struct_passwd.pw_shell)
shell = shell_path.rsplit("/", 1)[-1]
user = struct_passwd.pw_name

# the *original* user's environment, readonly
user_environ: typing.Mapping[str, str] = os.environ.copy()

home = user_environ["HOME"] if CI else struct_passwd.pw_dir

root = os.path.normpath(
    os.path.expanduser("~/.local/share/sentry-devtools/")
)  # todo: dubious
config = os.getenv("CONFIG_PATH", os.path.join(root, "config.ini"))

homebrew_repo = "/opt/homebrew"
homebrew_bin = f"{homebrew_repo}/bin"
if INTEL_MAC:
    homebrew_repo = "/usr/local/Homebrew"
    homebrew_bin = "/usr/local/bin"
