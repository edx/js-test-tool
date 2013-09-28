from unittest import TestCase
from js_test_tool.result_report \
    import ResultData, ConsoleResultReporter, XUnitResultReporter
from StringIO import StringIO


import logging
LOGGER = logging.getLogger(__name__)


class ResultDataTest(TestCase):

    def test_add_results(self):

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
            'num_passed': num_passed
        }


class ConsoleResultReporterTest(TestCase):
    pass


class XUnitResultReporterTest(TestCase):
    pass
