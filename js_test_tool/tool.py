"""
Implement the command-line tool interface.
"""

import argparse
import sys
from js_test_tool.runner import SuiteRunnerFactory

DESCRIPTION = "Run JavaScript test suites and collect coverage information."
TEST_SUITE_HELP = "Test suite description file."
COVERAGE_XML_HELP = "Generated XML coverage report."
COVERAGE_HTML_HELP = "Generated HTML coverage report."
PHANTOMJS_HELP = "Run the tests using the PhantomJS browser."
CHROME_HELP = "Run the tests using the Chrome browser."
FIREFOX_HELP = "Run the tests using the Firefox browser."

BROWSER_ARGS = [('--use-phantomjs', 'phantomjs', PHANTOMJS_HELP),
                ('--use-chrome', 'chrome', CHROME_HELP),
                ('--use-firefox', 'firefox', FIREFOX_HELP)]


def parse_args(argv):
    """
    Parse command line arguments, returning a dict of valid options.

        {
            'test_suite_paths': TEST_SUITE_PATHS,
            'coverage_xml': COVERAGE_XML,
            'coverage_html': COVERAGE_HTML
            'browser_names': BROWSER_NAMES
        }

    `TEST_SUITE_PATHS` is a list of paths to files describing the test
    suite to run (source files, spec files, dependencies, browser to use, etc.)

    `COVERAGE_XML` is the name of the coverage XML report to generate.
    `COVERAGE_HTML` is the name of the coverage HTML report to generate.

    `coverage_xml` and `coverage_html` are optional; if not specified,
    the dictionary will not contain those keys.

    `BROWSER_NAMES` is the list of browsers under which to run the tests.

    `argv` is the list of command line arguments, starting with
    the name of the program.

    Raises an `IOError` if the test suite description does not exist.
    Raises a `SystemExit` exception if arguments are otherwise invalid.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    # Test suite description files
    parser.add_argument('test_suite_paths', type=str, nargs='+',
                        help=TEST_SUITE_HELP)

    # Coverage output files
    parser.add_argument('--coverage-xml', type=str, help=COVERAGE_XML_HELP)
    parser.add_argument('--coverage-html', type=str, help=COVERAGE_HTML_HELP)

    # Browsers
    for (browser_arg, browser_name, browser_help) in BROWSER_ARGS:
        parser.add_argument(browser_arg, dest='browser_names',
                            action='append_const', const=browser_name,
                            help=browser_help)

    # Parse the arguments
    # Exclude the first argument, which is the name of the program
    arg_dict = vars(parser.parse_args(argv[1:]))

    # Check that we have at least one browser specified
    if not arg_dict.get('browser_names'):
        raise SystemExit('You must specify at least one browser.')

    return arg_dict


def generate_reports(suite_runner, output_file):
    """
    Use `suite_runner` (a `SuiteRunner` instance)
    to generate test and coverage reports.  Write the test report
    to `output_file` (an open file-like object).

    Returns a boolean indicating whether all the tests passed.
    """

    # Generate the test results report
    passed, test_report = suite_runner.run()

    # Generate the coverage reports
    # (may do nothing if dependencies not installed
    # or report paths not specified)
    suite_runner.write_coverage_reports()

    # Print test results to the output file (may be stdout)
    output_file.write(test_report)

    return passed


def main():
    """
    Main entry point for the command-line tool.
    """
    args_dict = parse_args(sys.argv)

    # Configure a test suite runner
    factory = SuiteRunnerFactory()
    suite_runner, browser_list = \
        factory.build_runner(args_dict.get('test_suite_paths'),
                             args_dict.get('browser_names'),
                             args_dict.get('coverage_xml'),
                             args_dict.get('coverage_html'))

    try:
        # Generate the reports and write test results to stdout
        all_passed = generate_reports(suite_runner, sys.stdout)

    finally:

        # Quit out of the browsers we created
        for browser in browser_list:
            browser.quit()

    # If any test failed, exit with non-zero status code
    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
