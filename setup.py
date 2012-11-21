#!/usr/bin/python
# -*- coding: UTF-8 -*-

import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages

setup(
    name='TractConverter',
    version='0.3.4',
    author='Marc-Alexandre Côté',
    author_email='marc-alexandre.cote@usherbrooke.ca',
    packages = find_packages(),
    scripts = ['distribute_setup.py'],
    entry_points = {
        'console_scripts': [
            'TractConverter = tractconverter.TractConverter:main',
            'WalkingTractConverter = tractconverter.WalkingTractConverter:main',
            ],
        'setuptools.installation': [
            'eggsecutable = tractconverter.WalkingTractConverter:main',
            ]
        },
    #url='http://pypi.python.org/pypi/TractConverter/',
    license='LICENSE.txt',
    description='Converter for white matter tract files used in neuroimaging.',
    long_description=open('README.txt').read(),
    install_requires=[
        'distribute',
        'numpy',
        'nibabel >= 1.1.0',
    ],
)