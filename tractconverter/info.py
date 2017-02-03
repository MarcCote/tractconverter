# -*- coding: UTF-8 -*-

""" This file contains defines parameters for tractconverter that we use to fill
settings in setup.py, the tractconverter top-level docstring, and for building the
docs.  In setup.py in particular, we exec this file, so it cannot import tractconverter
"""

# tractconverter version information.  An empty _version_extra corresponds to a
# full release.  '.dev' as a _version_extra string means this is a development
# version
_version_major = 0
_version_minor = 8
_version_micro = 1
#_version_extra = '.dev'
_version_extra = ''

# Format expected by setup.py and doc/source/conf.py: string of form "X.Y.Z"
__version__ = "%s.%s.%s%s" % (_version_major,
                              _version_minor,
                              _version_micro,
                              _version_extra)

CLASSIFIERS = ["Development Status :: 3 - Alpha",
               "Environment :: Console",
               "Intended Audience :: Science/Research",
               "License :: OSI Approved :: BSD License",
               "Operating System :: OS Independent",
               "Programming Language :: Python",
               "Topic :: Scientific/Engineering"]

description = 'Tractogram converter in python'

# Note: this long_description is actually a copy/paste from the top-level
# README.txt, so that it shows up nicely on PyPI.  So please remember to edit
# it only in one place and sync it correctly.
long_description = """
================
 TractConverter
================

TractConverter is a python toolbox to convert tractogram files.

TractConverter is for research only; please do not use results
from TractConverter on clinical data.

Website
=======

N/A

Mailing Lists
=============

N/A

Code
====

You can find our sources and single-click downloads:

* `Main repository`_ on Github.
* Documentation_ for all releases and current development tree.
* Download as a tar/zip file the `current trunk`_.
* Downloads of all `available releases`_.

.. _main repository: http://github.com/MarcCote/tractconverter
.. _Documentation: N/A
.. _current trunk: http://github.com/MarcCote/tractconverter/master
.. _available releases: N/A

License
=======

tractconverter is licensed under the terms of the BSD license. Some code included with
tractconverter is also licensed under the BSD license.  Please the LICENSE file in the
tractconverter distribution.
"""

# versions for dependencies
NUMPY_MIN_VERSION='1.7'
NIBABEL_MIN_VERSION='1.0.0'

# Main setup parameters
NAME                = 'tractconverter'
MAINTAINER          = "Marc-Alexandre Côté"
MAINTAINER_EMAIL    = "marc-alexandre.cote@usherbrooke.ca"
DESCRIPTION         = description
LONG_DESCRIPTION    = long_description
URL                 = "N/A"
DOWNLOAD_URL        = "N/A"
LICENSE             = "BSD license"
CLASSIFIERS         = CLASSIFIERS
AUTHOR              = "SCIL"
AUTHOR_EMAIL        = "scil@gmail.com"
PLATFORMS           = "OS Independent"
MAJOR               = _version_major
MINOR               = _version_minor
MICRO               = _version_micro
ISRELEASE           = _version_extra == ''
VERSION             = __version__
PROVIDES            = ["tractconverter"]
REQUIRES            = ["numpy (>=%s)" % NUMPY_MIN_VERSION,
                       "nibabel (>=%s)" % NIBABEL_MIN_VERSION]
