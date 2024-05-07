from __future__ import annotations

import configparser
import json
import logging
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple
from collections.abc import Sequence
from typing import Dict

from devtools.lib import proc
from devtools.lib.proc import CommandError
from devtools.lib.repository import Repository


logger = logging.getLogger(__name__)

Identity = namedtuple("Identity", ["account", "token", "expiration"])


def get_identity() -> Identity:
    """Pulls the current identity from gcloud"""
    parser = configparser.ConfigParser()
    try:
        _, stdout, stderr = proc.run(
            (
                "gcloud",
                "config",
                "config-helper",
                "--format",
                "config(configuration.properties.core.account,credential.access_token)",
            ),
            stderr=sys.stderr,
        )
        parser.read_string(stdout)
    except CommandError:
        raise SystemExit(
            "An error occurred while get information from gcloud. Do you need to log in with `gcloud auth login`?"
        )

    account = parser.get("configuration.properties.core", "account")
    token = parser.get("credential", "access_token")

    return Identity(account, token, None)


def create_token(
    current: Identity,
    target: str,
    scopes: Sequence[str] = (
        "profile",
        "email",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/cloud-platform",
    ),
    lifetime: int = 3600,
) -> Identity:
    """
    Creates a GCP access token
    """
    if not scopes:
        raise SystemExit("GCP requires at least one scope")
    if not target.endswith("iam.gserviceaccount.com"):
        raise SystemExit("GCP sudo only works for service accounts")
    iam_api = "https://iamcredentials.googleapis.com/v1"

    data = {"lifetime": f"{lifetime}s", "scope": scopes}

    data = json.dumps(data).encode("utf-8")

    url = "{}/projects/-/serviceAccounts/{}:generateAccessToken".format(
        iam_api, urllib.parse.quote_plus(target)
    )
    req = urllib.request.Request(url, data=data, method="POST")

    logger.debug("Calling GCP with %s", data)
    req.add_header("Authorization", "Bearer " + current.token)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")

    output = {}
    try:
        with urllib.request.urlopen(req) as f:
            response = f.read()
            logger.debug("Response from GCP API: %s", response)
            output.update(json.loads(response))
    except urllib.error.HTTPError as e:
        print(e.read())
        raise e

    return Identity(target, output["accessToken"], output["expireTime"])


def sudo(
    target: str,
    scopes: Sequence[str] = (
        "profile",
        "email",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/cloud-platform",
    ),
    lifetime: int = 3600,
) -> Identity:
    identity = get_identity()
    new_token = create_token(identity, target, scopes, lifetime)

    return new_token


def sudo_alias(repo: Repository, target: str) -> Identity:
    """
    Ported from Tacos-GHA

    Generates the tokens necessary to masquerade as another account on GCP
    """
    config = repo.config()
    section = f"gcpsudo.{target}"
    if not config.has_section(section):
        raise SystemExit(
            f"Account {target} not found in {repo.config_path}/config.ini"
        )

    target_account = config.get(section, "account")
    target_scopes = config.get(section, "scopes").split()

    return sudo(target_account, target_scopes)


def to_env(identity: Identity) -> Dict[str, str]:
    return {
        "CLOUDSDK_CORE_ACCOUNT": identity.account,
        "GOOGLE_OAUTH_ACCESS_TOKEN": identity.token,
        "CLOUDSDK_AUTH_ACCESS_TOKEN": identity.token,
    }
