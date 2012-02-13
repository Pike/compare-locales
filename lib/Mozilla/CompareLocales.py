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

'Mozilla l10n compare locales tool'

import codecs
import os
import os.path
import shutil
import re
import logging
from difflib import SequenceMatcher
try:
  from collections import defaultdict
except ImportError:
  class defaultdict(dict):
    def __init__(self, defaultclass):
      dict.__init__(self)
      self.__defaultclass = defaultclass
    def __getitem__(self, k):
      if not dict.__contains__(self, k):
        self[k] = self.__defaultclass()
      return dict.__getitem__(self, k)
# backwards compat hack for any(), new in python 2.5
try:
  any([True])
except NameError:
  def any(sequence):
    for item in sequence:
      if item:
        return True
    return False

try:
  from json import dumps
except:
  from simplejson import dumps


import Parser
import Paths
import Checks

class Tree(object):
  def __init__(self, valuetype):
    self.branches = dict()
    self.valuetype = valuetype
    self.value = None
  def __getitem__(self, leaf):
    parts = []
    if isinstance(leaf, Paths.File):
      parts = [p for p in [leaf.locale, leaf.module] if p] + \
          leaf.file.split('/')
    else:
      parts = leaf.split('/')
    return self.__get(parts)
  def __get(self, parts):
    common = None
    old = None
    new = tuple(parts)
    t = self
    for k, v in self.branches.iteritems():
      for i, part in enumerate(zip(k, parts)):
        if part[0] != part[1]:
          i -= 1
          break
      if i < 0:
        continue
      i += 1
      common = tuple(k[:i])
      old = tuple(k[i:])
      new = tuple(parts[i:])
      break
    if old:
      self.branches.pop(k)
      t = Tree(self.valuetype)
      t.branches[old] = v
      self.branches[common] = t
    elif common:
      t = self.branches[common]
    if new:
      if common:
        return t.__get(new)
      t2 = t
      t = Tree(self.valuetype)
      t2.branches[new] = t
    if t.value is None:
      t.value = t.valuetype()
    return t.value
  indent = '  '
  def getContent(self, depth = 0):
    '''
    Returns iterator of (depth, flag, key_or_value) tuples.
    If flag is 'value', key_or_value is a value object, otherwise
    (flag is 'key') it's a key string.
    '''
    keys = self.branches.keys()
    keys.sort()
    if self.value is not None:
      yield (depth, 'value', self.value)
    for key in keys:
      yield (depth, 'key', key)
      for child in self.branches[key].getContent(depth + 1):
        yield child
  def toJSON(self):
    '''
    Returns this Tree as a JSON-able tree of hashes.
    Only the values need to take care that they're JSON-able.
    '''
    json = {}
    keys = self.branches.keys()
    keys.sort()
    if self.value is not None:
      json['value'] = self.value
    children = [('/'.join(key), self.branches[key].toJSON())
                    for key in keys]
    if children:
      json['children'] = children
    return json
  def getStrRows(self):
    def tostr(t):
      if t[1] == 'key':
        return self.indent * t[0] + '/'.join(t[2])
      return self.indent * (t[0] + 1) + str(t[2])
    return map(tostr, self.getContent())
  def __str__(self):
    return '\n'.join(self.getStrRows())

class AddRemove(SequenceMatcher):
  def __init__(self):
    SequenceMatcher.__init__(self, None, None, None)
  def set_left(self, left):
    if not isinstance(left, list):
      left = [l for l in left]
    self.set_seq1(left)
  def set_right(self, right):
    if not isinstance(right, list):
      right = [l for l in right]
    self.set_seq2(right)
  def __iter__(self):
    for tag, i1, i2, j1, j2 in self.get_opcodes():
      if tag == 'equal':
        for pair in zip(self.a[i1:i2], self.b[j1:j2]):
          yield ('equal', pair)
      elif tag == 'delete':
        for item in self.a[i1:i2]:
          yield ('delete', item)
      elif tag == 'insert':
        for item in self.b[j1:j2]:
          yield ('add', item)
      else:
        # tag == 'replace'
        for item in self.a[i1:i2]:
          yield ('delete', item)
        for item in self.b[j1:j2]:
          yield ('add', item)

class DirectoryCompare(SequenceMatcher):
  def __init__(self, reference):
    SequenceMatcher.__init__(self, None, [i for i in reference],
                             [])
    self.watcher = None
  def setWatcher(self, watcher):
    self.watcher = watcher
  def compareWith(self, other):
    if not self.watcher:
      return
    self.set_seq2([i for i in other])
    for tag, i1, i2, j1, j2 in self.get_opcodes():
      if tag == 'equal':
        for i, j in zip(xrange(i1,i2), xrange(j1,j2)):
          self.watcher.compare(self.a[i], self.b[j])
      elif tag == 'delete':
        for i in xrange(i1,i2):
          self.watcher.add(self.a[i], other.cloneFile(self.a[i]))
      elif tag == 'insert':
        for j in xrange(j1, j2):
          self.watcher.remove(self.b[j])
      else:
        for j in xrange(j1, j2):
          self.watcher.remove(self.b[j])
        for i in xrange(i1,i2):
          self.watcher.add(self.a[i], other.cloneFile(self.a[i]))

class Observer(object):
  stat_cats = ['missing', 'obsolete', 'missingInFiles', 'report',
               'changed', 'unchanged', 'keys']
  def __init__(self):
    class intdict(defaultdict):
      def __init__(self):
        defaultdict.__init__(self, int)
    self.summary = defaultdict(intdict)
    self.details = Tree(dict)
    self.filter = None
  # support pickling
  def __getstate__(self):
    return dict(summary = self.getSummary(), details = self.details)
  def __setstate__(self, state):
    class intdict(defaultdict):
      def __init__(self):
        defaultdict.__init__(self, int)
    self.summary = defaultdict(intdict)
    if 'summary' in state:
      for loc, stats in state['summary'].iteritems():
        self.summary[loc].update(stats)
    self.details = state['details']
    self.filter = None
  def getSummary(self):
    plaindict = {}
    for k, v in self.summary.iteritems():
      plaindict[k] = dict(v)
    return plaindict
  def toJSON(self):
    return dict(summary = self.getSummary(), details = self.details.toJSON())
  def notify(self, category, file, data):
    rv = "error"
    if category in self.stat_cats:
      # these get called post reporting just for stats
      # return "error" to forward them to other observers
      self.summary[file.locale][category] += data
      return "error"
    if category in ['missingFile', 'obsoleteFile']:
      if self.filter is not None:
        rv = self.filter(file)
      if rv != "ignore":
        self.details[file][category] = rv
      return rv
    if category in ['missingEntity', 'obsoleteEntity']:
      if self.filter is not None:
        rv = self.filter(file, data)
      if rv == "ignore":
        return rv
      v = self.details[file]
      try:
        v[category].append(data)
      except KeyError:
        v[category] = [data]
      return rv
    if category == 'error':
      try:
        self.details[file][category].append(data)
      except KeyError:
        self.details[file][category] = [data]
      self.summary[file.locale]['errors'] += 1
    elif category == 'warning':
      try:
        self.details[file][category].append(data)
      except KeyError:
        self.details[file][category] = [data]
      self.summary[file.locale]['warnings'] += 1
    return rv
  def toExhibit(self):
    items = []
    for locale in sorted(self.summary.iterkeys()):
      summary = self.summary[locale]
      if locale is not None:
        item = {'id': 'xxx/' + locale,
                'label': locale,
                'locale': locale}
      else:
        item = {'id': 'xxx',
                'label': 'xxx',
                'locale': 'xxx'}
      item['type'] = 'Build'
      total = sum([summary[k]
                   for k in ('changed','unchanged','report','missing',
                             'missingInFiles')
                   if k in summary])
      rate = (('changed' in summary and summary['changed'] * 100)
              or 0) / total
      item.update((k, summary.get(k, 0))
                  for k in ('changed','unchanged'))
      item.update((k, summary[k]) 
                  for k in ('report','errors','warnings')
                  if k in summary)
      item['missing'] = summary.get('missing', 0) + \
          summary.get('missingInFiles', 0)
      item['completion'] = rate
      item['total'] = total
      result = 'success'
      if item.get('warnings',0):
        result = 'warning'
      if item.get('errors',0) or item.get('missing',0):
        result = 'failure'
      item['result'] = result
      items.append(item)
    data = {"properties": dict.fromkeys(
        ("completion", "errors", "warnings", "missing", "report",
         "unchanged", "changed", "obsolete"),
        {"valueType": "number"}),
              "types": {
        "Build": {"pluralLabel": "Builds"}
        }}
    data['items'] = items
    return dumps(data, indent=2)
  def serialize(self, type="text/plain"):
    if type=="application/json":
      return self.toExhibit()
    def tostr(t):
      if t[1] == 'key':
        return '  ' * t[0] + '/'.join(t[2])
      o = []
      indent = '  ' * (t[0] + 1)
      if 'error' in t[2]:
        o += [indent + 'ERROR: ' + e for e in t[2]['error']]
      if 'warning' in t[2]:
        o += [indent + 'WARNING: ' + e for e in t[2]['warning']]
      if 'missingEntity' in t[2] or 'obsoleteEntity' in t[2]:
        missingEntities = ('missingEntity' in t[2] and t[2]['missingEntity']) \
            or []
        obsoleteEntities = ('obsoleteEntity' in t[2] and
                            t[2]['obsoleteEntity']) or []
        entities = missingEntities + obsoleteEntities
        entities.sort()
        for entity in entities:
          op = '+'
          if entity in obsoleteEntities:
            op = '-'
          o.append(indent + op + entity)
      elif 'missingFile' in t[2]:
        o.append(indent + '// add and localize this file')
      elif 'obsoleteFile' in t[2]:
        o.append(indent + '// remove this file')
      return '\n'.join(o)
    out = []
    for locale, summary in self.summary.iteritems():
      if locale is not None:
        out.append(locale + ':')
      out += [k + ': ' + str(v) for k,v in summary.iteritems()]
      total = sum([summary[k] \
                     for k in ['changed','unchanged','report','missing',
                               'missingInFiles'] \
                     if k in summary])
      rate = (('changed' in summary and summary['changed'] * 100)
              or 0) / total
      out.append('%d%% of entries changed' % rate)
    return '\n'.join(map(tostr, self.details.getContent()) + out)
  def __str__(self):
    return 'observer'

class ContentComparer:
  keyRE = re.compile('[kK]ey')
  nl = re.compile('\n', re.M)
  def __init__(self, filterObserver):
    '''Create a ContentComparer.
    filterObserver is usually a instance of Observer. The return values
    of the notify method are used to control the handling of missing
    entities.
    '''
    self.reference = dict()
    self.filterObserver = filterObserver
    self.observers = []
    self.merge_stage = None
  def add_observer(self, obs):
    '''Add a non-filtering observer.
    Results from the notify calls are ignored.
    '''
    self.observers.append(obs)
  def set_merge_stage(self, merge_stage):
    self.merge_stage = merge_stage
  def merge(self, ref_entities, ref_map, ref_file, l10n_file, missing, skips,
            p):
    outfile = os.path.join(self.merge_stage, l10n_file.module, l10n_file.file)
    outdir = os.path.dirname(outfile)
    if not os.path.isdir(outdir):
      os.makedirs(outdir)
    if not p.canMerge:
      shutil.copyfile(ref_file.fullpath, outfile)
      print "copied reference to " + outfile
      return
    trailing = (['\n'] + 
                [ref_entities[ref_map[key]].all for key in missing] +
                [ref_entities[ref_map[skip.key]].all for skip in skips])
    if skips:
      # we need to skip a few errornous blocks in the input, copy by hand
      f = codecs.open(outfile, 'wb', p.encoding)
      offset = 0
      for skip in skips:
        chunk = skip.span
        f.write(p.contents[offset:chunk[0]])
        offset = chunk[1]
      f.write(p.contents[offset:])
    else:
      shutil.copyfile(l10n_file.fullpath, outfile)
      f = codecs.open(outfile, 'ab', p.encoding)
    print "adding to " + outfile
    def ensureNewline(s):
      if not s.endswith('\n'):
        return s + '\n'
      return s
    f.write(''.join(map(ensureNewline,trailing)))
    f.close()
  def notify(self, category, file, data):
    """Check filterObserver for the found data, and if it's
    not to ignore, notify observers.
    """
    rv = self.filterObserver.notify(category, file, data)
    if rv == 'ignore':
      return rv
    for obs in self.observers:
      # non-filtering observers, ignore results
      obs.notify(category, file, data)
    return rv
  def remove(self, obsolete):
    self.notify('obsoleteFile', obsolete, None)
    pass
  def compare(self, ref_file, l10n):
    try:
      p = Parser.getParser(ref_file.file)
      checks = Checks.getChecks(ref_file)
    except UserWarning:
      # no comparison, XXX report?
      return
    if ref_file not in self.reference:
      # we didn't parse this before
      try:
        p.readContents(ref_file.getContents())
      except Exception, e:
        self.notify('error', ref_file, str(e))
        return
      self.reference[ref_file] = p.parse()
    ref = self.reference[ref_file]
    ref_list = ref[1].keys()
    ref_list.sort()
    try:
      p.readContents(l10n.getContents())
      l10n_entities, l10n_map = p.parse()
    except Exception, e:
      self.notify('error', l10n, str(e))
      return
    lines = []
    def _getLine(offset):
      if not lines:
        lines.append(0)
        for m in self.nl.finditer(p.contents):
          lines.append(m.end())
      _line = 1
      for i in xrange(len(lines), 0, -1):
        if offset >= lines[i-1]:
          return (i, offset - lines[i-1])
      return (1, offset)
    l10n_list = l10n_map.keys()
    l10n_list.sort()
    ar = AddRemove()
    ar.set_left(ref_list)
    ar.set_right(l10n_list)
    report = missing = obsolete = changed = unchanged = keys = 0
    missings = []
    skips = []
    for action, item_or_pair in ar:
      if action == 'delete':
        # missing entity
        _rv = self.notify('missingEntity', l10n, item_or_pair)
        if _rv == "ignore":
          continue
        if _rv == "error":
          # only add to missing entities for l10n-merge on error, not report
          missings.append(item_or_pair)
          missing += 1
        else:
          # just report
          report += 1
      elif action == 'add':
        # obsolete entity or junk
        if isinstance(l10n_entities[l10n_map[item_or_pair]], Parser.Junk):
          junk = l10n_entities[l10n_map[item_or_pair]]
          params = (junk.val,) + junk.span
          self.notify('error', l10n, 'Unparsed content "%s" at %d-%d' % params)
        elif self.notify('obsoleteEntity', l10n, item_or_pair) != 'ignore':
          obsolete += 1
      else:
        # entity found in both ref and l10n, check for changed
        entity = item_or_pair[0]
        refent = ref[0][ref[1][entity]]
        l10nent = l10n_entities[l10n_map[entity]]
        if self.keyRE.search(entity):
          keys += 1
        else:
          if refent.val == l10nent.val:
            self.doUnchanged(l10nent)
            unchanged += 1
          else:
            self.doChanged(ref_file, refent, l10nent)
            changed += 1
          # run checks:
        if checks:
          for tp, pos, msg, cat in checks(refent, l10nent):
            # compute real src position, if first line, col needs adjustment
            _l, _offset = _getLine(l10nent.val_span[0])
            if isinstance(pos, tuple):
              # line, column
              if pos[0] == 1:
                col = pos[1] + _offset
              else:
                col = pos[1]
              _l += pos[0] - 1
            else:
              _l, col = _getLine(l10nent.val_span[0] + pos)
             # skip error entities when merging
            if tp == 'error' and self.merge_stage is not None:
              skips.append(l10nent)
            self.notify(tp, l10n,
                        u"%s at line %d, column %d for %s" %
                        (msg, _l, col, refent.key))
        pass
    if missing:
      self.notify('missing', l10n, missing)
    if self.merge_stage is not None and (missings or skips):
      self.merge(ref[0], ref[1], ref_file, l10n, missings, skips, p)
    if report:
      self.notify('report', l10n, report)
    if obsolete:
      self.notify('obsolete', l10n, obsolete)
    if changed:
      self.notify('changed', l10n, changed)
    if unchanged:
      self.notify('unchanged', l10n, unchanged)
    if keys:
      self.notify('keys', l10n, keys)
    pass
  def add(self, orig, missing):
    if self.notify('missingFile', missing, None) == "ignore":
      # filter said that we don't need this file, don't count it
      return
    f = orig
    try:
      p = Parser.getParser(f.file)
    except UserWarning:
      return
    try:
      p.readContents(f.getContents())
      entities, map = p.parse()
    except Exception, e:
      self.notify('error', f, str(e))
      return
    self.notify('missingInFiles', missing, len(map))
  def doUnchanged(self, entity):
    # overload this if needed
    pass
  def doChanged(self, file, ref_entity, l10n_entity):
    # overload this if needed
    pass

def compareApp(app, otherObserver = None, merge_stage = None, clobber = False):
  '''Compare locales set in app.

  Optional arguments are:
  - otherObserver. A object implementing 
      notify(category, _file, data)
    The return values of that callback are ignored.
  - merge_stage. A directory to be used for staging the output of
    l10n-merge.
  - clobber. Clobber the module subdirectories of the merge dir as we go.
    Use wisely, as it might cause data loss.
  '''
  o  = Observer()
  cc = ContentComparer(o)
  if otherObserver is not None:
    cc.add_observer(otherObserver)
  cc.set_merge_stage(merge_stage)
  o.filter = app.filter
  for module, reference, locales in app:
    if merge_stage is not None and clobber:
      # if clobber and merge is on, remove the stage for the module if it exists
      clobberdir = os.path.join(merge_stage, module)
      if os.path.exists(clobberdir):
        shutil.rmtree(clobberdir)
        print "clobbered " + clobberdir
    dc = DirectoryCompare(reference)
    dc.setWatcher(cc)
    for locale, localization in locales:
      dc.compareWith(localization)
  return o

def compareDirs(reference, locale, otherObserver = None, merge_stage = None):
  '''Compare reference and locale dir.

  Optional arguments are:
  - otherObserver. A object implementing 
      notify(category, _file, data)
    The return values of that callback are ignored.
  '''
  o  = Observer()
  cc = ContentComparer(o)
  if otherObserver is not None:
    cc.add_observer(otherObserver)
  cc.set_merge_stage(merge_stage)
  dc = DirectoryCompare(Paths.EnumerateDir(reference))
  dc.setWatcher(cc)
  dc.compareWith(Paths.EnumerateDir(locale))
  return o
