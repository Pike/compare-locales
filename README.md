[![Build Status](https://travis-ci.org/Pike/compare-locales.svg?branch=master)](https://travis-ci.org/Pike/compare-locales)
# compare-locales
python library to lint mozilla localizations

Finds
* missing strings
* obsolete strings
* errors on runtime errors without false positives
* warns on possible runtime errors

It also includes `l10n-merge` functionality, which pads localization with missing English strings,
and replaces entities with errors with English.
