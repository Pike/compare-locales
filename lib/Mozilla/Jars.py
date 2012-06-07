# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from zipfile import ZipFile
from difflib import SequenceMatcher
import os.path
import re

from Paths import File
import CompareLocales

class JarEntry(File):
  def __init__(self, zf, file, fakefile):
    File.__init__(self, None, fakefile)
    self.realfile = file
    self.zipfile = zf
  def __str__(self):
    return self.zipfile.filename + '!' + self.realfile
  def getContents(self):
    return self.zipfile.read(self.realfile)

class EnumerateJar(object):
  def __init__(self, basepath):
    basepath = os.path.abspath(basepath)
    if not basepath.endswith('.jar'):
      raise RuntimeError("Only jar files supported")
    self.basepath = basepath
    # best guess we have on locale code
    self.locale = os.path.split(basepath)[1].replace('.jar','')
    self.zf = ZipFile(basepath, 'r')
  def cloneFile(self, other):
    return JarEntry(self.zf, other.realfile, other.file)
  def __iter__(self):
    # get all entries, drop those ending with '/', those are dirs.
    files = [f for f in self.zf.namelist() if not f.endswith('/')]
    files.sort()
    # unfortunately, we have to fake file paths of the form
    # locale/AB-CD/
    # for comparison.
    # For real, the corresponding manifest would tell us. Whichever.
    localesub = re.compile('^locale/' + self.locale)
    for f in files:
      yield JarEntry(self.zf, f, localesub.sub('locale/@AB_CD@', f))

def compareJars(ref, l10n):
  o  = CompareLocales.Observer()
  cc = CompareLocales.ContentComparer(o)
  dc = CompareLocales.DirectoryCompare(EnumerateJar(ref))
  dc.setWatcher(cc)
  dc.compareWith(EnumerateJar(l10n))
  return o
