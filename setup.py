#!/usr/bin/env python

from setuptools import setup
from js_test_tool import VERSION, DESCRIPTION

REQUIREMENTS = [line.strip() for line in 
                open("requirements.txt").readlines()]

setup(
    name='js_test_tool',
    version=VERSION,
    description=DESCRIPTION,
    author='Will Daly',
    author_email='will@edx.org',
    packages=['js_test_tool'],
    package_data={'js_test_tool': ['templates/*', 'runner/jasmine/*']},
    install_requires=['setuptools'] + REQUIREMENTS,
    entry_points={
        'console_scripts': ['js-test-tool = js_test_tool.tool:main']
    }
)
