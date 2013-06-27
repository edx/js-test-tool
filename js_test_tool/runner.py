"""
Run test suites and generate coverage reports.
"""
from js_test_tool.suite import SuiteDescription, SuiteRenderer
from js_test_tool.suite_server import SuitePageServer
from js_test_tool.coverage import CoverageReporter
import os.path
import json
from jinja2 import Environment, PackageLoader
from splinter.browser import Browser as SplinterBrowser


# Set up the template environment
TEMPLATE_LOADER = PackageLoader(__package__)
TEMPLATE_ENV = Environment(loader=TEMPLATE_LOADER,
                           trim_blocks=True)


class BrowserError(Exception):
    """
    Error occurred while loading a page in the browser.
    """
    pass


class Browser(object):
    """
    Browser capable of executing JavaScript.
    """

    # Expect the results page to have a <div> with this ID
    # containing the JSON-encoded test results
    RESULTS_DIV_ID = 'js_test_tool_results'

    # Wait time for the DOM to load, in seconds
    TIMEOUT = 10

    def __init__(self, browser_name):
        """
        Initialize the browser to use `browser_name` (e.g. chrome).
        Valid browser names are those defined by the Splinter API:
        http://splinter.cobrateam.info/docs/
        """
        # Store the browser name
        self._name = browser_name

        # Create a browser session 
        try:
            self._splinter_browser = SplinterBrowser(browser_name)
        except:
            raise BrowserError('Could not create a browser instance')

    def get_page_results(self, url):
        """
        Load the test suite page at `url`, parsing and returning the
        results on the page.

        Returns a list of dictionaries of the form:

            {'test_group': TEST_GROUP_NAME,
             'test_name': TEST_NAME,
             'status': pass | fail | error | skip,
             'detail': DETAILS}
        """

        # Load the URL in the browser
        try:
            self._splinter_browser.visit(url)

        except:
            raise BrowserError("Could not load page at '{}'".format(url))

        # Check that we successfully loaded the page
        if not self._splinter_browser.status_code.is_success():
            raise BrowserError("Could not load page at '{}'".format(url))

        # Wait for the DOM to load
        self._splinter_browser.is_element_present_by_id(self.RESULTS_DIV_ID,
                                                        wait_time=self.TIMEOUT)

        # Retrieve the <div> containing the JSON-encoded results
        elements = self._splinter_browser.find_by_id(self.RESULTS_DIV_ID)

        # Raise an error if we can't find the div we expect
        if elements.is_empty():
            msg = "Could not find test results on page at '{}'".format(url)
            raise BrowserError(msg)

        else:
            # Try to JSON-decode the contents of the <div>
            contents = elements.first.html

            try:
                return self._parse_runner_output(contents)

            # Raise an error if invalid JSON
            except ValueError:
                msg = "Could not decode JSON test results: '{}'".format(contents)
                raise BrowserError(msg)

    def name(self):
        """
        Return the name of the browser (e.g. 'chrome')
        """
        return self._name

    def quit(self):
        """
        Quit the browser.  This should be called to clean up
        the browser's resources.
        """
        self._splinter_browser.quit()

    def _parse_runner_output(self, output):
        """
        Parse the output of the test runner in the rendered page.

        Expect `output` to be a JSON-encoded string representing
        a list of dictionaries with keys
        'testGroup', 'testName', 'testStatus', and 'testDetail'

        Returns a list of dictonaries with keys `test_group`, `test_name`,
        `status` and `detail`.

        If the test runner output does not have the expected keys,
        raises a `BrowserError`.
        """

        # We use strict=False to allow for control characters
        # such as newlines.
        results_list = json.loads(output, strict=False)

        final_list = []
        for result_dict in results_list:

            # Munge the keys to make them more Pythonic
            modified_dict = {'test_group': result_dict.get('testGroup'),
                             'test_name': result_dict.get('testName'),
                             'status': result_dict.get('testStatus'),
                             'detail': result_dict.get('testDetail')}

            # Verify that we got all the keys we expected
            for key, value in modified_dict.items():
                if value is None:
                    msg = "Test result is missing required key '{}'".format(key)
                    raise BrowserError(msg)

            # Add the modified dict to the list
            final_list.append(modified_dict)

        return final_list
        

class SuiteRunner(object):
    """
    Run test suites and generate coverage reports.
    """

    # Name of the template used to render the report
    REPORT_TEMPLATE_NAME = 'test_results_report.txt'

    def __init__(self, browser_list, suite_page_server, coverage_reporter):
        """
        Configure the suite runner to retrieve test suite pages
        from `suite_page_server` (`SuitePageServer` instance)
        and collect coverage info using `coverage_reporter`
        (`CoverageReporter` instance).

        Uses each `Browser` instance in `browser_list` to load the test
        suite pages.
        """

        # Store dependencies
        self._browser_list = browser_list
        self._suite_page_server = suite_page_server
        self._coverage_reporter = coverage_reporter

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

        all_reports = []
        all_passed = True

        try:

            for browser in self._browser_list:

                # Run the test suite with one of our browsers
                passed, report_str = self._run_with_browser(browser)

                # If any tests failed, then report that we had failures
                if not passed:
                    all_passed = False

                # Store the report string
                all_reports.append(report_str)

        # Re-raise any exceptions that occur
        except:
            raise

        # Stop the suite page server, freeing up the port
        finally:
            self._suite_page_server.stop()

        # Return whether everything passed and all reports
        return all_passed, '\n\n\n'.join(all_reports)

    def write_coverage_reports(self):
        """
        Generate coverage reports by running each available test suite page.
        The location and format of the reports is controlled by
        how the `CoverageReporter` is configured.

        Note: this may not create any reports if JSCover is not configured
        or no report paths were specified.
        """
        pass

    def _run_with_browser(self, browser):
        """
        Load all test suite pages in `browser` (a `Browser` instance)
        and return a tuple `(passed, report)` where
        `passed` is a bool indicating whether all tests passed,
        and `report` is a unicode string describing the test results.
        """

        all_results = []

        # Load each suite page URL
        for url in self._suite_page_server.suite_url_list():

            # Use the browser to load the page and parse the results
            suite_results = browser.get_page_results(url)

            # Store the results and keep loading pages
            all_results.extend(suite_results)

        # Render the report
        stats = self._result_stats(all_results)
        report_str = self._render_report(browser.name(), all_results, stats)

        # Check whether the tests passed or failed overall
        passed = (stats['num_failed'] + stats['num_error']) == 0

        # Return results
        return passed, report_str

    def _render_report(self, browser_name, suite_result_list, stats_dict):
        """
        Return a unicode string representing the result of running
        the test suite.

        `browser_name` is the name of the browser used to run the tests

        `suite_result_list` is a list of result dictionaries.  See
        `Browser.get_page_results()` for the format of the dictionary items.

        `stats_dict` is a dictionary with keys `num_failed`, `num_error`,
        `num_skipped`, and `num_passed`.
        """

        # Create the template context
        context = {'browser_name': browser_name,
                   'results': suite_result_list,
                   'num_failed': stats_dict['num_failed'],
                   'num_error': stats_dict['num_error'],
                   'num_skipped': stats_dict['num_skipped'],
                   'num_passed': stats_dict['num_passed']}

        # Use a template to render the report string
        template = TEMPLATE_ENV.get_template(self.REPORT_TEMPLATE_NAME)
        return template.render(context)

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

    def __init__(self, 
                 desc_class=SuiteDescription, 
                 renderer_class=SuiteRenderer,
                 server_class=SuitePageServer, 
                 coverage_class=CoverageReporter, 
                 browser_class=Browser,
                 runner_class=SuiteRunner):
        """
        Configure the factory to use the provided classes.
        You should only ever override the defaults when testing.
        """
        self._desc_class = desc_class
        self._renderer_class = renderer_class
        self._server_class = server_class
        self._coverage_class = coverage_class
        self._browser_class = browser_class
        self._runner_class = runner_class

    def build_runners(self, suite_path_list, browser_names, 
                      coverage_xml_path, coverage_html_path):
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
        
        * `suite_runners` is a list of configured `SuiteRunner` instances.
        * `browsers` is a list of browsers used by the runners.
        
        It is the caller's responsibility to call `Browser.quit()` for
        each browser in the list.
        """

        # Load the suite descriptions
        suite_desc_list = self._build_suite_descriptions(suite_path_list)

        # Create a renderer
        renderer = self._renderer_class()

        # Create the coverage reporter
        coverage = self._coverage_class(coverage_html_path, coverage_xml_path)

        # Create the suite page server
        # We re-use the same server across test suites
        server = self._server_class(suite_desc_list, renderer)

        # Create a list of all browsers we will need
        browsers = [self._browser_class(name) for name in browser_names]

        # Create a suite runner for each description
        suite_runner_list = []
        for suite_desc in suite_desc_list:

            # Create the suite runner
            runner = self._runner_class(browsers, server, coverage)
            suite_runner_list.append(runner)

        # Return the list of suite runners and browsers
        return suite_runner_list, browsers

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
