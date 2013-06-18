"""
Implement the command-line tool interface.
"""

import argparse

DESCRIPTION = "Run JavaScript test suites and collect coverage information."
TEST_SUITE_HELP = "Test suite description file."
COVERAGE_XML_HELP = "Generated XML coverage report."
COVERAGE_HTML_HELP = "Generated HTML coverage report."


def parse_args(argv):
    """
    Parse command line arguments, returning a dict of valid options.

        {
            'test_suite_desc': TEST_SUITE_DESCRIPTION,
            'coverage_xml': COVERAGE_XML,
            'coverage_html': COVERAGE_HTML
        }

    `TEST_SUITE_DESCRIPTION` is a file handle describing the test suite to run
    (source files, spec files, dependencies, browser to use, etc.)

    `COVERAGE_XML` is the name of the coverage XML report to generate.
    `COVERAGE_HTML` is the name of the coverage HTML report to generate.

    `coverage_xml` and `coverage_html` are optional; if not specified,
    the dictionary will not contain those keys.

    Raises an `IOError` if the test suite description does not exist.
    Raises a `SystemExit` exception if arguments are otherwise invalid.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('test_suite_desc', type=file, help=TEST_SUITE_HELP)
    parser.add_argument('--coverage-xml', type=str, help=COVERAGE_XML_HELP)
    parser.add_argument('--coverage-html', type=str, help=COVERAGE_HTML_HELP)

    return vars(parser.parse_args(argv))


def main():
    """
    Main entry point for the command-line tool.
    """
    pass


if __name__ == "__main__":
    main()
