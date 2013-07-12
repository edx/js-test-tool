from unittest import TestCase
import mock
from textwrap import dedent
import os.path
from js_test_tool.runner import SuiteRunner, SuiteRunnerFactory, \
    UnknownBrowserError
from js_test_tool.browser import Browser
from js_test_tool.suite import SuiteDescription, SuiteRenderer
from js_test_tool.suite_server import SuitePageServer
from js_test_tool.coverage import CoverageData
from js_test_tool.coverage_report import HtmlCoverageReporter, XmlCoverageReporter
from js_test_tool.tests.helpers import TempWorkspaceTestCase


class SuiteRunnerTest(TestCase):

    def setUp(self):

        # Create mock dependencies
        self.mock_browser = mock.MagicMock(Browser)
        self.mock_page_server = mock.MagicMock(SuitePageServer)
        self.mock_coverage_reporters = [mock.MagicMock(HtmlCoverageReporter),
                                        mock.MagicMock(XmlCoverageReporter)]

        # Configure the page server to provide a suite page URL
        self._set_suite_urls(['http://127.0.0.1:8080/suite/0'])

        # Configure the page server to provide coverage data
        self.mock_coverage_data = mock.MagicMock(CoverageData)
        self.mock_page_server.all_coverage_data.return_value = self.mock_coverage_data

        # Start with no test results
        self.mock_browser.get_page_results.return_value = []
        self.mock_browser.name.return_value = 'chrome'

        # Create a SuiteRunner instance
        self.runner = SuiteRunner([self.mock_browser],
                                  self.mock_page_server,
                                  self.mock_coverage_reporters)

    def test_page_server_started_and_stopped(self):

        # Load all the suite pages
        self.runner.run()

        # Expect that the page server was started/stopped
        self.mock_page_server.start.assert_called_once_with()
        self.mock_page_server.stop.assert_called_once_with()

    def test_loads_all_suite_urls(self):

        # Configure the suite runner to load multiple pages
        suite_urls = ['http://127.0.0.1:8080/suite/{}'.format(suite_num)
                      for suite_num in range(10)]

        self._set_suite_urls(suite_urls)

        # Load all the suite pages
        self.runner.run()

        # Expect that the browser was asked to load all the pages
        loaded_urls = [args[0] for (args, _)
                       in self.mock_browser.get_page_results.call_args_list]

        self.assertEqual(sorted(suite_urls), sorted(loaded_urls))

    def test_all_results_pass(self):

        # All tests pass
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should start at zero',
                                 'pass', '')
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should add to the sum',
                                 'pass', '')
        self._add_browser_result(self.mock_browser,
                                 'Multiplier test', 'it should multiply',
                                 'pass', '')

        # Run the tests
        passed, report = self.runner.run()

        # Check that we get the expected report
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome
        -----------------------
        Adder test: it should start at zero [pass]
        Adder test: it should add to the sum [pass]
        Multiplier test: it should multiply [pass]

        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  3
        =======================
        """)

        self.assertTrue(passed)
        self._assert_reports_equal(report, expected_report)

    def test_some_results_fail(self):

        # Some tests fail
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should start at zero',
                                 'pass', '')
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should add to the sum',
                                 'fail', 'Stack trace\nCan go here')
        self._add_browser_result(self.mock_browser,
                                 'Multiplier test', 'it should multiply',
                                 'pass', '')

        # Run the tests
        passed, report = self.runner.run()

        # Check that we get the expected report
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome
        -----------------------
        Adder test: it should start at zero [pass]
        Adder test: it should add to the sum [fail]
            Stack trace
            Can go here

        Multiplier test: it should multiply [pass]

        -----------------------
        Failed:  1
        Error:   0
        Skipped: 0
        Passed:  2
        =======================
        """)

        self.assertFalse(passed)
        self._assert_reports_equal(report, expected_report)

    def test_all_results_fail(self):

        # All tests fail
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should start at zero',
                                 'fail', 'Desc')
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should add to the sum',
                                 'fail', 'Desc')
        self._add_browser_result(self.mock_browser,
                                 'Multiplier test', 'it should multiply',
                                 'fail', 'Desc')

        # Run the tests
        passed, report = self.runner.run()

        # Check that we get the expected report
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome
        -----------------------
        Adder test: it should start at zero [fail]
            Desc

        Adder test: it should add to the sum [fail]
            Desc

        Multiplier test: it should multiply [fail]
            Desc


        -----------------------
        Failed:  3
        Error:   0
        Skipped: 0
        Passed:  0
        =======================
        """)

        self.assertFalse(passed)
        self._assert_reports_equal(report, expected_report)

    def test_results_error(self):

        # Some tests have error
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should start at zero',
                                 'pass', '')
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should add to the sum',
                                 'error', 'Desc')
        self._add_browser_result(self.mock_browser,
                                 'Multiplier test', 'it should multiply',
                                 'pass', '')

        # Run the tests
        passed, report = self.runner.run()

        # Check that we get the expected report
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome
        -----------------------
        Adder test: it should start at zero [pass]
        Adder test: it should add to the sum [error]
            Desc

        Multiplier test: it should multiply [pass]

        -----------------------
        Failed:  0
        Error:   1
        Skipped: 0
        Passed:  2
        =======================
        """)

        self.assertFalse(passed)
        self._assert_reports_equal(report, expected_report)

    def test_results_skip(self):

        # Some tests skipped
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should start at zero',
                                 'pass', '')
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should add to the sum',
                                 'skip', 'Desc')
        self._add_browser_result(self.mock_browser,
                                 'Multiplier test', 'it should multiply',
                                 'pass', '')

        # Run the tests
        passed, report = self.runner.run()

        # Check that we get the expected report
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome
        -----------------------
        Adder test: it should start at zero [pass]
        Adder test: it should add to the sum [skip]
            Desc

        Multiplier test: it should multiply [pass]

        -----------------------
        Failed:  0
        Error:   0
        Skipped: 1
        Passed:  2
        =======================
        """)

        self.assertTrue(passed)
        self._assert_reports_equal(report, expected_report)

    def test_multiple_suites(self):

        # Configure multiple test suite pages
        suite_urls = ['http://127.0.0.1:8080/suite/0',
                      'http://127.0.0.1:8080/suite/1']

        self._set_suite_urls(suite_urls)

        # Add test results
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should start at zero',
                                 'pass', '')

        # Run the tests
        passed, report = self.runner.run()

        # Because of the way we set up the browser mock, each page
        # loaded will report the same test result.  So we expect
        # that we get duplicate results, one for each URL.
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome
        -----------------------
        Adder test: it should start at zero [pass]
        Adder test: it should start at zero [pass]

        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  2
        =======================
        """)

        self.assertTrue(passed)
        self._assert_reports_equal(report, expected_report)

    def test_no_results(self):

        # Do not add any test results
        # Run the tests
        passed, report = self.runner.run()

        # Expect that we pass by default
        self.assertTrue(passed)

        # Special message in the report
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome
        -----------------------
        Warning: No test results reported.
        =======================
        """)

        self._assert_reports_equal(report, expected_report)

    def test_multiple_browsers_all_pass(self):

        # Configure multiple browsers
        other_browser = mock.MagicMock(Browser)
        other_browser.name.return_value = 'firefox'
        other_browser.get_page_results.return_value = []
        self.runner = SuiteRunner([self.mock_browser, other_browser],
                                  self.mock_page_server,
                                  self.mock_coverage_reporters)

        # Add test results for the Chrome browser
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should start at zero',
                                 'pass', '')
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should add to the sum',
                                 'pass', '')

        # Add test results for the Firefox browser
        self._add_browser_result(other_browser,
                                 'Adder test', 'it should start at zero',
                                 'pass', '')
        self._add_browser_result(other_browser,
                                 'Adder test', 'it should add to the sum',
                                 'pass', '')

        # Run the tests
        passed, report = self.runner.run()

        # Because of the way we set up the browser mock, each page
        # loaded will report the same test result.  So we expect
        # that we get duplicate results, one for each URL.
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome
        -----------------------
        Adder test: it should start at zero [pass]
        Adder test: it should add to the sum [pass]

        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  2
        =======================
        =======================
        Browser: firefox
        -----------------------
        Adder test: it should start at zero [pass]
        Adder test: it should add to the sum [pass]

        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  2
        =======================
        """)

        self.assertTrue(passed)
        self._assert_reports_equal(report, expected_report)

    def test_multiple_browsers_some_fail(self):

        # Configure multiple browsers
        other_browser = mock.MagicMock(Browser)
        other_browser.name.return_value = 'firefox'
        other_browser.get_page_results.return_value = []
        self.runner = SuiteRunner([self.mock_browser, other_browser],
                                  self.mock_page_server,
                                  self.mock_coverage_reporters)

        # Add test results for the Chrome browser
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should start at zero',
                                 'pass', '')
        self._add_browser_result(self.mock_browser,
                                 'Adder test', 'it should add to the sum',
                                 'pass', '')

        # Add test results for the Firefox browser
        self._add_browser_result(other_browser,
                                 'Adder test', 'it should start at zero',
                                 'fail', 'Desc')
        self._add_browser_result(other_browser,
                                 'Adder test', 'it should add to the sum',
                                 'pass', '')

        # Run the tests
        passed, report = self.runner.run()

        # Because of the way we set up the browser mock, each page
        # loaded will report the same test result.  So we expect
        # that we get duplicate results, one for each URL.
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome
        -----------------------
        Adder test: it should start at zero [pass]
        Adder test: it should add to the sum [pass]

        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  2
        =======================
        =======================
        Browser: firefox
        -----------------------
        Adder test: it should start at zero [fail]
            Desc

        Adder test: it should add to the sum [pass]

        -----------------------
        Failed:  1
        Error:   0
        Skipped: 0
        Passed:  1
        =======================
        """)

        self.assertFalse(passed)
        self._assert_reports_equal(report, expected_report)

    def test_write_coverage_reports(self):

        # Trigger the runner to write coverage reports to an output file
        self.runner.write_coverage_reports()

        # Expect that each of the coverage reporters was called
        # with the data returned by the suite page server.
        for reporter in self.mock_coverage_reporters:
            reporter.write_report.assert_called_with(self.mock_coverage_data)

    def _set_suite_urls(self, url_list):
        """
        Configure the suite page server to use each url in `url_list`
        as the suite page.
        """
        self.mock_page_server.suite_url_list.return_value = url_list

    def _add_browser_result(self, mock_browser, group_name, test_name, status, detail):
        """
        Configure `mock_browser` (a `Browser mock) to return the test result:

        `group_name`: name of the test group (e.g. 'Adder tests')
        `test_name`: name of the specific test case
                     (e.g. 'it should start at zero')
        `status`: pass | fail | skip
        `detail`: details of the test case (e.g. a stack trace)
        """

        # Retrieve the current results dict
        results = mock_browser.get_page_results.return_value

        # Append the new result
        results.append({'test_group': group_name,
                        'test_name': test_name,
                        'status': status,
                        'detail': detail})

    def _assert_reports_equal(self, report, expected_report):
        """
        Asserts that two console reports are equal, with
        some extra debugging logging.

        Strips the strings to avoid failures due to starting/ending
        newline issues.
        """
        if report.strip() != expected_report.strip():
            print "Expected: \n\n" + expected_report.strip() + "\n\n"
            print "Actual: \n\n" + report.strip() + "\n\n"
            self.assertEqual(report, expected_report)


class SuiteRunnerFactoryTest(TempWorkspaceTestCase):

    def setUp(self):

        # Call superclass implementation to create the workspace
        super(SuiteRunnerFactoryTest, self).setUp()

        # Create mock instances to be returned by the constructors
        # of each mock class.
        self.mock_desc = mock.MagicMock(SuiteDescription)
        self.mock_renderer = mock.MagicMock(SuiteRenderer)
        self.mock_server = mock.MagicMock(SuitePageServer)
        self.mock_html_coverage = mock.MagicMock(HtmlCoverageReporter)
        self.mock_xml_coverage = mock.MagicMock(XmlCoverageReporter)
        self.mock_browser = mock.MagicMock(Browser)
        self.mock_runner = mock.MagicMock(SuiteRunner)

        # Create mocks for each class that the factory will instantiate
        self.mock_desc_class = mock.MagicMock(return_value=self.mock_desc)
        self.mock_renderer_class = mock.MagicMock(return_value=self.mock_renderer)
        self.mock_server_class = mock.MagicMock(return_value=self.mock_server)
        self.mock_html_coverage_class = mock.MagicMock(return_value=self.mock_html_coverage)
        self.mock_xml_coverage_class = mock.MagicMock(return_value=self.mock_xml_coverage)
        self.mock_browser_class = mock.MagicMock(return_value=self.mock_browser)
        self.mock_runner_class = mock.MagicMock(return_value=self.mock_runner)

        # Create the factory
        self.factory = SuiteRunnerFactory(
            desc_class=self.mock_desc_class,
            renderer_class=self.mock_renderer_class,
            server_class=self.mock_server_class,
            html_coverage_class=self.mock_html_coverage_class,
            xml_coverage_class=self.mock_xml_coverage_class,
            runner_class=self.mock_runner_class,
            browser_class=self.mock_browser_class)

    def test_build_runner(self):

        # Build the runner
        num_suites = 5
        runner, _ = self._build_runner(num_suites)

        # Expect that we get the suite runner instance
        self.assertEqual(runner, self.mock_runner)

    def test_configure_browsers(self):

        # Build a runner and configure it to test using these browsers
        browser_names = ['chrome', 'firefox', 'phantomjs']
        _, browsers = self._build_runner(1, browser_names=browser_names)

        # Expect that the suite runner was configured with the correct browsers
        expected_browsers = [self.mock_browser] * len(browser_names)
        self.assertEqual(browsers, expected_browsers)

        expected_reporters = [self.mock_xml_coverage, self.mock_html_coverage]
        self.mock_runner_class.assert_called_with(expected_browsers,
                                                  self.mock_server,
                                                  expected_reporters)

    def test_configure_server(self):

        # Build the runner
        num_suites = 5
        self._build_runner(num_suites)

        # Expect that the suite page server is correctly configured
        # Because of the way we configure the mocks, each suite description
        # should be identical.  Check that we get the right number.
        suite_desc_list = [self.mock_desc for _ in range(num_suites)]
        self.mock_server_class.assert_called_with(suite_desc_list,
                                                  self.mock_renderer,
                                                  jscover_path=None)

    def test_configure_suite_desc(self):

        # Build the runner
        # Ignore the return value because we are checking for calls the
        # factory makes to our mocks.
        num_suites = 5
        self._build_runner(num_suites)

        # Retrieve all the file paths passed to SuiteDescription constructors
        all_paths = []
        all_root_dirs = []
        for (args, _) in self.mock_desc_class.call_args_list:
            file_handle = args[0]
            all_paths.append(file_handle.name)
            all_root_dirs.append(args[1])

        # Expect that all the paths we passed to the factory were used
        # to instantiate SuiteDescription instances
        for suite_path in self._suite_paths(num_suites):
            self.assertIn(suite_path, all_paths)

        # Expect that all the root dirs are the temp directory
        # (where we created the description file)
        for root_dir in all_root_dirs:
            self.assertEqual(os.path.realpath(root_dir),
                             os.path.realpath(self.temp_dir))

    def test_configure_coverage(self):

        # Build the runner
        # Ignore the return value because we are checking for calls the
        # factory makes to our mocks.
        html_path = 'coverage.html'
        xml_path = 'coverage.xml'
        self._build_runner(1, coverage_html_path=html_path,
                           coverage_xml_path=xml_path)

        # Expect that the coverage reporters were configured correctly
        self.mock_html_coverage_class.assert_called_with(html_path)
        self.mock_xml_coverage_class.assert_called_with(xml_path)

    def test_configure_jscover(self):

        # Set the environment variable to configure
        # JSCover (used by the server to instrument
        # the JavaScript sources for coverage)
        with mock.patch.dict('os.environ', JSCOVER_JAR='jscover.jar'):
            self._build_runner(1, coverage_xml_path='coverage.xml')

        # Expect that the server was configured with the JSCover JAR path
        _, kwargs = self.mock_server_class.call_args
        self.assertEqual(kwargs.get('jscover_path'), 'jscover.jar')

    def test_invalid_browser_names(self):

        with self.assertRaises(UnknownBrowserError):
            self._build_runner(1, browser_names=['chrome', 'invalid'])

    def test_empty_browser_name_list(self):

        with self.assertRaises(ValueError):
            self._build_runner(1, browser_names=[])

    @staticmethod
    def _suite_paths(num_suites):
        """
        Return a list of unique suite file paths of length `num_suites`.
        """
        return ['suite_{}.yaml'.format(num) for num in range(num_suites)]

    def _build_runner(self, num_suites,
                      coverage_xml_path='coverage.xml',
                      coverage_html_path='coverage.html',
                      browser_names=None):
        """
        Build a configured `SuiteRunner` instance
        using the `SuiteRunnerFactory`.

        `num_suites` is the number of suite descriptions to use.

        `coverage_xml_path` and `coverage_html_path` are the paths
        to the coverage reports to be generated.

        `browser_names` is a list of browser names to use in the
        suite descriptions.

        Because we are using mock dependencies that always return the same
        values, each suite runner will be identical,
        and they will all use the same browser dependencies.

        Returns a tuple `(suite_runner, browsers)`.  See
        `SuiteRunnerFactory.build_runner()` for details.
        """

        # Supply default browser names
        if browser_names is None:
            browser_names = ['chrome']

        # Create fake suite description files
        suite_path_list = self._suite_paths(num_suites)

        for path in suite_path_list:
            with open(path, 'w') as file_handle:
                file_handle.write('test file')

        # Build the suite runner instances
        return self.factory.build_runner(suite_path_list,
                                         browser_names,
                                         coverage_xml_path,
                                         coverage_html_path)
