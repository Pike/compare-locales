# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
from __future__ import unicode_literals

from .dtd import DTDChecker
from .fluent import FluentChecker
from .properties import PropertiesChecker


def getChecker(file, extra_tests=None):
    if PropertiesChecker.use(file):
        return PropertiesChecker(extra_tests, locale=file.locale)
    if DTDChecker.use(file):
        return DTDChecker(extra_tests, locale=file.locale)
    if FluentChecker.use(file):
        return FluentChecker(extra_tests, locale=file.locale)
    return None
