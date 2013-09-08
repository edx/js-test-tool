#!/usr/bin/env python

from setuptools import setup
from js_test_tool import VERSION, DESCRIPTION

REQUIREMENTS = [line.strip() for line in 
                open("requirements.txt").readlines()]

setup(
    name='js_test_tool',
    version=VERSION,
    description=DESCRIPTION,
    author='edX',
    url='http://github.com/edx/js-test-tool',
    classifiers=['Development Status :: 3 - Alpha',
                 'Environment :: Console',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: GNU Affero General Public License v3',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python',
                 'Topic :: Software Development :: Testing',
                 'Topic :: Software Development :: Quality Assurance'],
    packages=['js_test_tool'],
    package_data={'js_test_tool': ['templates/*', 'runner/jasmine/*']},
    install_requires=['setuptools'] + REQUIREMENTS,
    entry_points={
        'console_scripts': ['js-test-tool = js_test_tool.tool:main']
    }
)
