# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n test automation.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation
# Portions created by the Initial Developer are Copyright (C) 2006
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#	Axel Hecht <l10n@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import os.path
import os
from ConfigParser import ConfigParser, NoSectionError, NoOptionError
from urlparse import urlparse, urljoin
from urllib import pathname2url, url2pathname
from urllib2 import urlopen
from Mozilla.CompareLocales import defaultdict

class L10nConfigParser(object):
  '''Helper class to gather application information from ini files.

  This class is working on synchronous open to read files or web data.
  Subclass this and overwrite loadConfigs and addChild if you need async.
  '''
  def __init__(self, inipath, **kwargs):
    if os.path.isabs(inipath):
      self.inipath = 'file:%s' % pathname2url(inipath)
    else:
      pwdurl = 'file:%s/' % pathname2url(os.getcwd())
      self.inipath = urljoin(pwdurl, inipath)
    self.children = []
    self.dirs = []
    self.defaults = kwargs

  def loadConfigs(self):
    self.onLoadConfig(urlopen(self.inipath))

  def onLoadConfig(self, inifile):
    cp = ConfigParser(self.defaults)
    cp.readfp(inifile)
    try:
      depth = cp.get('general', 'depth')
    except:
      depth = '.'
    self.baseurl = urljoin(self.inipath, depth)
    try:
      for title, path in cp.items('includes'):
        # skip default items
        if title in self.defaults:
          continue
        # add child config parser
        self.addChild(title, path, cp)
    except NoSectionError:
      pass
    try:
      self.dirs.extend(cp.get('compare', 'dirs').split())
    except (NoOptionError, NoSectionError):
      pass
    try:
      self.all_path = cp.get('general', 'all')
      self.all_url = urljoin(self.baseurl, self.all_path)
    except (NoOptionError, NoSectionError):
      self.all_path = None
      self.all_url = None

  def addChild(self, title, path, orig_cp):
    cp = L10nConfigParser(urljoin(self.baseurl, path), **self.defaults)
    cp.loadConfigs()
    self.children.append(cp)

  def dirsIter(self):
    url = urlparse(self.baseurl)
    basepath = None
    if url[0] == 'file':
      basepath = url2pathname(url[2])
    for dir in self.dirs:
      yield (dir, basepath)
    

  def directories(self):
    for t in self.dirsIter():
      yield t
    for child in self.children:
      for t in child.directories():
        yield t

  def allLocales(self):
    return urlopen(self.all_url).read().splitlines()


class SourceTreeConfigParser(L10nConfigParser):
  '''Subclassing L10nConfigParser to work with just the repos
  checked out next to each other instead of intermingled like
  we do for real builds.
  '''

  def __init__(self, inipath, basepath, initial_module=None):
    '''Add additional arguments basepath and initial_module.

    basepath is used to resolve local paths, initial_momdule 
    is used to support single module setups like fennec.
    The module in that case would be 'mobile' while the local
    paths are just 'locales/en-US/...'
    '''
    L10nConfigParser.__init__(self, inipath)
    self.basepath = basepath
    self.initial_module = initial_module

  def addChild(self, title, path, orig_cp):
    # check if there's a section with details for this include
    # we might have to check a different repo, or even VCS
    # for example, projects like "mail" indicate in
    # an "include_" section where to find the l10n.ini for "toolkit"
    details = 'include_' + title
    if orig_cp.has_section(details):
      branch = orig_cp.get(details, 'mozilla')
      inipath = orig_cp.get(details, 'l10n.ini')
      path = self.basepath + '/' + branch + '/' + inipath
    else:
      path = urljoin(self.baseurl, path)
    cp = SourceTreeConfigParser(path, self.basepath, **self.defaults)
    cp.loadConfigs()
    self.children.append(cp)

  def dirsIter(self):
    if self.initial_module is not None:
      assert len(self.dirs) == 1
      yield self.dirs[0], os.path.join(os.path.abspath(self.basepath),
                                       self.initial_module)
    else:
      for dir, basepath in L10nConfigParser.dirsIter(self):
        yield dir, basepath


class File(object):
  def __init__(self, fullpath, file, module = None, locale = None):
    self.fullpath = fullpath
    self.file = file
    self.module = module
    self.locale = locale
    pass
  def getContents(self):
    # open with universal line ending support and read
    return open(self.fullpath, 'rU').read()
  def __hash__(self):
    f = self.file
    if self.module:
      f = self.module + '/' + f
    return hash(f)
  def __str__(self):
    return self.fullpath
  def __cmp__(self, other):
    if not isinstance(other, File):
      raise NotImplementedError
    rv = cmp(self.module, other.module)
    if rv != 0:
      return rv
    return cmp(self.file, other.file)

class EnumerateDir(object):
  ignore_dirs = ['CVS', '.svn', '.hg']
  def __init__(self, basepath, module = None, locale = None):
    self.basepath = basepath
    self.module = module
    self.locale = locale
    pass
  def cloneFile(self, other):
    '''
    Return a File object that this enumerator would return, if it had it.
    '''
    return File(os.path.join(self.basepath, other.file), other.file,
                self.module, self.locale)
  def __iter__(self):
    # our local dirs are given as a tuple of path segments, starting off
    # with an empty sequence for the basepath.
    dirs = [()]
    while dirs:
      dir = dirs.pop(0)
      fulldir = os.path.join(self.basepath, *dir)
      try:
        entries = os.listdir(fulldir)
      except OSError:
        # we probably just started off in a non-existing dir, ignore
        continue
      entries.sort()
      for entry in entries:
        leaf = os.path.join(fulldir, entry)
        if os.path.isdir(leaf):
          if entry not in self.ignore_dirs:
            dirs.append(dir + (entry,))
          continue
        yield File(leaf, '/'.join(dir + (entry,)),
                   self.module, self.locale)

class LocalesWrap(object):
  def __init__(self, base, module, locales):
    self.base = base
    self.module = module
    self.locales = locales
  def __iter__(self):
    for locale in self.locales:
      path = os.path.join(self.base, locale, self.module)
      yield (locale, EnumerateDir(path, self.module, locale))

class EnumerateApp(object):
  reference =  'en-US'
  def __init__(self, inipath, l10nbase, locales = None):
    self.setupConfigParser(inipath)
    self.modules = defaultdict(dict)
    self.l10nbase = os.path.abspath(l10nbase)
    self.filters = []
    drive, tail = os.path.splitdrive(inipath)
    filterpath = drive + url2pathname(urlparse(urljoin(tail,'filter.py'))[2])
    self.addFilterFrom(filterpath)
    self.locales = locales or self.config.allLocales()
    self.locales.sort()
    pass
  def setupConfigParser(self, inipath):
    self.config = L10nConfigParser(inipath)
    self.config.loadConfigs()
  def addFilterFrom(self, filterpath):
    if not os.path.exists(filterpath):
      return
    l = {}
    execfile(filterpath, {}, l)
    if 'test' not in l or not callable(l['test']):
      # XXX error handling?
      return
    self.filters.append(l['test'])
  def filter(self, l10n_file, entity = None):
    for f in self.filters:
      try: 
        if not f(l10n_file.module, l10n_file.file, entity):
          return False
      except:
        # XXX error handling
        continue
    return True
  def __iter__(self):
    '''
    Iterate over all modules, return en-US directory enumerator, and an
    iterator over all locales in each iteration. Per locale, the locale
    code and an directory enumerator will be given.
    '''
    dirmap = dict(self.config.directories())
    mods = dirmap.keys()
    mods.sort()
    for mod in mods:
      if self.reference == 'en-US':
        base = os.path.join(dirmap[mod], mod, 'locales', 'en-US')
      else:
        base = os.path.join(self.l10nbase, self.reference, mod)
      yield (mod, EnumerateDir(base, mod, self.reference),
             LocalesWrap(self.l10nbase, mod, self.locales))


class EnumerateSourceTreeApp(EnumerateApp):
  '''Subclass EnumerateApp to work on side-by-side checked out
  repos, and to no pay attention to how the source would actually
  be checked out for building.

  It's supporting applications like Fennec, too, which have
  'locales/en-US/...' in their root dir, but claim to be 'mobile'.
  '''

  def __init__(self, inipath, basepath, l10nbase, locales=None,
               initial_module=None):
    self.initial_module = initial_module
    self.basepath = basepath
    EnumerateApp.__init__(self, inipath, l10nbase, locales)

  def setupConfigParser(self, inipath):
    self.config = SourceTreeConfigParser(inipath, self.basepath,
                                         self.initial_module)
    self.config.loadConfigs()

  def __iter__(self):
    redir = None
    if self.initial_module is not None:
      # We're something like fennec. If we see the module of the single
      # fake module, redirect it to not have the mod in the path
      redir = self.config.dirs[0]
      target = os.path.join(os.path.abspath(self.basepath),
                            self.initial_module,
                            'locales', 'en-US')
    for mod, ref, l10n in EnumerateApp.__iter__(self):
      if mod != redir:
        yield mod, ref, l10n
      else:
        yield mod, EnumerateDir(target, mod, self.reference), l10n


def get_base_path(mod, loc):
  'statics for path patterns and conversion'
  __l10n = 'l10n/%(loc)s/%(mod)s'
  __en_US = 'mozilla/%(mod)s/locales/en-US'
  if loc == 'en-US':
    return __en_US % {'mod': mod}
  return __l10n % {'mod': mod, 'loc': loc}

def get_path(mod, loc, leaf):
  return get_base_path(mod, loc) + '/' + leaf

