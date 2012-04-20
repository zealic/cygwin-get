#!/usr/bin/env python
# -*- coding:utf-8 -*-
# <code>
#   <author name="Zealic" email="zealic(at)gmail.com" />
#   <timestamp>2012-04-20</timestamp>
# </code>
"""cygwin-get 0.3 - Manage cygwin installations (Command-line user interface).

Usage:
cygwin-get [-h] [-d] [-s <file>] [-r <file>] [-t <dir>] [-m <url>] [-v <spec>] <packages-list>

=======================================
-h |--help
    Display this help.

-n | --no-download
    Do not download packages.

-s | --setupinfo
    Specify setup file. (Default : $TARGET-DIR/setup.ini, when use "*", will download it from web.)

-r | --response
    Xml packages response file (packages-list).

-t | --target-dir
    Target download directory. (Default : $CYGWIN-GET_HOME/packages).

--mirror
    Mirror site. (Default : http://mirrors.163.com/cygwin)

--version-spec
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
__version__ = "0.2"
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
option_version_spec   = "test"


def initialize():
  import getopt
  global option_no_download, option_target_dir, option_mirror, option_version_spec
  option_setupinfo = None
  option_response_file = None
  
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
  
  requires = {}
  if option_response_file <> None and os.path.exists(option_response_file):
    requires = parse_response_file(option_response_file)
  requires = get_requires(args, requires)
  
  if option_setupinfo == "*" or option_setupinfo == None:
    setupinfo_file = os.path.join(option_target_dir, "setup.ini")
    if option_setupinfo == "*" or not os.path.exists(setupinfo_file):
      url = get_url("setup.ini")
      download_file(url, setupinfo_file)
    option_setupinfo = setupinfo_file
  
  try:
    allPkg = parse_cygwin_config(option_setupinfo)
  except IOError:
    report_info('Error opening setup.ini file.')
    sys.exit(EX_NO_SETUP_INFO)
  
  return allPkg, requires

def get_requires(names, old_requires = {}):
  requires = dict(old_requires)
  for name in names:
    requires[name] = {}
  for k, v in requires.iteritems():
    if not v.has_key("spec"): v["spec"] = option_version_spec
  return requires

def main():
  allPkg, requires = initialize()
  
  deps = {}
  
  if len(requires) > 0:
    resolve_deps(allPkg, requires, deps)
  if not option_no_download:
      outputs = []
      for k, v in deps.iteritems():
        try:
          package_file = get_package(v, v["spec"])
          if package_file:
            outputs.append(package_file)
        except urllib2.HTTPError as e:
          if e.getcode() == 404 and k == "_update-info-dir":
            report_info("setup.ini file has expired, use '-s*' switch or update this file.")
            exit(EX_UPDATE_SETUP_INFO)
          else:
            report_info("Http error code " + str(e.getcode()) + " of " + e.geturl())
            exit(EX_HTTP_ERROR)
      outputs.sort()
      if len(outputs) > 0:
        print("\n".join(outputs))
  else:
    outputs = []
    for k, v in deps.iteritems():
      outputs.append(k)
    if len(outputs) > 0:
      print("\n".join(outputs))
  exit(EX_OK)


def usage(exitCode = None):
  report_info(__doc__)
  if exit != None: exit(exitCode)


def parse_response_file(response_file):
  from xml.etree.ElementTree import ElementTree
  
  try:
    tree = ElementTree()
    root = tree.parse(response_file)
    packages = root.findall('package')
    result = {}
    for p in packages:
      currentRequire = {}
      name = p.attrib["name"]
      result[name] = currentRequire
      if p.attrib.has_key("spec"):
        currentRequire["spec"] = p.attrib["spec"]
      else:
        currentRequire["spec"] = option_version_spec
    return result
  except Exception as e:
    report_info("Invalid response file '%s', %s" % (response_file, e.message))
    exit(EX_INVALID_RESPONSE)


def parse_cygwin_config(config_file):
  cfg = file(config_file, "r")
  allLines = cfg.readlines()

  allPkg = {}
  currentPkg = {}
  currentSpec = {}

  for currentLine in allLines:
    currentLine = currentLine.strip()
    if currentLine.startswith("@ "):
      pkgName = str(currentLine[2:])
      specName = "current"
      currentPkg = {}
      currentSpec = {"name": specName, "package_name": pkgName}
      currentPkg["name"] = pkgName
      currentPkg["specs"] = {}
      currentPkg["specs"][specName] = currentSpec
      allPkg[pkgName] = currentPkg
    elif currentLine.startswith("[") and currentLine.endswith("]"):
      name = currentLine[1:-1]
      currentSpec = {"name": name, "package_name": currentPkg["name"]}
      currentPkg["specs"][name] = currentSpec
    elif currentLine.startswith("sdesc: "):
      currentPkg["sdesc"] = currentLine[8:-1]
    elif currentLine.startswith("ldesc: "):
      if currentLine.endswith('"'):
        currentPkg["ldesc"] = str(currentLine[8:-1])
      else:
        currentPkg["__ldesc"] = str(currentLine[8:])
    elif currentLine.endswith('"') and currentPkg.has_key("__ldesc"):
      currentPkg["ldesc"] = currentPkg["__ldesc"] + "\n" + str(currentLine[0:-1])
      del currentPkg["__ldesc"]
    elif currentPkg.has_key("__ldesc"):
      currentPkg["__ldesc"] = currentPkg["__ldesc"] + "\n" + currentLine
    elif currentLine.startswith("category: "):
      currentPkg["category"] = set(str(currentLine[10:]).split(" "))
    elif currentLine.startswith("requires: "):
      currentPkg["requires"] = set(str(currentLine[10:]).split(" "))
    elif currentLine.startswith("version: "):
      currentSpec["version"] = str(currentLine[9:])
    elif currentLine.startswith("install: "):
      install_parts = str(currentLine[9:]).split(" ")
      currentSpec["install"] = {"path" : install_parts[0], "size" : install_parts[1], "hash" : install_parts[2]}
    elif currentLine.startswith("source: "):
      source_parts = str(currentLine[8:]).split(" ")
      currentSpec["source"] = {"path" : source_parts[0], "size" : source_parts[1], "hash" : source_parts[2]}
  return allPkg


def resolve_deps(all_packages, requires, result):
  for packageName, metadata in requires.iteritems():
    if packageName.startswith("@"):
      categoryName = str(packageName[1:])
      for k, v in all_packages.iteritems():
        if categoryName in v["category"]:
          append_package(all_packages, all_packages[k], metadata["spec"], result)
    elif all_packages.has_key(packageName):
      append_package(all_packages, all_packages[packageName], metadata["spec"], result)


def append_package(all_packages, package, spec, result):
  packageName = package["name"]
  if not result.has_key(packageName):
    result[packageName] = dict(package, spec = spec)
    if package.has_key("requires"):
      resolve_deps(all_packages , get_requires(package["requires"]), result)


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
      if rs == "":
        break
      target_file.write(rs)
  except:
    target_file.close()
    os.remove(file_path)
    raise
  finally:
    if not target_file.closed: target_file.close()


def get_package(package, spec):
  if package["specs"].has_key(spec):
    package_spec = package["specs"][spec]
  else:
    package_spec = package["specs"]["current"]
  
  if not package_spec.has_key("install"):
    return None
  package_path =  package_spec["install"]["path"]
  file_path = os.path.join(option_target_dir, package_path)
  if not download_package(package_spec, file_path):
    report_info("Verify package %s failed : \n%s" % (package["name"], file_path))
    exit(EX_VERIFY_FAILED)
  return file_path


def download_package(package_spec, file_path):
  url = get_url(package_spec["install"]["path"])
  base_name = os.path.basename(url)
  if os.path.exists(file_path):
    if verify_package(package_spec, file_path):
      report_info('"%s" already exists, PASS!' % base_name)
      return True
  
  report_info("Downloading " + base_name + " ...")
  download_file(url, file_path)
  return verify_package(package_spec, file_path)


def verify_package(package_spec, file_path):
  import hashlib
  
  if os.path.getsize(file_path) != int(package_spec["install"]["size"]):
    return False
  m = hashlib.md5()
  f = file(file_path, "rb")
  while True:
    rs = f.read(BUFFER_SIZE)
    if rs == "":
      break
    m.update(rs)
  f.close()
  return m.hexdigest() == package_spec["install"]["hash"]

def report_info(message):
  sys.stderr.write(message + "\n")

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt as e:
    report_info('\nYou cancelled the operation!') 
    exit(EX_KEY_SIGNAL)
