"""Python library and scripts to assist in localizing Mozilla projects

This library and the command-line script provide a way to check
a given localization for completeness, errors and warnings. It also supports
"l10n merge", which produces sanitized versions of localized files to be
included in builds and deployments. For more information see
https://developer.mozilla.org/en/docs/Compare-locales
"""

from __future__ import absolute_import
DOCSTRINGS = __doc__.split("\n")

from setuptools import setup, find_packages

import sys
import os.path
sys.path.insert(0, os.path.dirname(__file__))

from compare_locales import version

CLASSIFIERS = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Topic :: Software Development :: Libraries :: Python Modules
Topic :: Software Development :: Localization
Topic :: Software Development :: Testing\
"""

setup(name="compare-locales",
      version=version,
      author="Axel Hecht",
      author_email="axel@mozilla.com",
      description=DOCSTRINGS[0],
      long_description="\n".join(DOCSTRINGS[2:]),
      license="MPL 2.0",
      classifiers=CLASSIFIERS.split("\n"),
      platforms=["any"],
      python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4',
      entry_points={'console_scripts': [
          'compare-locales = compare_locales.commands:CompareLocales.call']},
      packages=find_packages(),
      package_data={
          'compare_locales.tests': ['data/*.properties', 'data/*.dtd']
      },
      install_requires=[
          'fluent >=0.7.0, <0.8',
          'pytoml',
          'six',
      ],
      test_suite='compare_locales.tests')
