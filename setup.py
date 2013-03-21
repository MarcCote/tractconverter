#!/usr/bin/python
# -*- coding: UTF-8 -*-

''' Installation script for tractconverter package '''
# Inspired by setup.py of dipy (http://nipy.sourceforge.net/dipy/)

import os
import sys
from os.path import join as pjoin, dirname
from glob import glob

import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages

# BEFORE importing distutils, remove MANIFEST. distutils doesn't properly
# update it when the contents of directories change.
if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')

import numpy as np

# Get version and release info, which is all stored in tractconverter/info.py
ver_file = pjoin('tractconverter', 'info.py')
execfile(ver_file)

# force_setuptools can be set from the setup_egg.py script
if not 'force_setuptools' in globals():
    # For some commands, use setuptools
    if len(set(('develop', 'bdist_egg', 'bdist_rpm', 'bdist', 'bdist_dumb',
                'bdist_wininst', 'install_egg_info', 'egg_info',
                'easy_install')).intersection(sys.argv)) > 0:
        force_setuptools = True
    else:
        force_setuptools = False

if force_setuptools:
    # Try to preempt setuptools monkeypatching of Extension handling when Pyrex
    # is missing.  Otherwise the monkeypatched Extension will change .pyx
    # filenames to .c filenames, and we probably don't have the .c files.
    sys.path.insert(0, pjoin(dirname(__file__), 'fake_pyrex'))
    import setuptools

# We may just have imported setuptools, or we may have been exec'd from a
# setuptools environment like pip
if 'setuptools' in sys.modules:
    extra_setuptools_args = dict(
        tests_require=['nose'],
        test_suite='nose.collector',
        zip_safe=False,
        extras_require=dict(
            doc=['Sphinx>=1.0'],
            test=['nose>=0.10.1']),
        install_requires=['nibabel>=' + NIBABEL_MIN_VERSION])

    # We need setuptools install command because we're going to override it
    # further down.  Using distutils install command causes some confusion, due
    # to the Pyrex / setuptools hack above (force_setuptools)
    from setuptools.command import install
else:
    extra_setuptools_args = {}
    from distutils.command import install

# Import distutils _after_ potential setuptools import above, and after removing
# MANIFEST
from distutils.core import setup
from distutils.extension import Extension

# Define extensions
EXTS = []

# Do our own build and install time dependency checking. setup.py gets called in
# many different ways, and may be called just to collect information (egg_info).
# We need to set up tripwires to raise errors when actually doing things, like
# building, rather than unconditionally in the setup.py import or exec
# We may make tripwire versions of build_ext, build_py, install
try:
    from nisext.sexts import package_check, get_comrec_build
except ImportError:  # No nibabel
    msg = ('Need nisext package from nibabel installation'
           ' - please install nibabel first')
    # pybuilder = derror_maker(build_py.build_py, msg)
    # extbuilder = derror_maker(build_ext.build_ext, msg)
# else: # We have nibabel
    # pybuilder = get_comrec_build('tractconverter')
    # Cython is a dependency for building extensions, iff we don't have stamped
    # up pyx and c files.
    # extbuilder = cyproc_exts(EXTS, CYTHON_MIN_VERSION, 'pyx-stamps')

# Installer that checks for install-time dependencies


class installer(install.install):

    def run(self):
        package_check('numpy', NUMPY_MIN_VERSION)
        package_check('nibabel', NIBABEL_MIN_VERSION)
        install.install.run(self)


cmdclass = dict(
    install=installer)


def main(**extra_args):
    setup(name=NAME,
          maintainer=MAINTAINER,
          maintainer_email=MAINTAINER_EMAIL,
          description=DESCRIPTION,
          long_description=LONG_DESCRIPTION,
          url=URL,
          download_url=DOWNLOAD_URL,
          license=LICENSE,
          classifiers=CLASSIFIERS,
          author=AUTHOR,
          author_email=AUTHOR_EMAIL,
          platforms=PLATFORMS,
          version=VERSION,
          requires=REQUIRES,
          provides=PROVIDES,
          packages=['tractconverter',
                    'tractconverter.formats'
                    ],
          ext_modules=EXTS,
          package_data={'tractconverter':
                        [pjoin('data', '*')
                         ]},
          data_files=[('share/doc/tractconverter/examples',
                       glob(pjoin('doc', 'examples', '*.py')))],
          scripts=glob(pjoin('scripts', '*')),
          cmdclass=cmdclass,
          **extra_args
          )

# simple way to test what setup will do
# python setup.py install --prefix=/tmp
if __name__ == "__main__":
    main(**extra_setuptools_args)
