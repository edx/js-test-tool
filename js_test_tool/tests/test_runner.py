from unittest import TestCase
import mock
from textwrap import dedent
import os.path
import sys
from js_test_tool.runner import SuiteRunner, SuiteRunnerFactory, \
    UnknownBrowserError
from js_test_tool.browser import Browser
from js_test_tool.suite import SuiteDescription, SuiteRenderer
from js_test_tool.suite_server import SuitePageServer, TimeoutError
from js_test_tool.coverage import CoverageData
from js_test_tool.coverage_report import HtmlCoverageReporter, XmlCoverageReporter
from js_test_tool.result_report import ConsoleResultReporter, XUnitResultReporter
from js_test_tool.tests.helpers import TempWorkspaceTestCase, assert_long_str_equal


class SuiteRunnerTest(TestCase):

    def setUp(self):

        # Create mock dependencies
        self.mock_browser = mock.MagicMock(Browser)
        self.mock_page_server = mock.MagicMock(SuitePageServer)
        self.mock_result_reporters = [
            mock.MagicMock(ConsoleResultReporter),
            mock.MagicMock(XUnitResultReporter)
        ]
        self.mock_coverage_reporters = [
            mock.MagicMock(HtmlCoverageReporter),
            mock.MagicMock(XmlCoverageReporter)
        ]

        # Configure the page server to provide a suite page URL
        self._set_suite_urls(['http://127.0.0.1:8080/suite/0'])

        # Configure the page server to provide coverage data
        self.mock_coverage_data = mock.MagicMock(CoverageData)
        self.mock_page_server.all_coverage_data.return_value = self.mock_coverage_data

        # Start with no test results
        self.mock_browser.get_page_results.return_value = []
        self.mock_browser.name.return_value = 'chrome'

        # Create a SuiteRunner instance
        self.runner = SuiteRunner(
            [self.mock_browser],
            self.mock_page_server,
            self.mock_result_reporters,
            self.mock_coverage_reporters
        )

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

    def test_result_data(self):

        other_browser = mock.MagicMock(Browser)
        other_browser.name.return_value = 'firefox'
        other_browser.get_page_results.return_value = []
        self.runner = SuiteRunner(
            [self.mock_browser, other_browser],
            self.mock_page_server,
            self.mock_result_reporters,
            self.mock_coverage_reporters
        )

        # Add test results for the Chrome browser
        self._add_browser_result(
            self.mock_browser,
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self._add_browser_result(
            self.mock_browser,
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        # Add test results for the Firefox browser
        self._add_browser_result(
            other_browser,
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self._add_browser_result(
            other_browser,
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        # Expect that we get the test results back
        # in a `ResultData` object
        result_data = self.runner.run()

        self.assertEqual(
            result_data.browsers(),
            ['chrome', 'firefox']
        )

        expected_results = [
            {
                'test_group': 'Adder test',
                'test_name': 'it should start at zero',
                'status': 'pass', 'detail': ''
            },
            {
                'test_group': 'Adder test',
                'test_name': 'it should add to the sum',
                'status': 'pass', 'detail': ''
            },
        ]

        self.assertEqual(
            result_data.test_results('chrome'),
            expected_results
        )

        self.assertEqual(
            result_data.test_results('firefox'),
            expected_results
        )

    def test_multiple_suites(self):

        # Configure multiple test suite pages
        suite_urls = ['http://127.0.0.1:8080/suite/0',
                      'http://127.0.0.1:8080/suite/1']

        self._set_suite_urls(suite_urls)

        # Add test results
        self._add_browser_result(
            self.mock_browser,
            'Adder test', 'it should start at zero',
            'pass', ''
        )

        # Run the tests
        result_data = self.runner.run()

        # Because of the way we set up the browser mock, each page
        # loaded will report the same test result.  So we expect
        # that we get duplicate results, one for each URL.
        self.assertEqual(result_data.browsers(), ['chrome'])

        expected_results = [
            {
                'test_group': 'Adder test',
                'test_name': 'it should start at zero',
                'status': 'pass', 'detail': ''
            },
            {
                'test_group': 'Adder test',
                'test_name': 'it should start at zero',
                'status': 'pass', 'detail': ''
            },
        ]

        self.assertEqual(
            result_data.test_results('chrome'),
            expected_results
        )

    def test_no_results(self):

        # Do not add any test results
        # Run the tests
        result_data = self.runner.run()

        # Expect that we pass by default
        self.assertTrue(result_data.all_passed())

    def test_generate_result_reports(self):

        # Run the suite to generate test result reports
        result_data = self.runner.run()

        # Check that each of our reporters was called
        for reporter in self.mock_result_reporters:
            reporter.write_report.assert_called_once_with(result_data)

    def test_write_coverage_reports(self):

        # Get the coverage data by running the test suite
        self.runner.run()

        # Trigger the runner to write coverage reports to an output file
        self.runner.write_coverage_reports()

        # Expect that each of the coverage reporters was called
        # with the data returned by the suite page server.
        for reporter in self.mock_coverage_reporters:
            reporter.write_report.assert_called_with(self.mock_coverage_data)

    def test_coverage_timeout(self):

        # Simulate `all_coverage_data()` timeout
        self.mock_page_server.all_coverage_data.side_effect = TimeoutError

        # Load all the suite pages
        # This should not raise an exception
        self.runner.run()

        # Expect that when we write the coverage report
        # nothing happens
        self.runner.write_coverage_reports()

        for reporter in self.mock_coverage_reporters:
            self.assertEqual(reporter.write_report.call_args_list, list())

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
        assert_long_str_equal(report, expected_report, strip=True)


class SuiteRunnerFactoryTest(TempWorkspaceTestCase):

    def setUp(self):

        # Call superclass implementation to create the workspace
        super(SuiteRunnerFactoryTest, self).setUp()

        # Create mock instances to be returned by the constructors
        # of each mock class.
        self.mock_desc = mock.MagicMock(SuiteDescription)
        self.mock_renderer = mock.MagicMock(SuiteRenderer)
        self.mock_server = mock.MagicMock(SuitePageServer)
        self.mock_console_result = mock.MagicMock(ConsoleResultReporter)
        self.mock_xunit_result = mock.MagicMock(XUnitResultReporter)
        self.mock_html_coverage = mock.MagicMock(HtmlCoverageReporter)
        self.mock_xml_coverage = mock.MagicMock(XmlCoverageReporter)
        self.mock_browser = mock.MagicMock(Browser)
        self.mock_runner = mock.MagicMock(SuiteRunner)

        # Create mocks for each class that the factory will instantiate
        self.mock_desc_class = mock.MagicMock(return_value=self.mock_desc)
        self.mock_renderer_class = mock.MagicMock(return_value=self.mock_renderer)
        self.mock_server_class = mock.MagicMock(return_value=self.mock_server)
        self.mock_console_result_class = mock.MagicMock(return_value=self.mock_console_result)
        self.mock_xunit_result_class = mock.MagicMock(return_value=self.mock_xunit_result)
        self.mock_html_coverage_class = mock.MagicMock(return_value=self.mock_html_coverage)
        self.mock_xml_coverage_class = mock.MagicMock(return_value=self.mock_xml_coverage)
        self.mock_browser_class = mock.MagicMock(return_value=self.mock_browser)

        # Create the factory
        self.factory = SuiteRunnerFactory(
            desc_class=self.mock_desc_class,
            renderer_class=self.mock_renderer_class,
            server_class=self.mock_server_class,
            console_result_class=self.mock_console_result_class,
            xunit_result_class=self.mock_xunit_result_class,
            html_coverage_class=self.mock_html_coverage_class,
            xml_coverage_class=self.mock_xml_coverage_class,
            browser_class=self.mock_browser_class
        )

    def test_configure_browsers(self):

        # Build a runner and configure it to test using these browsers
        browser_names = ['chrome', 'firefox', 'phantomjs']
        _, browsers = self._build_runner(1, browser_names=browser_names,
                                         coverage_xml_path='coverage.xml',
                                         coverage_html_path='coverage.html',
                                         timeout_sec=5)

        # Expect that the browsers were created using the provided timeout
        call_args = self.mock_browser_class.call_args_list
        for _, kwargs in call_args:
            timeout_sec = kwargs.get('timeout_sec')
            self.assertEqual(timeout_sec, 5)

        # Expect that the suite runner was configured with the correct browsers
        expected_browsers = [self.mock_browser] * len(browser_names)
        self.assertEqual(browsers, expected_browsers)

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
            self.assertEqual(
                os.path.realpath(root_dir),
                os.path.realpath(self.temp_dir)
            )

    def test_configure_coverage(self):

        # Build the runner
        # Ignore the return value because we are checking for calls the
        # factory makes to our mocks.
        html_path = 'coverage.html'
        xml_path = 'coverage.xml'
        runner, _ = self._build_runner(
            1, coverage_html_path=html_path,
            coverage_xml_path=xml_path
        )

        # Expect that the coverage reporters were configured correctly
        self.mock_html_coverage_class.assert_called_with(html_path)
        self.mock_xml_coverage_class.assert_called_with(xml_path)
        self.assertEqual(
            runner.coverage_reporters(),
            [self.mock_xml_coverage, self.mock_html_coverage]
        )

    def test_configure_jscover(self):

        # Set the environment variable to configure
        # JSCover (used by the server to instrument
        # the JavaScript sources for coverage)
        with mock.patch.dict('os.environ', JSCOVER_JAR='jscover.jar'):
            runner, _ = self._build_runner(1, coverage_xml_path='coverage.xml')

        # Expect that the server was configured with the JSCover JAR path
        _, kwargs = self.mock_server_class.call_args
        self.assertEqual(kwargs.get('jscover_path'), 'jscover.jar')
        self.assertEqual(
            runner.coverage_reporters(),
            [self.mock_xml_coverage]
        )

    def test_configure_coverage_but_no_report(self):

        # Build a runner with no coverage report
        # But DO configure the JSCover environment variable
        with mock.patch.dict('os.environ', JSCOVER_JAR='jscover.jar'):
            runner, _ = self._build_runner(
                1, coverage_xml_path=None,
                coverage_html_path=None
            )

        # Expect that the server was NOT configured to use coverage
        _, kwargs = self.mock_server_class.call_args
        self.assertEqual(kwargs.get('jscover_path'), None)
        self.assertEqual(runner.coverage_reporters(), [])

    def test_configure_console_result(self):
        runner, _ = self._build_runner(1)

        # By default, only a console reporter is configured
        self.assertEqual(
            runner.result_reporters(),
            [self.mock_console_result]
        )

        # The console reporter should be configured
        # to send results to stdout
        self.mock_console_result_class.assert_called_with(sys.stdout)

    def test_configure_xunit_result(self):
        runner, _ = self._build_runner(1, xunit_path='foo.txt')

        # Should configure the runner to generate both
        # console and xunit reports
        self.assertEqual(
            runner.result_reporters(),
            [self.mock_console_result, self.mock_xunit_result]
        )

        # XUnit reporter should be configured with the right path
        args, _ = self.mock_xunit_result_class.call_args
        self.assertTrue(isinstance(args[0], file))
        self.assertEqual(args[0].name, 'foo.txt')

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
                      xunit_path=None,
                      coverage_xml_path=None,
                      coverage_html_path=None,
                      browser_names=None,
                      timeout_sec=None):
        """
        Build a configured `SuiteRunner` instance
        using the `SuiteRunnerFactory`.

        `num_suites` is the number of suite descriptions to use.

        `xunit_path` is the path to the XUnit (XML) test result file.

        `coverage_xml_path` and `coverage_html_path` are the paths
        to the coverage reports to be generated.

        `browser_names` is a list of browser names to use in the
        suite descriptions.

        `timeout_sec` is the number of seconds to wait for a page to load
        before timing out

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
        return self.factory.build_runner(
            suite_path_list, browser_names,
            xunit_path, coverage_xml_path,
            coverage_html_path, timeout_sec
        )
