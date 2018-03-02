"""Python library and scripts to assist in localizing Mozilla applications

Localization of XUL applications in general and Mozilla applications in
particular are done by a number of different file formats. Independent
of the format, the Mozilla architecture does not provide fallback strings
at runtime. This library and the calling scripts provide a way to check
a given localization for completeness. For more information see
https://developer.mozilla.org/en/docs/Compare-locales
"""

DOCSTRINGS = __doc__.split("\n")

from setuptools import setup

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
      entry_points={'console_scripts': [
          'compare-locales = compare_locales.commands:CompareLocales.call']},
      packages=['compare_locales', 'compare_locales.tests'],
      package_data={
          'compare_locales.tests': ['data/*.properties', 'data/*.dtd']
      },
      install_requires=[
          'fluent >=0.6.4, <0.7',
          'pytoml',
      ],
      test_suite='compare_locales.tests')
