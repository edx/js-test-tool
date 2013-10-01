from unittest import TestCase
from js_test_tool.result_report \
    import ResultData, ConsoleResultReporter, XUnitResultReporter
from js_test_tool.tests.helpers import assert_long_str_equal
from StringIO import StringIO
from textwrap import dedent
from lxml import etree


import logging
LOGGER = logging.getLogger(__name__)


class ResultDataTest(TestCase):

    def testadd_results(self):

        data = ResultData()
        input_results = [self._build_result('pass'), self._build_result('fail')]

        data.add_results('chrome', input_results)
        self.assertEqual(data.browsers(), ['chrome'])
        self.assertEqual(data.test_results('chrome'), input_results)
        self.assertEqual(data.all_passed(), False)

    def test_no_results(self):
        data = ResultData()
        self.assertEqual(data.browsers(), [])
        self.assertEqual(data.test_results('chrome'), [])
        self.assertEqual(data.stats('chrome'), self._build_stats())
        self.assertEqual(data.all_passed(), True)

    def test_all_passed(self):

        # Tuples relating all_passed to input results from each browser.
        cases = [
            (True, [], []),
            (True, [self._build_result('pass')], []),
            (True, [self._build_result('pass'), self._build_result('pass')], []),
            (True, [self._build_result('pass')], [self._build_result('pass')]),
            (False, [self._build_result('fail')], [self._build_result('pass')]),
            (False, [self._build_result('error')], [self._build_result('pass')]),
            (False, [self._build_result('fail')], [self._build_result('fail')]),
            (False, [self._build_result('error')], [self._build_result('fail')]),
            (False, [self._build_result('error')], [self._build_result('error')]),
        ]

        for (expect_passed, chrome_results, firefox_results) in cases:
            data = ResultData()
            data.add_results('chrome', chrome_results)
            data.add_results('firefox', firefox_results)
            self.assertEqual(data.all_passed(), expect_passed)

    def test_stats(self):

        # Tuples relating input results to stats
        cases = [
            ([], self._build_stats()),
            ([self._build_result('error')], self._build_stats(num_error=1)),
            ([self._build_result('fail')], self._build_stats(num_failed=1)),
            ([self._build_result('skip')], self._build_stats(num_skipped=1)),
            ([self._build_result('pass')], self._build_stats(num_passed=1)),
            ([
                self._build_result('error'),
                self._build_result('error'),
                self._build_result('fail'),
                self._build_result('fail'),
                self._build_result('fail'),
                self._build_result('pass'),
                self._build_result('pass'),
                self._build_result('pass'),
                self._build_result('pass'),
                self._build_result('skip'),
                self._build_result('skip'),
                self._build_result('skip'),
                self._build_result('skip'),
                self._build_result('skip'),
            ], self._build_stats(
                num_error=2, num_failed=3,
                num_passed=4, num_skipped=5
            ))
        ]

        for input_results, expected_stats in cases:
            data = ResultData()
            data.add_results('chrome', input_results)
            self.assertEqual(data.stats('chrome'), expected_stats)

    def test_overall_stats(self):

        data = ResultData()
        data.add_results('chrome', [
            self._build_result('error'),
            self._build_result('error'),
            self._build_result('fail'),
            self._build_result('fail'),
            self._build_result('fail'),
            self._build_result('pass'),
            self._build_result('pass'),
            self._build_result('pass'),
            self._build_result('pass'),
            self._build_result('skip'),
            self._build_result('skip'),
            self._build_result('skip'),
            self._build_result('skip'),
            self._build_result('skip'),
        ])

        data.add_results('firefox', [
            self._build_result('error'),
            self._build_result('fail'),
            self._build_result('pass'),
            self._build_result('skip'),
        ])

        # Expect that the overall stats (no browser specified)
        # is the sum of all browser-specific stats
        expected_stats = self._build_stats(
            num_error=3, num_failed=4,
            num_passed=5, num_skipped=6
        )

        self.assertEqual(data.stats(None), expected_stats)

    @staticmethod
    def _build_result(status):
        """
        Return a dict representing a test result with
        the given status.
        """
        return {
            'test_group': 'foo',
            'test_name': 'bar',
            'detail': 'baz',
            'status': status
        }

    @staticmethod
    def _build_stats(num_failed=0, num_error=0, num_skipped=0, num_passed=0):
        """
        Return a dict representing the stats for a browser's test results.
        """
        return {
            'num_failed': num_failed,
            'num_error': num_error,
            'num_skipped': num_skipped,
            'num_passed': num_passed,
            'num_tests': num_failed + num_error + num_skipped + num_passed
        }


class ResultReporterTestCase(TestCase):
    """
    Base class for reporter tests.
    """

    # Subclasses override this to specify the class under test
    REPORTER_CLASS = None

    def setUp(self):
        self.result_data = ResultData()

    def add_result(self, browser_name, group_name, test_name, status, detail):
        """
        Add test results for the browser with `browser_name`.

        `group_name`: name of the test group (e.g. 'Adder tests')
        `test_name`: name of the specific test case
                     (e.g. 'it should start at zero')
        `status`: pass | fail | skip
        `detail`: details of the test case (e.g. a stack trace)
        """
        self.result_data.add_results(
            browser_name, [{
                'test_group': group_name,
                'test_name': test_name,
                'status': status,
                'detail': detail
            }]
        )

    def assert_report(self, expected_report):
        """
        Assert that the console report matches `expected_report`.
        """
        assert_long_str_equal(self.build_report(), expected_report, strip=True)

    def build_report(self):
        """
        Build a report.
        """
        output = StringIO()
        self.REPORTER_CLASS(output).write_report(self.result_data)
        return output.getvalue()


class ConsoleResultReporterTest(ResultReporterTestCase):

    REPORTER_CLASS = ConsoleResultReporter

    def test_all_results_pass(self):

        # All tests pass
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'pass', ''
        )

        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome

        ...


        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  3
        =======================
        """)

        self.assert_report(expected_report)

    def test_some_results_fail(self):

        # Some tests fail
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'fail', 'Stack trace\nCan go here'
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'pass', ''
        )

        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome

        .F.

        Adder test: it should add to the sum [fail]
            Stack trace
            Can go here


        -----------------------
        Failed:  1
        Error:   0
        Skipped: 0
        Passed:  2
        =======================
        """)

        self.assert_report(expected_report)

    def test_all_results_fail(self):

        # All tests fail
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'fail', 'Desc'
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'fail', 'Desc'
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'fail', 'Desc'
        )

        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome

        FFF

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

        self.assert_report(expected_report)

    def test_results_error(self):

        # Some tests have error
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'error', 'Desc'
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'pass', ''
        )

        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome

        .E.

        Adder test: it should add to the sum [error]
            Desc


        -----------------------
        Failed:  0
        Error:   1
        Skipped: 0
        Passed:  2
        =======================
        """)

        self.assert_report(expected_report)

    def test_results_skip(self):

        # Some tests skipped
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'skip', 'Desc'
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'pass', ''
        )

        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome

        .S.

        Adder test: it should add to the sum [skip]
            Desc


        -----------------------
        Failed:  0
        Error:   0
        Skipped: 1
        Passed:  2
        =======================
        """)

        self.assert_report(expected_report)

    def test_no_results(self):

        # Do not add any test results
        self.result_data.add_results('chrome', [])

        # Expect a special message in the report
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome

        Warning: No test results reported.
        =======================
        """)

        self.assert_report(expected_report)

    def test_multiple_browsers_all_pass(self):

        # Add test results for the Chrome browser
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        # Add test results for the Firefox browser
        self.add_result(
            'firefox',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'firefox',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome

        ..


        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  2
        =======================
        =======================
        Browser: firefox

        ..


        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  2
        =======================
        """)

        self.assert_report(expected_report)

    def test_multiple_browsers_some_fail(self):

        # Add test results for the Chrome browser
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        # Add test results for the Firefox browser
        self.add_result(
            'firefox',
            'Adder test', 'it should start at zero',
            'fail', 'Desc'
        )
        self.add_result(
            'firefox',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome

        ..


        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  2
        =======================
        =======================
        Browser: firefox

        F.

        Adder test: it should start at zero [fail]
            Desc


        -----------------------
        Failed:  1
        Error:   0
        Skipped: 0
        Passed:  1
        =======================
        """)

        self.assert_report(expected_report)

    def test_long_results(self):

        # Add many results, all of which pass
        for i in range(167):
            self.add_result(
                'chrome',
                'Foo', 'Bar {0}'.format(i),
                'pass', ''
            )

        # ... lines should be wrapped
        expected_report = dedent("""
        =======================
        JavaScript test results
        =======================
        Browser: chrome

        ................................................................................
        ................................................................................
        .......


        -----------------------
        Failed:  0
        Error:   0
        Skipped: 0
        Passed:  167
        =======================
        """)

        self.assert_report(expected_report)


class XUnitResultReporterTest(ResultReporterTestCase):

    REPORTER_CLASS = XUnitResultReporter

    def test_all_results_pass(self):

        # All tests pass
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'pass', ''
        )

        expected_report = dedent("""
        <?xml version="1.0" ?>
        <testsuite name="javascript" errors="0" failures="0" skipped="0" tests="3">
            <testcase classname="[chrome] Adder test" name="it should start at zero">
            </testcase>
            <testcase classname="[chrome] Adder test" name="it should add to the sum">
            </testcase>
            <testcase classname="[chrome] Multiplier test" name="it should multiply">
            </testcase>
        </testsuite>
        """)

        self.assert_report(expected_report)

    def test_some_results_fail(self):

        # Some tests fail
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'fail', 'Stack trace\nCan go here'
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'pass', ''
        )

        expected_report = dedent("""
        <?xml version="1.0" ?>
        <testsuite name="javascript" errors="0" failures="1" skipped="0" tests="3">
            <testcase classname="[chrome] Adder test" name="it should start at zero">
            </testcase>
            <testcase classname="[chrome] Adder test" name="it should add to the sum">
                <failure type="Failure" message=""><![CDATA[Stack trace
        Can go here]]></failure>
            </testcase>
            <testcase classname="[chrome] Multiplier test" name="it should multiply">
            </testcase>
        </testsuite>
        """)

        self.assert_report(expected_report)

    def test_all_results_fail(self):

        # All tests fail
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'fail', 'Desc'
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'fail', 'Desc'
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'fail', 'Desc'
        )

        expected_report = dedent("""
        <?xml version="1.0" ?>
        <testsuite name="javascript" errors="0" failures="3" skipped="0" tests="3">
            <testcase classname="[chrome] Adder test" name="it should start at zero">
                <failure type="Failure" message=""><![CDATA[Desc]]></failure>
            </testcase>
            <testcase classname="[chrome] Adder test" name="it should add to the sum">
                <failure type="Failure" message=""><![CDATA[Desc]]></failure>
            </testcase>
            <testcase classname="[chrome] Multiplier test" name="it should multiply">
                <failure type="Failure" message=""><![CDATA[Desc]]></failure>
            </testcase>
        </testsuite>
        """)

        self.assert_report(expected_report)

    def test_results_error(self):

        # Some tests have error
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'error', 'Desc'
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'pass', ''
        )

        expected_report = dedent("""
        <?xml version="1.0" ?>
        <testsuite name="javascript" errors="1" failures="0" skipped="0" tests="3">
            <testcase classname="[chrome] Adder test" name="it should start at zero">
            </testcase>
            <testcase classname="[chrome] Adder test" name="it should add to the sum">
                <error type="Error" message=""><![CDATA[Desc]]></error>
            </testcase>
            <testcase classname="[chrome] Multiplier test" name="it should multiply">
            </testcase>
        </testsuite>
        """)

        self.assert_report(expected_report)

    def test_results_skip(self):

        # Some tests skipped
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'skip', 'Desc'
        )
        self.add_result(
            'chrome',
            'Multiplier test', 'it should multiply',
            'pass', ''
        )

        expected_report = dedent("""
        <?xml version="1.0" ?>
        <testsuite name="javascript" errors="0" failures="0" skipped="1" tests="3">
            <testcase classname="[chrome] Adder test" name="it should start at zero">
            </testcase>
            <testcase classname="[chrome] Adder test" name="it should add to the sum">
                <skipped/>
            </testcase>
            <testcase classname="[chrome] Multiplier test" name="it should multiply">
            </testcase>
        </testsuite>
        """)

        self.assert_report(expected_report)

    def test_no_results(self):

        # Do not add any test results
        self.result_data.add_results('chrome', [])

        expected_report = dedent("""
        <?xml version="1.0" ?>
        <testsuite name="javascript" errors="0" failures="0" skipped="0" tests="0">
        </testsuite>
        """)

        self.assert_report(expected_report)

    def test_multiple_browsers_all_pass(self):

        # Add test results for the Chrome browser
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        # Add test results for the Firefox browser
        self.add_result(
            'firefox',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'firefox',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        expected_report = dedent("""
        <?xml version="1.0" ?>
        <testsuite name="javascript" errors="0" failures="0" skipped="0" tests="4">
            <testcase classname="[chrome] Adder test" name="it should start at zero">
            </testcase>
            <testcase classname="[chrome] Adder test" name="it should add to the sum">
            </testcase>
            <testcase classname="[firefox] Adder test" name="it should start at zero">
            </testcase>
            <testcase classname="[firefox] Adder test" name="it should add to the sum">
            </testcase>
        </testsuite>
        """)

        self.assert_report(expected_report)

    def test_multiple_browsers_some_fail(self):

        # Add test results for the Chrome browser
        self.add_result(
            'chrome',
            'Adder test', 'it should start at zero',
            'pass', ''
        )
        self.add_result(
            'chrome',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        # Add test results for the Firefox browser
        self.add_result(
            'firefox',
            'Adder test', 'it should start at zero',
            'fail', 'Desc'
        )
        self.add_result(
            'firefox',
            'Adder test', 'it should add to the sum',
            'pass', ''
        )

        expected_report = dedent("""
        <?xml version="1.0" ?>
        <testsuite name="javascript" errors="0" failures="1" skipped="0" tests="4">
            <testcase classname="[chrome] Adder test" name="it should start at zero">
            </testcase>
            <testcase classname="[chrome] Adder test" name="it should add to the sum">
            </testcase>
            <testcase classname="[firefox] Adder test" name="it should start at zero">
                <failure type="Failure" message=""><![CDATA[Desc]]></failure>
            </testcase>
            <testcase classname="[firefox] Adder test" name="it should add to the sum">
            </testcase>
        </testsuite>
        """)

        self.assert_report(expected_report)

    def test_invalid_xml_in_attribtes(self):

        illegal_chars = '&<>"\''

        # Include invalid XML characters
        self.add_result(illegal_chars, illegal_chars, illegal_chars, 'pass', illegal_chars)

        # Generate a report
        report = self.build_report()

        # Verify that we can parse it as XML
        try:
            etree.fromstring(report)
        except etree.XMLSyntaxError:
            self.fail("Could not parse report as XML:\n\n{}".format(report))
