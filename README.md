## devenv

managing dev environments since '24

`devenv` is an extensible execution framework and library for authoring
a simple set of high level commands - bootstrap, sync, doctor, nuke - that
manage a repository's dev environment.


## install

Download [this](https://raw.githubusercontent.com/getsentry/devtools/main/install-devenv.sh) and run it:

```
bash install-tools.sh
```

## technical overview

devtools itself lives in `~/.local/share/sentry-devtools`. Inside:
- `bin` contains devtools itself and `direnv`
  - this is the only PATH entry needed for devenv
- a private python and virtualenv used exclusively by `devenv`

As much as possible, a repo's dev environment is self-contained within `[reporoot]/.devenv`.

We're relying on `direnv` (which bootstrap will install, globally) to add `[reporoot]/.devenv/bin` to PATH.
Therefore a minimum viable `[reporoot]/.envrc` might look like:

```bash
if [ -f "${PWD}/.env" ]; then
    dotenv
fi

PATH_add "${HOME}/.local/share/sentry-devenv/bin"

if ! command -v devtools >/dev/null; then
    echo "install devenv: https://github.com/getsentry/devenv#install"
    return 1
fi

PATH_add "${PWD}/.devenv/bin"
```

### configuration

global configuration is at `~/.config/sentry-devenv/config.ini`.

repository configuration is at `[reporoot]/devenv/config.ini`.


## develop

We use `tox`. The easiest way to run devenv locally is just using the tox venv's executable:

```
~/code/sentry $  ~/code/devenv/.tox/py311/bin/devenv sync
```
