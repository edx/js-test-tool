#!/usr/bin/env bash

# Run the tests under coverage and report diff coverage
# Includes both unit and acceptance test suites

# Make sure you run `pip install -r test-requirements.txt`
# to get requirements for this script.

# Run from the repo root

coverage run -p -m nose
coverage run -p `which lettuce` js_test_tool/features
coverage combine
coverage xml
diff-cover coverage.xml
