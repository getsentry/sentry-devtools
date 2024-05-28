from __future__ import annotations

import logging

from devenv.constants import SYSTEM_MACHINE
from devenv.lib import config
from devenv.lib import gcloud
from devenv.lib import proc
from devenv.lib import venv

logger = logging.getLogger(__name__)


def ensure_gcloud_authed(gcloud: str) -> None:
    # gcloud auth list --filter=status:ACTIVE --format="value(account)"
    # should return a sentry.io email.
    # if no accounts exist or are active, stdout shouldnt have anything (rc is still 0).

    # A faster way to check is gcloud config config-helper,
    # which exits 1 if there is no active account,
    # and also prompts for yubikey 2FA if it needs refreshing.
    try:
        proc.run((gcloud, "config", "config-helper"), stdout=True)
        return
    except RuntimeError:
        proc.run((gcloud, "auth", "login", "--activate", "--update-adc"))

    # Check again, and if something's still wrong then exit.
    proc.run((gcloud, "config", "config-helper"), exit=True)


def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]

    # configure versions for tools in devenv/config.ini
    cfg = config.get_repo(reporoot)

    gcloud.install(
        cfg["gcloud"]["version"],
        cfg["gcloud"][SYSTEM_MACHINE],
        cfg["gcloud"][f"{SYSTEM_MACHINE}_sha256"],
        reporoot,
    )

    ensure_gcloud_authed(f"{reporoot}/.devenv/bin/gcloud")

    venv_dir, python_version, requirements, editable_paths, bins = venv.get(
        reporoot, "default"
    )
    url, sha256 = config.get_python(reporoot, python_version)
    print(f"ensuring venv at {venv_dir}...")
    venv.ensure(venv_dir, python_version, url, sha256)

    print(f"syncing with {requirements}...")
    venv.sync(reporoot, venv_dir, requirements, editable_paths, bins)

    return 0
