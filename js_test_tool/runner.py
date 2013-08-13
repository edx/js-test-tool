"""
Run test suites and generate coverage reports.
"""
from js_test_tool.suite import SuiteDescription, SuiteRenderer
from js_test_tool.suite_server import SuitePageServer
from js_test_tool.coverage_report import HtmlCoverageReporter, XmlCoverageReporter
from js_test_tool.browser import Browser
from textwrap import dedent
import os.path
from jinja2 import Environment, PackageLoader

import logging
LOGGER = logging.getLogger(__name__)

# Set up the template environment
TEMPLATE_LOADER = PackageLoader(__package__)
TEMPLATE_ENV = Environment(loader=TEMPLATE_LOADER,
                           trim_blocks=True)


class UnknownBrowserError(Exception):
    """
    The suite runner encountered an unknown browser name.
    """
    pass


class SuiteRunner(object):
    """
    Run test suites and generate coverage reports.
    """

    # Name of the template used to render the report
    REPORT_TEMPLATE_NAME = 'console_report.txt'

    def __init__(self, browser_list, suite_page_server, coverage_reporters):
        """
        Configure the suite runner to retrieve test suite pages
        from `suite_page_server` (`SuitePageServer` instance)
        and generate coverage reports using `coverage_reporters`
        (a list of `CoverageReporter` instances).

        Uses each `Browser` instance in `browser_list` to load the test
        suite pages.
        """

        # Store dependencies
        self._browser_list = browser_list
        self._suite_page_server = suite_page_server
        self._coverage_reporters = coverage_reporters

    def run(self):
        """
        Execute each available test suite page and record whether
        each test passed/failed.

        Returns a tuple `(passed, report)` where `passed` is a boolean
        indicating whether all tests passed and `report` is a unicode
        string report of test results.
        """

        # Start the suite page server running on a local port
        self._suite_page_server.start()

        # Create a dictionary to store context passed to the template
        context_dict = {'browser_results': [],
                        'all_passed': True}

        try:

            for browser in self._browser_list:

                # Run the test suite with one of our browsers
                browser_results = self._run_with_browser(browser)
                context_dict['browser_results'].append(browser_results)

                # Check whether any of the tests failed
                stats = browser_results['stats']
                if (stats['num_failed'] + stats['num_error']) > 0:
                    context_dict['all_passed'] = False

            # After all browsers have loaded their pages,
            # Block until all coverage data received
            # (if coverage is not configured, this will
            # not do anything).
            self._suite_page_server.all_coverage_data()

        # Re-raise any exceptions that occur
        except:
            raise

        # Stop the suite page server, freeing up the port
        finally:
            self._suite_page_server.stop()

        # Render the console report
        template = TEMPLATE_ENV.get_template(self.REPORT_TEMPLATE_NAME)
        report_str = template.render(context_dict)

        return (context_dict['all_passed'], report_str)

    def write_coverage_reports(self):
        """
        Generate coverage reports by running each available test suite page.
        The location and format of the reports is controlled by
        how the `CoverageReporter` is configured.

        Note: this may not create any reports if JSCover is not configured
        or no report paths were specified.
        """
        data = self._suite_page_server.all_coverage_data()

        if data is not None:
            for reporter in self._coverage_reporters:
                reporter.write_report(data)

    def _run_with_browser(self, browser):
        """
        Load all test suite pages in `browser` (a `Browser` instance)
        and return a dictionary describing the results.

        The returned dictionary has the following form:

            {
                'browser_name': BROWSER_NAME,

                'test_results': [ {'test_group': TEST_GROUP,
                                   'test_name': TEST_NAME,
                                   'status': "pass" | "fail" | "skip" | "error",
                                   'detail': DETAILS }, ...],

                'stats': {'num_failed': NUM_FAILED,
                          'num_error': NUM_ERROR,
                          'num_skipped': NUM_SKIPPED,
                          'num_passed': NUM_PASSED}
            }

        If an error occurs when retrieving or parsing the page,
        raises a `BrowserError`.
        """

        all_results = []

        # Load each suite page URL
        for url in self._suite_page_server.suite_url_list():

            # Use the browser to load the page and parse the results
            suite_results = browser.get_page_results(url)

            # Store the results and keep loading pages
            all_results.extend(suite_results)

        # Calculate statistics
        stats = self._result_stats(all_results)

        # Construct the context dict
        return {'browser_name': browser.name(),
                'test_results': all_results,
                'stats': stats}

    def _result_stats(self, all_results):
        """
        Calculate totals for each status in `all_results`.

        `all_results` is a list of result dictionaries.  See
        `Browser.get_page_results()` for the format of the dictionary items.

        Returns a dictionary of the form

            {'num_failed': NUM_FAILED,
             'num_error': NUM_ERROR,
             'num_skipped': NUM_SKIPPED,
             'num_passed': NUM_PASSED}
        """
        stats_dict = {'num_failed': 0,
                      'num_error': 0,
                      'num_skipped': 0,
                      'num_passed': 0}

        # For each test that we ran, across all test suites
        for result_dict in all_results:

            # Get the result status (assumed to be defined)
            status = result_dict['status']

            # Determine which value to increment
            if status == 'fail':
                key = 'num_failed'
            elif status == 'error':
                key = 'num_error'
            elif status == 'skip':
                key = 'num_skipped'
            elif status == 'pass':
                key = 'num_passed'
            else:
                msg = '{} is not a valid result status'.format(status)
                raise ValueError(msg)

            # Increment the appropriate count
            stats_dict[key] += 1

        # Return the stats we collected
        return stats_dict


class SuiteRunnerFactory(object):
    """
    Configure `SuiteRunner` instances.
    """

    # Supported browser names
    SUPPORTED_BROWSERS = ['chrome', 'firefox', 'phantomjs']

    def __init__(self,
                 desc_class=SuiteDescription,
                 renderer_class=SuiteRenderer,
                 server_class=SuitePageServer,
                 html_coverage_class=HtmlCoverageReporter,
                 xml_coverage_class=XmlCoverageReporter,
                 browser_class=Browser,
                 runner_class=SuiteRunner):
        """
        Configure the factory to use the provided classes.
        You should only ever override the defaults when testing.
        """
        self._desc_class = desc_class
        self._renderer_class = renderer_class
        self._server_class = server_class
        self._html_coverage_class = html_coverage_class
        self._xml_coverage_class = xml_coverage_class
        self._browser_class = browser_class
        self._runner_class = runner_class

    def build_runner(self, suite_path_list, browser_names,
                     coverage_xml_path, coverage_html_path,
                     timeout_sec):
        """
        Configure `SuiteRunner` instances for each suite description.
        Each `SuiteRunner` will:

        * Start instances of each browser listed in `browser_names`.
        `browser_names` is a list of browser names such as "chrome",
        "firefox", and "phantomjs".

        * Run the test suites described in
          `suite_path_list` (list of paths to suite description files)

        * Write coverage reports to `coverage_xml_path` (Cobertura XML format)
          and `coverage_html_path` (HTML).

        If the coverage paths are `None`, that report will not be generated.

        Returns a tuple `(suite_runners, browsers)`

        * `suite_runner` is a configured `SuiteRunner` instance.
        * `browsers` is a list of browsers used by the runners.

        It is the caller's responsibility to call `Browser.quit()` for
        each browser in the list.

        Uses the environment variable `JSCOVER_JAR` to configure
        the server to instrument JavaScript sources for coverage.
        `JSCOVER_JAR` should be a path to the JSCover JAR file.

        Raises an `UnknownBrowserError` if an invalid browser name is provided.
        Raises a `ValueError` if no browser names are provided.
        """

        # Validate the list of browser names
        # Can raise an exception if the list is invalid
        self._validate_browser_names(browser_names)

        # Load the suite descriptions
        suite_desc_list = self._build_suite_descriptions(suite_path_list)

        # Create a renderer
        renderer = self._renderer_class()

        # Create the coverage reporters
        coverage_reporters = []
        if coverage_xml_path is not None:
            xml_coverage = self._xml_coverage_class(coverage_xml_path)
            coverage_reporters.append(xml_coverage)

        if coverage_html_path is not None:
            html_coverage = self._html_coverage_class(coverage_html_path)
            coverage_reporters.append(html_coverage)

        # Configure to use coverage only if we expect a report
        if len(coverage_reporters) > 0:

            # Get the path to the JSCover JAR file from an env variable
            jscover_path = os.environ.get('JSCOVER_JAR')

            # Print a warning if the path isn't set
            if jscover_path is None:
                msg = dedent("""
                JSCover is not configured: no coverage reports will be generated.

                To configure JSCover:

                1) Download the latest version from http://tntim96.github.io/JSCover/
                2) Set the JSCOVER_JAR environment variable as the path to JSCover-all.jar
                """).strip()

                LOGGER.warning(msg)

        else:
            jscover_path = None

        # Create the suite page server
        # We re-use the same server across test suites
        server = self._server_class(suite_desc_list, renderer,
                                    jscover_path=jscover_path)

        # Create a list of all browsers we will need
        browsers = [self._browser_class(name, timeout_sec=timeout_sec)
                    for name in browser_names]

        # Create a suite runner for each description
        runner = self._runner_class(browsers, server, coverage_reporters)

        # Return the list of suite runner and browsers
        return runner, browsers

    def _build_suite_descriptions(self, suite_path_list):
        """
        Load suite descriptions from files located at paths in
        `suite_path_list`.

        Returns the list of `SuiteDescription` instances.
        """

        desc_list = []

        for path in suite_path_list:

            with open(path) as desc_file:
                root_dir = os.path.dirname(os.path.abspath(path))
                desc = self._desc_class(desc_file, root_dir)
                desc_list.append(desc)

        return desc_list

    @classmethod
    def _validate_browser_names(cls, browser_list):
        """
        Validate the list of browser names in `browser_list`.
        If it encounters unknown browser names, raises a `UnknownBrowserError`.
        If the list is empty, it raises a `ValueError`.
        """

        # Empty list
        if len(browser_list) == 0:
            raise ValueError("No browser names specified.")

        # Validate the list of browser names
        unknown_browsers = [name for name in browser_list
                            if not name in cls.SUPPORTED_BROWSERS]

        if len(unknown_browsers) > 0:
            msg = "Unknown browsers: {}".format(', '.join(unknown_browsers))
            raise UnknownBrowserError(msg)
