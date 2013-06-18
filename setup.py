#!/usr/bin/env python

from setuptools import setup

setup(
    name='js_test_tool',
    version='0.0.1',
    description='Run JavaScript test suites and collect coverage information.',
    author='Will Daly',
    author_email='will@edx.org',
    packages=['js_test_tool'],
    install_requires=['setuptools'],
    entry_points={
        'console_scripts': ['js-test-tool = js_test_tool.tool:main']
    }
)
