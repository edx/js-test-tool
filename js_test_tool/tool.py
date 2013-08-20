"""
Implement the command-line tool interface.
"""

import argparse
import sys
from textwrap import dedent
import pkg_resources
import os.path
from js_test_tool.runner import SuiteRunnerFactory
from js_test_tool.dev_runner import SuiteDevRunnerFactory

import logging
LOGGER = logging.getLogger(__name__)

VALID_COMMANDS = ['init', 'run', 'dev']

DESCRIPTION = "Run JavaScript test suites and collect coverage information."
COMMAND_HELP = dedent("""
        init: Create a default suite description in the current directory.
        run: Run the test suites provided.
        dev: Run the test suite in the default browser.
        """).strip()
TEST_SUITE_HELP = "Test suite description file."
COVERAGE_XML_HELP = "Generated XML coverage report."
COVERAGE_HTML_HELP = "Generated HTML coverage report."
PHANTOMJS_HELP = "Run the tests using the PhantomJS browser."
CHROME_HELP = "Run the tests using the Chrome browser."
FIREFOX_HELP = "Run the tests using the Firefox browser."
TIMEOUT_HELP = "Number of seconds to wait for the test runner page to load before timing out."

BROWSER_ARGS = [('--use-phantomjs', 'phantomjs', PHANTOMJS_HELP),
                ('--use-chrome', 'chrome', CHROME_HELP),
                ('--use-firefox', 'firefox', FIREFOX_HELP)]

DEFAULT_SUITE_DESC_PATH = 'templates/default_test_suite.yml'


def parse_args(argv):
    """
    Parse command line arguments, returning a dict of valid options.

        {
            'command': 'init' | 'run',
            'test_suite_paths': TEST_SUITE_PATHS,
            'coverage_xml': COVERAGE_XML,
            'coverage_html': COVERAGE_HTML,
            'browser_names': BROWSER_NAMES,
            'timeout_sec': TIMEOUT_SEC
        }

    The command indicates whether to `init` (create a default suite description)
    or `run` the suite.

    `TEST_SUITE_PATHS` is a list of paths to files describing the test
    suite to run (source files, spec files, dependencies, browser to use, etc.)

    `COVERAGE_XML` is the name of the coverage XML report to generate.
    `COVERAGE_HTML` is the name of the coverage HTML report to generate.

    `coverage_xml` and `coverage_html` are optional; if not specified,
    the dictionary will not contain those keys.

    `BROWSER_NAMES` is the list of browsers under which to run the tests.

    `TIMEOUT_SEC` is the number of seconds to wait for a test runner
    page to load before timing out.

    `argv` is the list of command line arguments, starting with
    the name of the program.

    Raises an `IOError` if the test suite description does not exist.
    Raises a `SystemExit` exception if arguments are otherwise invalid.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    # Command
    parser.add_argument('command', type=str, help=COMMAND_HELP)

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

    # Timeout
    parser.add_argument('--timeout-sec', type=float, help=TIMEOUT_HELP)

    # Parse the arguments
    # Exclude the first argument, which is the name of the program
    arg_dict = vars(parser.parse_args(argv[1:]))

    # Check that the command is one we recognize
    if not arg_dict.get('command') in VALID_COMMANDS:
        raise SystemExit('Invalid command.')

    # Check that we have at least one browser specified
    # if running the test suite
    if arg_dict.get('command') == 'run' and not arg_dict.get('browser_names'):
        raise SystemExit('You must specify at least one browser.')

    # Check that if we're running in dev mode, we're
    # only using one test suite
    if arg_dict.get('command') == 'dev' and len(arg_dict.get('test_suite_paths')) > 1:
        raise SystemExit('You cannot run multiple test suites in dev mode')

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


def create_default_suite(*file_name_list):
    """
    Create a default suite description at each file name
    provided in `file_name_list`
    """
    suite_desc_str = pkg_resources.resource_string('js_test_tool',
                                                   DEFAULT_SUITE_DESC_PATH)

    for name in file_name_list:

        # If the file already exists, skip it
        if os.path.exists(name):
            LOGGER.warning("'{}' already exists".format(name))

        # Otherwise, create it
        else:
            with open(name, 'w') as file_handle:
                file_handle.write(suite_desc_str)

            print "Created '{}'".format(name)


def main():
    """
    Main entry point for the command-line tool.
    """
    args_dict = parse_args(sys.argv)
    command = args_dict.get('command')

    if command == 'init':
        create_default_suite(*args_dict.get('test_suite_paths'))

    elif command == 'dev':

        # Arg validation guarantees that there is exactly 1 path
        test_suite_path = args_dict.get('test_suite_paths')[0]

        # Build a dev-mode runner using a factory
        factory = SuiteDevRunnerFactory()
        suite_dev_runner = factory.build_runner(test_suite_path)

        # Run in dev mode (serve pages until user terminates)
        suite_dev_runner.run()

    elif command == 'run':

        # Configure a test suite runner
        factory = SuiteRunnerFactory()
        suite_runner, browser_list = \
            factory.build_runner(args_dict.get('test_suite_paths'),
                                 args_dict.get('browser_names'),
                                 args_dict.get('coverage_xml'),
                                 args_dict.get('coverage_html'),
                                 args_dict.get('timeout_sec'))

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

    # Shouldn't get here because we validate the args,
    # but it never hurts to check.
    else:
        raise SystemExit('Invalid command.')


if __name__ == "__main__":
    main()
