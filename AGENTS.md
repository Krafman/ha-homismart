# Instructions for AI agents and contributors

## Never publish real home data

This project is developed and tested against a real HomiSmart installation.
None of its data may appear in this repository, commit
messages, pull requests, issues or release notes. That includes:

- device, hub and unit IDs (14 hex characters) and internal `deviceId` numbers;
- device names, room and area names, and people's names (rooms and devices are
  often named after family members);
- the account's username, password, tokens, and private hostnames.

Use obviously fake values instead: IDs of the form `TT00000000NNNN` (for
example `01000000000001`, hub `00000000000001`) and names like "Hall light".
When live testing informs a change, describe it in general terms ("one
shutter ignored text values") and never paste live output, logs or
diagnostics. Credentials for live tests live in git-ignored `.env` files only.

`scripts/check_example_data.py` runs in CI and rejects real-looking device
IDs. Names can't be checked automatically, so review every new string yourself
before committing.

## Releases and CI cost

- CI runs on pull requests and on pushes to `main` only. Batch changes and
  push once; don't push work that is known to fail (for example, a pin to a
  version that isn't on PyPI yet).
- Releases are GitHub releases (the Marketplace offers them as updates); the
  tag must equal `version` in `custom_components/homismart/manifest.json`.
  Release the client first when the integration needs a new client version,
  then bump the pin in `manifest.json` and `requirements_test.txt` together.
  Finish testing (including on a real Home Assistant) before releasing.

## Protocol notes

- Control commands (`0006`) must be typed like the official app's device
  object: numbers as numbers (`curtainState`, `lock`, `iconId`, ...) and
  `power` always present. Some devices silently ignore text values.
- Tests use Home Assistant's own `pytest-homeassistant` package (Python 3.14):
  `pip install -r requirements_test.txt && pytest`.
