# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'Commands exposed to commandlines'

import logging
from argparse import ArgumentParser
import os

from compare_locales import version
from compare_locales.paths import EnumerateApp, TOMLParser
from compare_locales.compare import compareProjects, Observer


class BaseCommand(object):
    """Base class for compare-locales commands.
    This handles command line parsing, and general sugar for setuptools
    entry_points.
    """

    def __init__(self):
        self.parser = None

    def get_parser(self):
        """Get an ArgumentParser, with class docstring as description.
        """
        parser = ArgumentParser(description=self.__doc__)
        parser.add_argument('--version', action='version',
                            version='%(prog)s ' + version)
        parser.add_argument('-v', '--verbose', action='count', dest='v',
                            default=0, help='Make more noise')
        parser.add_argument('-q', '--quiet', action='count', dest='q',
                            default=0, help='Make less noise')
        parser.add_argument('-m', '--merge',
                            help='''Use this directory to stage merged files,
use {ab_CD} to specify a different directory for each locale''')
        return parser

    def add_data_argument(self, parser):
        parser.add_argument('--data', choices=['text', 'exhibit', 'json'],
                            default='text',
                            help='''Choose data and format (one of text,
exhibit, json); text: (default) Show which files miss which strings, together
with warnings and errors. Also prints a summary; json: Serialize the internal
tree, useful for tools. Also always succeeds; exhibit: Serialize the summary
data in a json useful for Exhibit
''')

    @classmethod
    def call(cls):
        """Entry_point for setuptools.
        The actual command handling is done in the handle() method of the
        subclasses.
        """
        cmd = cls()
        cmd.handle_()

    def handle_(self):
        """The instance part of the classmethod call."""
        self.parser = self.get_parser()
        args = self.parser.parse_args()
        # log as verbose or quiet as we want, warn by default
        logging.basicConfig()
        logging.getLogger().setLevel(logging.WARNING -
                                     (args.v - args.q) * 10)
        observers = self.handle(args)
        for observer in observers:
            print observer.serialize(type=args.data).encode('utf-8', 'replace')

    def handle(self, args):
        """Subclasses need to implement this method for the actual
        command handling.
        """
        raise NotImplementedError


class CompareLocales(BaseCommand):
    """Check the localization status of gecko applications.
The first arguments are paths to the l10n.ini or toml files for the
applications, followed by the base directory of the localization repositories.
Then you pass in the list of locale codes you want to compare. If there are
not locales given, the list of locales will be taken from the l10n.toml file
or the all-locales file referenced by the application\'s l10n.ini."""

    def get_parser(self):
        parser = super(CompareLocales, self).get_parser()
        parser.add_argument('config', metavar='l10n.toml', nargs='+',
                            help='TOML or INI file for the project')
        parser.add_argument('l10n_base_dir', metavar='l10n-base-dir',
                            help='Parent directory of localizations')
        parser.add_argument('locales', nargs='*', metavar='locale-code',
                            help='Locale code and top-level directory of '
                                 'each localization')
        parser.add_argument('-D', action='append', metavar='var=value',
                            default=[],
                            help='Overwrite variables in TOML files')
        parser.add_argument('--unified', action="store_true",
                            help="Show output for all projects unified")
        parser.add_argument('--full', action="store_true",
                            help="Compare projects that are disabled")
        parser.add_argument('--clobber-merge', action="store_true",
                            default=False, dest='clobber',
                            help="""WARNING: DATALOSS.
Use this option with care. If specified, the merge directory will
be clobbered for each module. That means, the subdirectory will
be completely removed, any files that were there are lost.
Be careful to specify the right merge directory when using this option.""")
        self.add_data_argument(parser)
        return parser

    def handle(self, args):
        # using nargs multiple times in argparser totally screws things
        # up, repair that.
        # First files are configs, then the base dir, everything else is
        # locales
        all_args = args.config + [args.l10n_base_dir] + args.locales
        del args.config[:]
        del args.locales[:]
        while all_args and not os.path.isdir(all_args[0]):
            args.config.append(all_args.pop(0))
        if not args.config:
            self.parser.error('no configuration file given')
        for cf in args.config:
            if not os.path.isfile(cf):
                self.parser.error('config file %s not found' % cf)
        if not all_args:
            self.parser.error('l10n-base-dir not found')
        args.l10n_base_dir = all_args.pop(0)
        args.locales.extend(all_args)
        # when we compare disabled projects, we set our locales
        # on all subconfigs, so deep is True.
        locales_deep = args.full
        configs = []
        config_env = {}
        for define in args.D:
            var, _, value = define.partition('=')
            config_env[var] = value
        for config_path in args.config:
            if config_path.endswith('.toml'):
                config = TOMLParser.parse(config_path, env=config_env)
                config.add_global_environment(l10n_base=args.l10n_base_dir)
                if args.locales:
                    config.set_locales(args.locales, deep=locales_deep)
                configs.append(config)
            else:
                app = EnumerateApp(
                    config_path, args.l10n_base_dir, args.locales)
                configs.append(app.asConfig())
        try:
            unified_observer = None
            if args.unified:
                unified_observer = Observer()
            observers = compareProjects(
                configs,
                stat_observer=unified_observer,
                merge_stage=args.merge, clobber_merge=args.clobber)
        except (OSError, IOError), exc:
            print "FAIL: " + str(exc)
            self.parser.exit(2)
        if args.unified:
            return [unified_observer]
        return observers
