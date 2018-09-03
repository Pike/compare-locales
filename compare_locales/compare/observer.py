# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'Mozilla l10n compare locales tool'

from __future__ import absolute_import
from __future__ import print_function
from collections import defaultdict
import six

from json import dumps

from .utils import Tree


class Observer(object):

    def __init__(self, quiet=0, filter=None, file_stats=False):
        '''Create Observer
        For quiet=1, skip per-entity missing and obsolete strings,
        for quiet=2, skip missing and obsolete files. For quiet=3,
        skip warnings and errors.
        '''
        self.summary = defaultdict(lambda: defaultdict(int))
        self.details = Tree(list)
        self.quiet = quiet
        self.filter = filter
        self.file_stats = None
        if file_stats:
            self.file_stats = defaultdict(lambda: defaultdict(dict))

    # support pickling
    def __getstate__(self):
        state = dict(summary=self._dictify(self.summary), details=self.details)
        if self.file_stats is not None:
            state['file_stats'] = self._dictify(self.file_stats)
        return state

    def __setstate__(self, state):
        self.summary = defaultdict(lambda: defaultdict(int))
        if 'summary' in state:
            for loc, stats in six.iteritems(state['summary']):
                self.summary[loc].update(stats)
        self.file_stats = None
        if 'file_stats' in state:
            self.file_stats = defaultdict(lambda: defaultdict(dict))
            for k, d in six.iteritems(state['file_stats']):
                self.file_stats[k].update(d)
        self.details = state['details']
        self.filter = None

    def _dictify(self, d):
        plaindict = {}
        for k, v in six.iteritems(d):
            plaindict[k] = dict(v)
        return plaindict

    def toJSON(self):
        # Don't export file stats, even if we collected them.
        # Those are not part of the data we use toJSON for.
        return {
            'summary': self._dictify(self.summary),
            'details': self.details.toJSON()
        }

    def updateStats(self, file, stats):
        # in multi-project scenarios, this file might not be ours,
        # check that.
        # Pass in a dummy entity key '' to avoid getting in to
        # generic file filters. If we have stats for those,
        # we want to aggregate the counts
        if (self.filter is not None and
                self.filter(file, entity='') == 'ignore'):
            return
        for category, value in six.iteritems(stats):
            self.summary[file.locale][category] += value
        if self.file_stats is None:
            return
        if 'missingInFiles' in stats:
            # keep track of how many strings are in a missing file
            # we got the {'missingFile': 'error'} from the notify pass
            self.details[file].append({'count': stats['missingInFiles']})
            # missingInFiles should just be "missing" in file stats
            self.file_stats[file.locale][file.localpath]['missing'] = \
                stats['missingInFiles']
            return  # there are no other stats for missing files
        self.file_stats[file.locale][file.localpath].update(stats)

    def notify(self, category, file, data):
        rv = 'error'
        if category in ['missingFile', 'obsoleteFile']:
            if self.filter is not None:
                rv = self.filter(file)
            if rv != "ignore" and self.quiet < 2:
                self.details[file].append({category: rv})
            return rv
        if category in ['missingEntity', 'obsoleteEntity']:
            if self.filter is not None:
                rv = self.filter(file, data)
            if rv == "ignore":
                return rv
            if self.quiet < 1:
                self.details[file].append({category: data})
            return rv
        if category in ('error', 'warning') and self.quiet < 3:
            self.details[file].append({category: data})
            self.summary[file.locale][category + 's'] += 1
        return rv

    def toExhibit(self):
        items = []
        for locale in sorted(six.iterkeys(self.summary)):
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
                         for k in ('changed', 'unchanged', 'report', 'missing',
                                   'missingInFiles')
                         if k in summary])
            total_w = sum([summary[k]
                           for k in ('changed_w', 'unchanged_w', 'missing_w')
                           if k in summary])
            rate = (('changed' in summary and summary['changed'] * 100) or
                    0) / total
            item.update((k, summary.get(k, 0))
                        for k in ('changed', 'unchanged'))
            item.update((k, summary[k])
                        for k in ('report', 'errors', 'warnings')
                        if k in summary)
            item['missing'] = summary.get('missing', 0) + \
                summary.get('missingInFiles', 0)
            item['completion'] = rate
            item['total'] = total
            item.update((k, summary.get(k, 0))
                        for k in ('changed_w', 'unchanged_w', 'missing_w'))
            item['total_w'] = total_w
            result = 'success'
            if item.get('warnings', 0):
                result = 'warning'
            if item.get('errors', 0) or item.get('missing', 0):
                result = 'failure'
            item['result'] = result
            items.append(item)
        data = {
            "properties": dict.fromkeys(
                ("completion", "errors", "warnings", "missing", "report",
                 "missing_w", "changed_w", "unchanged_w",
                 "unchanged", "changed", "obsolete"),
                {"valueType": "number"}),
            "types": {
                "Build": {"pluralLabel": "Builds"}
            }}
        data['items'] = items
        return dumps(data, indent=2)

    def serialize(self, type="text"):
        if type == "exhibit":
            return self.toExhibit()
        if type == "json":
            return dumps(self.toJSON())

        def tostr(t):
            if t[1] == 'key':
                return '  ' * t[0] + '/'.join(t[2])
            o = []
            indent = '  ' * (t[0] + 1)
            for item in t[2]:
                if 'error' in item:
                    o += [indent + 'ERROR: ' + item['error']]
                elif 'warning' in item:
                    o += [indent + 'WARNING: ' + item['warning']]
                elif 'missingEntity' in item:
                    o += [indent + '+' + item['missingEntity']]
                elif 'obsoleteEntity' in item:
                    o += [indent + '-' + item['obsoleteEntity']]
                elif 'missingFile' in item:
                    o.append(indent + '// add and localize this file')
                elif 'obsoleteFile' in item:
                    o.append(indent + '// remove this file')
            return '\n'.join(o)

        out = []
        for locale, summary in sorted(six.iteritems(self.summary)):
            if locale is not None:
                out.append(locale + ':')
            out += [
                k + ': ' + str(v) for k, v in sorted(six.iteritems(summary))]
            total = sum([summary[k]
                         for k in ['changed', 'unchanged', 'report', 'missing',
                                   'missingInFiles']
                         if k in summary])
            rate = 0
            if total:
                rate = (('changed' in summary and summary['changed'] * 100) or
                        0) / total
            out.append('%d%% of entries changed' % rate)
        return '\n'.join([tostr(c) for c in self.details.getContent()] + out)

    def __str__(self):
        return 'observer'
