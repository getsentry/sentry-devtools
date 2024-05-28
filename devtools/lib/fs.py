from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import secrets
import tarfile
import tempfile
import urllib.parse
import urllib.request
from collections.abc import Iterator
from urllib.error import HTTPError

from devtools.constants import home
from devtools.constants import shell
from devtools.lib import text

logger = logging.getLogger(__name__)


def shellrc() -> str:
    if shell == "zsh":
        return f"{home}/.zshrc"
    if shell == "bash":
        return f"{home}/.bashrc"
    if shell == "fish":
        return f"{home}/.config/fish/config.fish"
    raise NotImplementedError(f"unsupported shell: {shell}")


def idempotent_add(filepath: str, text: str, trim: bool = True) -> None:
    text = text.strip()
    if trim:
        new_lines = text.split()
    else:
        new_lines = text.split("\n")

    if not new_lines:
        return

    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write(f"{text}\n")
            return
    with open(filepath, "r+") as f:
        contents = f.read()

        if trim:
            existing_lines = contents.split()
        else:
            existing_lines = contents.split("\n")

        start = new_lines[0]
        if len(existing_lines) >= len(new_lines):
            scan_range = existing_lines[
                : len(existing_lines) - (len(new_lines)) + 1
            ]
        else:
            scan_range = []

        for x, current in enumerate(scan_range):
            if current == start:
                for y, line in enumerate(new_lines):
                    if existing_lines[x + y] != line:
                        break
                else:
                    # Found
                    break
        else:
            # Never found
            if contents and contents[-1] != "\n":
                f.write("\n")
            f.write(f"{text}\n")


def write_file(filepath: str, text: str, mode: int = 0o664) -> None:
    with open(filepath, "w") as f:
        f.write(text)
    os.chmod(filepath, mode)


def ensure_binroot(reporoot: str) -> str:
    binroot = os.path.join(reporoot, ".devenv", "bin")
    os.makedirs(binroot, exist_ok=True)

    idempotent_add(os.path.join(binroot, ".gitignore"), "*")
    return binroot


def ensure_symlink(expected_src: str, dest: str) -> None:
    try:
        src = os.readlink(dest)
        if src != expected_src:
            logger.warning("%s unexpectedly points to %s", dest, src)
            return
    except FileNotFoundError:
        os.symlink(expected_src, dest)
    except OSError as e:
        if e.errno == 22:
            logger.warning("%s exists and isn't a symlink", dest)
            return


@contextlib.contextmanager
def retrieve_temp_file(
    url: str, filename: str = "", sha256: str | None = None
) -> Iterator[str]:
    if not filename:
        parts = urllib.parse.urlparse(url)
        filename = os.path.basename(parts.path)

    target_dir = tempfile.mkdtemp(prefix="devtools")
    filepath = os.path.join(target_dir, filename)

    retrieve_file(url, filepath, sha256)
    try:
        yield filepath
    finally:
        logger.debug("Cleaning up %s", target_dir)
        os.remove(filepath)
        os.rmdir(target_dir)


def checksum(path: str) -> str:
    with open(path, "rb") as f:
        f.seek(0)
        sha = hashlib.sha256()
        buf = f.read(4096)

        while buf:
            sha.update(buf)
            buf = f.read(4096)

        return sha.hexdigest()


def retrieve_file(url: str, path: str, sha256: str | None = None) -> None:
    logger.debug("Retrieving %s to %s", url, path)

    def reporter(block: int, received: int, size: int) -> None:
        logger.debug("Downloading%s", text.decoration_sty("." * block))

    try:
        urllib.request.urlretrieve(url, path, reporthook=reporter)
    except HTTPError as e:
        raise SystemExit(f"Error getting {url}: {e}")

    if sha256:
        other256 = checksum(path)

        if not secrets.compare_digest(other256, sha256):
            raise RuntimeError(
                f"checksum mismatch for {url}:\n"
                f"- got: {other256}\n"
                f"- expected: {sha256}\n"
            )


def atomic_replace(src: str, dest: str) -> None:
    if os.path.dirname(src) != os.path.dirname(dest):
        raise RuntimeError(
            f"cannot atomically move to dest {dest}; it needs to be in the same dir as {src}"
        )
    os.replace(src, dest)


def download(url: str, sha256: str, dest: str = "") -> str:
    """Downloads a file to the cache directory using sha256 as a unique identifier or a target path name"""
    if not dest:
        cache_root = f"{home}/.cache/sentry-devtools"
        dest = f"{cache_root}/{sha256}"

    if os.path.isdir(dest):
        raise SystemExit(f"Destination {dest} is a directory")
    if os.path.exists(dest):
        return dest

    target_dir = os.path.dirname(dest)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    # Make an empty file
    fd, local_tmp = tempfile.mkstemp(suffix=".url", dir=target_dir)
    os.close(fd)
    try:
        retrieve_file(url, local_tmp, sha256=sha256)

        # Swap!
        atomic_replace(local_tmp, dest)

    finally:
        if os.path.exists(local_tmp):
            os.remove(local_tmp)
    return dest


def unpack(path: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tarfile.open(name=path, mode="r:*") as tarf:
        tarf.extractall(into)
