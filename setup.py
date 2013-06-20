#!/usr/bin/env python

from setuptools import setup

REQUIREMENTS = [line.strip() for line in 
                open("requirements.txt").readlines()]

setup(
    name='js_test_tool',
    version='0.0.1',
    description='Run JavaScript test suites and collect coverage information.',
    author='Will Daly',
    author_email='will@edx.org',
    packages=['js_test_tool'],
    install_requires=['setuptools'] + REQUIREMENTS,
    entry_points={
        'console_scripts': ['js-test-tool = js_test_tool.tool:main']
    }
)
