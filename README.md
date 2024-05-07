## devtools

## install

Download [this](https://raw.githubusercontent.com/getsentry/sentry-devtools/main/install-devtools.sh) and run it:

```
bash install-tools.sh
```

## technical overview

devtools itself lives in `~/.local/share/sentry-devtools`. Inside:
- `bin` contains devtools itself and `direnv`
  - this is the only PATH entry needed for devtools

The purpose of devtools is to ship commonly used patterns to developers in a way which will allow 
them to automate or script actions in a consistent manner.
