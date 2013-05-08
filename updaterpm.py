#!/usr/bin/python
# updaterpm.py (20070820)
# James Lee <jlee23@cs.umbc.edu>
#
# This script was once written in bash.  Parsing the 'yum' output is unreliable
# so this python script accesses the yum api itself.  This should be much more
# stable.
#
# The point of this script is not to update the rpms on the system as its
# filename might make it sound (thanks, Matt), rather it is written to do what
# yum itself does not; installing all the packages in the configured
# repositories, and removing all the packages installed on the system that are
# not in the repositories.

# Update 20071128: Modified the check on ignoreEnv so that it properly checks
#     for a NoneType object instead of an empty string.

import os
import shutil
import yum
import sys
import re
from types import *

CONFIGFILE='/usr/csee/etc/updaterpm.conf'
CONFDIR='/etc/yum.repos.d'
CSEE_CONFDIR='/etc/yum.repos.d.csee'
STAG_CONFDIR='/etc/yum.repos.d.staging'
STAGINGREPO='staging'

yumopts = ['yum', '-y', '--nogpgcheck']

#Clean up old config
def cleanupConfig():
  if os.path.exists(CONFDIR):
    if os.path.islink(CONFDIR):
      os.remove(CONFDIR)
    elif os.path.isdir(CONFDIR):
      shutil.rmtree(CONFDIR)
    else:
      os.remove(CONFDIR)
	
#Check for test mode argument and set the correct yum configuration
if len(sys.argv) > 1 and sys.argv[1] == '--staging':
  cleanupConfig()
  os.symlink(STAG_CONFDIR, CONFDIR)
elif len(sys.argv) > 1 and sys.argv[1] == '--production':
  cleanupConfig()
  os.symlink(CSEE_CONFDIR, CONFDIR)
elif not(os.path.exists(CONFDIR)):
  os.symlink(CSEE_CONFDIR, CONFDIR)

# Clean Yum cache files to make sure that we get the most recent ones
os.spawnvp(os.P_WAIT, 'yum', yumopts + ['clean all'])

# It actually is a good idea to have an up-to-date system before running the 
# bulk of this script
os.spawnvp(os.P_WAIT, 'yum', yumopts + ['update'])

base = yum.YumBase()
base.doGenericSetup()

# Gets all installed groups, and the available but not installed groups
installedGroups, availableGroups = base.doGroupLists()
installedGroups = set([i.name for i in installedGroups])
availableGroups = set([i.name for i in availableGroups])

# Packages that are installed, but not in any repository
extras = base.doPackageLists('extras').extras
extras = set(extras)

# Groups that should be installed
with open(CONFIGFILE) as configFile:
  allowedGroups = set([i.strip() for i in [x.split("\n") for x in configFile.readlines()]])

# For any package for which there is an update, the older version is marked as
# an extra, but we don't want to remove them, so we get a list of them:
updates = base.doPackagesLists('updates').updates
updates = set(updates)

# We remove the extra packages(Except those being updated), as well
# as any installed groups not in the configfile, then install all
# of the available groups in the config file.
removeGroups = installedGroups.difference(allowedGroups)
removePackages = extras.difference(updates)
installGroups = allowedGroups.intersection(availableGroups)

# Convert the package objects into a format for yum-cli as specified by the yum
# man page
def pkgsToStrList(pkgs):
    strList = []
    for i in pkgs:
        strList.append(str(i.epoch) + ':' + str(i.name) + '-' + str(i.ver) + '-' + str(i.rel) + '.' + str(i.arch))
    return strList

def grpsToStrList(grps):
  return ["@"+str(i.name) for i in grps]

removingPackages = pkgsToStrList(removePackages)
removingGroups = grpsToStrList(removeGroups)
installing = grpsToStrList(installGroups)

print 'Removing:'
for i in removingPackages+removingGroups:
    print '\t' + i

print '\nInstalling:'
for i in installing:
    print '\t' + i

print


if len(removingPackages) > 0:
  os.spawnvp(os.P_WAIT, 'yum', yumopts + ['remove'] + removing)

map(base.selectGroup, installing)
base.buildTransaction()
base.processTransaction()
