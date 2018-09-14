# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'Commands exposed to commandlines'

from __future__ import absolute_import
from __future__ import print_function
import logging
from argparse import ArgumentParser
import json
import os
import sys

from compare_locales import mozpath
from compare_locales import version
from compare_locales.paths import EnumerateApp, TOMLParser, ConfigNotFound
from compare_locales.compare import compareProjects


class CompareLocales(object):
    """Check the localization status of gecko applications.
The first arguments are paths to the l10n.ini or toml files for the
applications, followed by the base directory of the localization repositories.
Then you pass in the list of locale codes you want to compare. If there are
not locales given, the list of locales will be taken from the l10n.toml file
or the all-locales file referenced by the application\'s l10n.ini."""

    def __init__(self):
        self.parser = None

    def get_parser(self):
        """Get an ArgumentParser, with class docstring as description.
        """
        parser = ArgumentParser(description=self.__doc__)
        parser.add_argument('--version', action='version',
                            version='%(prog)s ' + version)
        parser.add_argument('-v', '--verbose', action='count',
                            default=0, help='Make more noise')
        parser.add_argument('-q', '--quiet', action='count',
                            default=0, help='''Show less data.
Specified once, doesn't obsolete entities. Specified twice, also drops
missing entities. Specify thrice to warnings and four time to
just show stats''')
        parser.add_argument('--validate', action='store_true',
                            help='Run compare-locales against reference')
        parser.add_argument('-m', '--merge',
                            help='''Use this directory to stage merged files,
use {ab_CD} to specify a different directory for each locale''')
        parser.add_argument('config_paths', metavar='l10n.toml', nargs='+',
                            help='TOML or INI file for the project')
        parser.add_argument('l10n_base_dir', metavar='l10n-base-dir',
                            help='Parent directory of localizations')
        parser.add_argument('locales', nargs='*', metavar='locale-code',
                            help='Locale code and top-level directory of '
                                 'each localization')
        parser.add_argument('-D', action='append', metavar='var=value',
                            default=[], dest='defines',
                            help='Overwrite variables in TOML files')
        parser.add_argument('--full', action="store_true",
                            help="Compare projects that are disabled")
        parser.add_argument('--return-zero', action="store_true",
                            help="Return 0 regardless of l10n status")
        parser.add_argument('--clobber-merge', action="store_true",
                            default=False, dest='clobber',
                            help="""WARNING: DATALOSS.
Use this option with care. If specified, the merge directory will
be clobbered for each module. That means, the subdirectory will
be completely removed, any files that were there are lost.
Be careful to specify the right merge directory when using this option.""")
        parser.add_argument('--json',
                            help='''Serialize to json. Use - to serialize
to stdout and to hide the default text output.
''')
        return parser

    @classmethod
    def call(cls):
        """Entry_point for setuptools.
        The actual command handling is done in the handle() method of the
        subclasses.
        """
        cmd = cls()
        return cmd.handle()

    def handle(self):
        """The instance part of the classmethod call."""
        self.parser = self.get_parser()
        args = self.parser.parse_args()
        # log as verbose or quiet as we want, warn by default
        logging_level = logging.WARNING - (args.verbose - args.quiet) * 10
        logging.basicConfig()
        logging.getLogger().setLevel(logging_level)

        config_paths, l10n_base_dir, locales = self.extract_positionals(args)

        # when we compare disabled projects, we set our locales
        # on all subconfigs, so deep is True.
        locales_deep = args.full
        configs = []
        config_env = {
            'l10n_base': l10n_base_dir
        }
        for define in args.defines:
            var, _, value = define.partition('=')
            config_env[var] = value
        for config_path in config_paths:
            if config_path.endswith('.toml'):
                try:
                    config = TOMLParser().parse(config_path, env=config_env)
                except ConfigNotFound as e:
                    self.parser.exit('config file %s not found' % e.filename)
                if locales:
                    config.set_locales(locales, deep=locales_deep)
                configs.append(config)
            else:
                app = EnumerateApp(
                    config_path, l10n_base_dir, locales)
                configs.append(app.asConfig())
        try:
            observers = compareProjects(
                configs,
                l10n_base_dir,
                quiet=args.quiet,
                merge_stage=args.merge, clobber_merge=args.clobber)
        except (OSError, IOError) as exc:
            print("FAIL: " + str(exc))
            self.parser.exit(2)

        if args.json is None or args.json != '-':
            details = observers.serializeDetails()
            if details:
                print(details)
            if len(configs) > 1:
                if details:
                    print('')
                print("Summaries for")
                for config_path in config_paths:
                    print("  " + config_path)
                print("    and the union of these, counting each string once")
            print(observers.serializeSummaries())
        if args.json is not None:
            data = [observer.toJSON() for observer in observers]
            stdout = args.json == '-'
            indent = 1 if stdout else None
            fh = sys.stdout if stdout else open(args.json, 'w')
            json.dump(data, fh, sort_keys=True, indent=indent)
            if stdout:
                fh.write('\n')
            fh.close()
        rv = 1 if observers.error else 0
        return rv

    def extract_positionals(self, args):
        # using nargs multiple times in argparser totally screws things
        # up, repair that.
        # First files are configs, then the base dir, everything else is
        # locales
        all_args = args.config_paths + [args.l10n_base_dir] + args.locales
        config_paths = []
        # The first directory is our l10n base, split there.
        while all_args and not os.path.isdir(all_args[0]):
            config_paths.append(all_args.pop(0))
        if not config_paths:
            self.parser.error('no configuration file given')
        for cf in config_paths:
            if not os.path.isfile(cf):
                self.parser.error('config file %s not found' % cf)
        if not all_args:
            self.parser.error('l10n-base-dir not found')
        l10n_base_dir = mozpath.abspath(all_args.pop(0))
        if args.validate:
            # signal validation mode by setting locale list to [None]
            locales = [None]
        else:
            locales = all_args

        return config_paths, l10n_base_dir, locales
