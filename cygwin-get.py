#!/usr/bin/env python
# -*- coding:utf-8 -*-
# <code>
#   <author name="Zealic" email="zealic(at)gmail.com" />
#   <timestamp>2013-07-26</timestamp>
# </code>
"""cygwin-get 0.3 - Manage cygwin installations (Command-line user interface).

Usage:
cygwin-get [-h] [-n] [-s <file>] [-r <file>] [-d <dir>] [-m <url>] [-v <spec>] <packages-list>

=======================================
-h |--help
    Display this help.

-n | --no-download
    Do not download packages.

-s | --setupinfo
    Specify setup file. (Default : $TARGET-DIR/setup.ini, when use "*", will download it from web.)

-r | --response
    Xml packages response file (packages-list).

-d | --target-dir
    Target download directory. (Default : $CYGWIN-GET_HOME/packages).

-m | --mirror
    Mirror site. (Default : http://mirrors.163.com/cygwin)

-v | --version-spec
    Version spec, value can be [test | current | prev]. (Default : test)

packages-list
    Specify package list.


Copyright 2011-2012 by Zealic <zealic#gmail.com>
"""
"""
Changelog:
# v0.3 :
  * Improve options.
  * Multi-thread download support.

# v0.2 :
  * Use xml packages response file.

# v0.1 :
  * Initial version.
"""
__version__ = "0.3"
import os, sys, urllib2

EX_KEY_SIGNAL         = -2
EX_SHOW_HELP          = -1
EX_OK                 = 0
EX_INVALID_ARG        = 1
EX_NO_SETUP_INFO      = 2
EX_VERIFY_FAILED      = 3
EX_UPDATE_SETUP_INFO  = 4
EX_HTTP_ERROR         = 5
EX_INVALID_RESPONSE   = 6

BUFFER_SIZE           = 1024 * 64

option_no_download    = False
option_target_dir     = os.path.join(os.path.dirname(__file__), "packages")
option_mirror         = "http://mirrors.163.com/cygwin"
option_response_file  = None
option_setupinfo      = None
option_version_spec   = "test"
option_requires       = None


def initialize_options():
  import getopt
  global option_no_download, option_target_dir, option_mirror, \
         option_setupinfo, option_response_file, \
         option_version_spec, option_requires
  
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hns:r:d:m:v:", ["help", "no-download", "setupinfo=", "response=", "target-dir=", "mirror=", "version-spec="])
  except getopt.GetoptError:
    usage(EX_INVALID_ARG)
  
  for o, v in opts :
    if o in ("-h", "--help"):
      usage(EX_SHOW_HELP)
    elif o in ("-n", "--no-download"):
      option_no_download = True
    elif o in ("-s", "--setupinfo"):
      option_setupinfo = v
    elif o in ("-r", "--response"):
      option_response_file= v
    elif o in ("-d", "--target-dir"):
      option_target_dir = v
    elif o in ("-m", "--mirror"):
      option_mirror = v
    elif o in ("-v", "--version-spec"):
      option_version_spec = v
  
  if option_response_file == None and len(args) == 0:
    usage(EX_INVALID_ARG)
  
  option_requires = set()
  if option_response_file <> None and os.path.exists(option_response_file):
    option_requires = parse_response_file(option_response_file)
  option_requires = get_requires(args, option_requires)
  
  if option_setupinfo == "*" or option_setupinfo == None:
    setupinfo_file = os.path.join(option_target_dir, "setup.ini")
    if option_setupinfo == "*" or not os.path.exists(setupinfo_file):
      report_info("Downloading setup.ini ...")
      url = get_url("setup.ini")
      download_file(url, setupinfo_file)
    option_setupinfo = setupinfo_file

def usage(exitCode = None):
  report_info(__doc__)
  if exit != None: exit(exitCode)

def get_requires(names, old_requires = set()):
  requires = set(old_requires)
  requires.update(names)
  return requires

def parse_response_file(response_file):
  from xml.etree.ElementTree import ElementTree
  
  try:
    tree = ElementTree()
    root = tree.parse(response_file)
    packages = root.findall('package')
    result = set()
    for p in packages:
      result.add(p.attrib["name"])
    return result
  except Exception as e:
    report_info("Invalid response file '%s', %s" % (response_file, e.message))
    exit(EX_INVALID_RESPONSE)

def get_url(file_path):
  import urlparse
  return urlparse.urlparse(option_mirror + "/" + file_path).geturl()

def download_file(url, file_path):
  dir = os.path.dirname(os.path.abspath(file_path))
  base_name = os.path.basename(url)
  if not os.path.exists(dir):
    os.makedirs(dir)

  re = urllib2.Request(url)
  target_file = file(file_path, 'wb')
  try:
    fd = urllib2.urlopen(re)
    while True:
      rs = fd.read(BUFFER_SIZE)
      if not rs:
        break
      target_file.write(rs)
  except:
    target_file.close()
    os.remove(file_path)
    raise
  finally:
    if not target_file.closed: target_file.close()

def report_info(message):
  sys.stderr.write(str(message) + "\n")


class CygwinRepository(object):
  def __init__(self, config_file, target_dir):
    self.packages = self.__parse_cygwin_config(config_file, target_dir)
  
  def __parse_cygwin_config(self, config_file, target_dir):
    report_info("Parsing setup.ini ...")
    cfg = file(config_file, "r")
    allLines = cfg.readlines()

    allPkg = {}
    currentPkg = {}
    currentSpec = {}
    currentLDesc = None

    for currentLine in allLines:
      currentLine = currentLine.strip()
      if currentLine.startswith("@ "):
        pkgName = str(currentLine[2:])
        specName = "current"
        currentSpec = {"name": specName, "package_name": pkgName}
        currentPkg = CygwinPackage()
        currentPkg.dir = target_dir
        currentPkg.name = pkgName
        currentPkg.categories = set()
        currentPkg.requires = set()
        currentPkg.specs = {specName: currentSpec}
        allPkg[pkgName] = currentPkg
      elif currentLine.startswith("[") and currentLine.endswith("]"):
        name = currentLine[1:-1]
        currentSpec = {"name": name, "package_name": currentPkg.name}
        currentPkg.specs[name] = currentSpec
      elif currentLine.startswith("sdesc: "):
        currentPkg.sdesc = currentLine[8:-1]
      elif currentLine.startswith("ldesc: "):
        if currentLine.endswith('"'):
          currentPkg.ldesc = str(currentLine[8:-1])
        else:
          currentLDesc = str(currentLine[8:])
      elif not currentLDesc is None:
        if currentLine.endswith('"'):
          currentPkg.ldesc = currentLDesc + "\n" + str(currentLine[0:-1])
          currentLDesc = None
        else:
          currentLDesc =currentLDesc + "\n" + currentLine
      elif currentLine.startswith("category: "):
        currentPkg.categories = set(str(currentLine[10:]).split(" "))
      elif currentLine.startswith("requires: "):
        currentPkg.requires = set(str(currentLine[10:]).split(" "))
      elif currentLine.startswith("version: "):
        currentSpec["version"] = str(currentLine[9:])
      elif currentLine.startswith("install: "):
        install_parts = str(currentLine[9:]).split(" ")
        currentSpec["binary"] = {"path" : install_parts[0], "size" : int(install_parts[1]), "hash" : install_parts[2]}
      elif currentLine.startswith("source: "):
        source_parts = str(currentLine[8:]).split(" ")
        currentSpec["source"] = {"path" : source_parts[0], "size" : int(source_parts[1]), "hash" : source_parts[2]}
    return allPkg
  
  def resolve(self, requires):
    result = dict()
    self.__resolve_core(requires, result)
    return result
  
  def __resolve_core(self, requires, result):
    for requireName in requires:
      if requireName.startswith("@"):
        categoryName = str(requireName[1:])
        for k, v in self.packages.iteritems():
          if categoryName in v.categories:
            self.__append_package(self.packages[k], result)
      elif self.packages.has_key(requireName):
        self.__append_package(self.packages[requireName], result)

  def __append_package(self, package, result):
    packageName = package.name
    if not result.has_key(packageName):
      result[packageName] = package
      if len(package.requires) > 0:
        self.__resolve_core(get_requires(package.requires), result)


class CygwinPackage(object):
  __solts__ = [ "dir",
    "name", "sdesc", "ldesc", "categories", "requires", "specs"]
  
  def download(self, spec):
    current_ver = self.__select_spec(spec)
    if not current_ver:
      report_info('Package "%s" dose not exist binary file, download skipped.' % self.name)
      return True
    url = get_url(current_ver["path"])
    base_name = os.path.basename(current_ver["path"])
    file_path = os.path.join(self.dir, current_ver["path"])
    if os.path.exists(file_path):
      if self.__verify(current_ver):
        report_info('"%s" already exists, PASS!' % base_name)
        return True
      report_info("Verify exist file failed, downloading " + base_name + " ...")
    else:
      report_info("Downloading " + base_name + " ...")
    download_file(url, file_path)
    return self.__verify(current_ver)
  
  def get_path(self, spec):
    current_ver = self.__select_spec(spec)
    if not current_ver:
      return "N/A"
    return os.path.join(self.dir, current_ver["path"])
  
  def __select_spec(self, spec):
    if self.specs.has_key(spec):
      return self.specs[spec]["binary"]
    elif self.specs.has_key("current") and self.specs["current"].has_key("binary"):
      return self.specs["current"]["binary"]
    return None
  
  def __verify(self, current_ver):
    import hashlib
    file_path = os.path.join(self.dir, current_ver["path"])
    if not os.path.exists(file_path): return False
    if os.path.getsize(file_path) != current_ver["size"]:
      return False
    m = hashlib.md5()
    f = file(file_path, "rb")
    while True:
      rs = f.read(BUFFER_SIZE)
      if rs == "":
        break
      m.update(rs)
    f.close()
    return m.hexdigest() == current_ver["hash"]


class TaskManager(object):
  import threading
  lock = threading.Lock()
  
  def run(self, tasks):
    import time
    from Queue import Queue
    from threading import Thread

    def _job_core(tasks):
      while tasks.qsize() > 0:
        if self.lock.acquire():
          task = tasks.get()
          self.lock.release()
          code, msg  = task()
          report_info(">> [%s] : %s" % (task.name, msg))
          if isinstance(code, int): exit(code)
          if tasks.qsize() != 0:
              report_info("   Reaming %d." % (tasks.qsize()))
          tasks.task_done()
    
    JOBS_SIZE = 5
    runningTasks = Queue()
    # Run tasks with job size
    for task in tasks:
        runningTasks.put(task)
    
    runners = []
    for i in xrange(JOBS_SIZE):
        runner = Thread(target = _job_core, args = (runningTasks,))
        runner.daemon = True
        runner.start()
        runners.append(runner)
    # Wait all tasks complete, It can response Ctrl + C interrupt.
    while any(runner.isAlive() for runner in runners):
      time.sleep(1)
    runningTasks.join()


def main():
  initialize_options()
  try:
    repos = CygwinRepository(option_setupinfo, option_target_dir)
  except IOError:
    report_info('Error opening setup.ini file.')
    sys.exit(EX_NO_SETUP_INFO)
  
  deps = repos.resolve(option_requires)
  outputs = []
  if not option_no_download:
    def async_run(package, spec, outputs):
      try:
        if package.download(spec):
          outputs.append(package.get_path(spec))
        else:
          return EX_VERIFY_FAILED, "Verify package %s failed." % (package.name)
      except urllib2.HTTPError as e:
        if e.getcode() == 404 and k == "_update-info-dir":
          return EX_UPDATE_SETUP_INFO, "setup.ini file has expired, use '-s *' switch or update this file."
        else:
          return EX_HTTP_ERROR, ("Http error code " + str(e.getcode()) + " of " + e.geturl())
      return None, "DONE"
    tasks = []
    for k, v in deps.iteritems():
      task = lambda pkg=v: async_run(pkg, option_version_spec, outputs)
      task.name = v.name
      tasks.append(task)
    taskMan = TaskManager()
    taskMan.run(tasks)
  else:
    outputs = []
    for k, v in deps.iteritems():
      outputs.append(v.get_path(option_version_spec))

  # Normalize result
  for i in xrange(len(outputs)): outputs[i] = os.path.normcase(outputs[i])
  outputs.sort()
  if len(outputs) > 0:
    print("\n".join(outputs))
  exit(EX_OK)


if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt as e:
    report_info('\nYou cancelled the operation!') 
    exit(EX_KEY_SIGNAL)
