"""
Run test suites and generate coverage reports.
"""
from js_test_tool.suite import SuiteDescription, SuiteRenderer
from js_test_tool.suite_server import SuitePageServer, TimeoutError
from js_test_tool.coverage_report import HtmlCoverageReporter, XmlCoverageReporter
from js_test_tool.browser import Browser
from js_test_tool.result_report import ResultData, \
    ConsoleResultReporter, XUnitResultReporter
from textwrap import dedent
import os.path
import sys
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

    def __init__(self, browser_list, suite_page_server,
                 result_reporters, coverage_reporters):
        """
        Configure the suite runner to retrieve test suite pages
        from `suite_page_server` (`SuitePageServer` instance)

        The runner will generate test result reports
        using `result_reporters` (a list of `BaseResultReporter` subclasses).

        The runner will generate coverage reports using
        `coverage_reporters` (a list of `BaseCoverageReporter` subclasses).

        Uses each `Browser` instance in `browser_list` to load the test
        suite pages.
        """

        # Store dependencies
        self._browser_list = browser_list
        self._suite_page_server = suite_page_server
        self._result_reporters = result_reporters
        self._coverage_reporters = coverage_reporters

        # Will store the coverage data we get from the suite server
        self._report_coverage_data = None

    def run(self):
        """
        Execute each available test suite page and record whether
        each test passed/failed.

        If configured, will write test results using reporters.

        Returns a `ResultData` object containing the test results.
        """

        # Start the suite page server running on a local port
        self._suite_page_server.start()

        # Create an object to hold results data for all browsers
        results_data = ResultData()

        try:

            for browser in self._browser_list:

                # Run the test suite with one of our browsers
                results_data.add_results(
                    browser.name(),
                    self._run_with_browser(browser)
                )

            # After all browsers have loaded their pages,
            # Block until all coverage data received
            # (if coverage is not configured, this will
            # not do anything).
            try:
                self._report_coverage_data = self._suite_page_server.all_coverage_data()

            # If we timed out, log it, but don't exit with failure
            except TimeoutError:
                msg = dedent("""
                Did not receive all coverage data.  No coverage reports will be written.
                (This sometimes occurs when JSCover does not have enough memory to run.)
                """).strip()
                LOGGER.warning(msg)

        # Re-raise any exceptions that occur
        except:
            raise

        # Stop the suite page server, freeing up the port
        finally:
            self._suite_page_server.stop()

        # Generate test result reports
        for reporter in self._result_reporters:
            reporter.write_report(results_data)

        return results_data

    def write_coverage_reports(self):
        """
        Generate coverage reports by running each available test suite page.
        The location and format of the reports is controlled by
        how the `CoverageReporter` is configured.

        Note: this may not create any reports if JSCover is not configured
        or no report paths were specified.
        """
        if self._report_coverage_data is not None:
            for reporter in self._coverage_reporters:
                reporter.write_report(self._report_coverage_data)

    def result_reporters(self):
        """
        Return the list of test result reporters for this runner.
        """
        return self._result_reporters

    def coverage_reporters(self):
        """
        Return the list of coverage reporters for this runner.
        """
        return self._coverage_reporters

    def _run_with_browser(self, browser):
        """
        Load all test suite pages in `browser` (a `Browser` instance)
        and returns a `ResultData` instance.

        If an error occurs when retrieving or parsing the page,
        raises a `BrowserError`.
        """

        all_results = []

        # Load each suite page URL
        for url in self._suite_page_server.suite_url_list():

            # Use the browser to load the page and parse the results
            all_results.extend(browser.get_page_results(url))

        return all_results


class SuiteRunnerFactory(object):
    """
    Configure `SuiteRunner` instances.
    """

    # Supported browser names
    SUPPORTED_BROWSERS = ['chrome', 'firefox', 'phantomjs']

    def __init__(
        self, desc_class=SuiteDescription,
        renderer_class=SuiteRenderer,
        server_class=SuitePageServer,
        console_result_class=ConsoleResultReporter,
        xunit_result_class=XUnitResultReporter,
        html_coverage_class=HtmlCoverageReporter,
        xml_coverage_class=XmlCoverageReporter,
        browser_class=Browser
    ):
        """
        Configure the factory to use the provided classes.
        You should only ever override the defaults when testing.
        """
        self._desc_class = desc_class
        self._renderer_class = renderer_class
        self._server_class = server_class
        self._console_result_class = console_result_class
        self._xunit_result_class = xunit_result_class
        self._html_coverage_class = html_coverage_class
        self._xml_coverage_class = xml_coverage_class
        self._browser_class = browser_class

    def build_runner(
        self, suite_path_list, browser_names,
        xunit_path, coverage_xml_path,
        coverage_html_path, timeout_sec
    ):
        """
        Configure `SuiteRunner` instances for each suite description.
        Each `SuiteRunner` will:

        * Start instances of each browser listed in `browser_names`.
        `browser_names` is a list of browser names such as "chrome",
        "firefox", and "phantomjs".

        * Run the test suites described in
          `suite_path_list` (list of paths to suite description files)

        * Generate a console and XUnit report of test results.
        The XUnit report will be written to `xunit_path` if specified.

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

        # Create the test result reporters
        # Always create a console reporter
        # Create the XUnit reporter only if a path is specified
        result_reporters = [self._console_result_class(sys.stdout)]
        if xunit_path is not None:
            xunit_file = open(xunit_path, 'w')
            xunit_reporter = self._xunit_result_class(xunit_file)
            result_reporters.append(xunit_reporter)

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
        runner = SuiteRunner(
            browsers, server,
            result_reporters, coverage_reporters
        )

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
