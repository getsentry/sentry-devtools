## devtools

## install

### default - global
Download [this](https://raw.githubusercontent.com/getsentry/sentry-devtools/main/install-devtools.sh) and run it:

```
bash install-devtools.sh
```
### global for edit

```shell
git clone https://github.com/getsentry/sentry-devtools
SNTY_DEVTOOLS_SOURCE=`pwd`/sentry-devtools bash sentry-devtools/install-devtools.sh
```

### local dev -- not global
```shell
git clone https://github.com/getsentry/sentry-devtools
cd sentry-devtools
devenv sync
direnv allow
pip install -e .
```

## upgrade -- default global install

```shell
devtools meta update
```

## technical overview

devtools itself lives in `~/.local/share/sentry-devtools`. Inside:
- `bin` contains devtools itself and `direnv`
  - this is the only PATH entry needed for devtools

The purpose of devtools is to ship commonly used patterns to developers in a way which will allow 
them to automate or script actions in a consistent manner. The code itself isn't intended to be the pinnacle of library 
development, however, the intent is to iterate and extract, or replace, parts of this tool over time as our needs 
change.
