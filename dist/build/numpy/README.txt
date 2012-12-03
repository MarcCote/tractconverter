NumPy is the fundamental package needed for scientific computing with Python. 
This package contains:

    * a powerful N-dimensional array object
    * sophisticated (broadcasting) functions
    * tools for integrating C/C++ and Fortran code
    * useful linear algebra, Fourier transform, and random number capabilities. 

It derives from the old Numeric code base and can be used as a replacement for Numeric. It also adds the features introduced by numarray and can be used to replace numarray.

More information can be found at the website:

http://scipy.org/NumPy

After installation, tests can be run with:

python -c 'import numpy; numpy.test()'

When installing a new version of numpy for the first time or before upgrading
to a newer version, it is recommended to turn on deprecation warnings when
running the tests:

python -Wd -c 'import numpy; numpy.test()'

The most current development version is always available from our
git repository:

http://github.com/numpy/numpy


