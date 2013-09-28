"""
Generate report of test results.
"""

from abc import ABCMeta, abstractmethod
from collections import defaultdict
from jinja2 import Environment, PackageLoader


import logging
LOGGER = logging.getLogger(__name__)


# Set up the template environment
TEMPLATE_LOADER = PackageLoader(__package__)
TEMPLATE_ENV = Environment(loader=TEMPLATE_LOADER,
                           trim_blocks=True,
                           lstrip_blocks=True,
                           extensions=['jinja2.ext.with_'])

class ResultData(object):
    """
    Test result data.
    """

    def __init__(self):
        """
        Initialize an empty `ResultData` object.
        """
        self._result_dict = defaultdict(list)

    def add_results(self, browser_name, test_results):
        """
        Add a new set of test results to the `ResultData` object.

        `browser_name` is the name of the browser the tests
        were run under.

        `test_results` is a list of dictionaries of the form:

            {
                'test_group': TEST_GROUP_NAME,
                'test_name': TEST_NAME,
                'status': pass | fail | error | skip,
                'detail': DETAILS
            }
        """
        self._result_dict[browser_name].extend(test_results)

    def browsers(self):
        """
        Return a list of browsers for which we have test results.
        """
        return self._result_dict.keys()

    def test_results(self, browser_name):
        """
        Return test results for the browser named `browser_name`.
        This is a list of dictionaries of the form:

            {
                'test_group': TEST_GROUP_NAME,
                'test_name': TEST_NAME,
                'status': pass | fail | error | skip,
                'detail': DETAILS
            }

        If no results are available for `browser_name`, returns
        an empty list.
        """
        return self._result_dict[browser_name]


    # Dict mapping status values to the counter
    # that should be incremented in the stats dict
    STATS_KEY_MAP = {
        'pass': 'num_passed',
        'fail': 'num_failed',
        'error': 'num_error',
        'skip': 'num_skipped'
    }


    def stats(self, browser_name):
        """
        Return summary statistics for the test results
        for the browser `browser_name`.  This is a dict
        of the form:

            {
                  'num_failed': NUM_FAILED,
                  'num_error': NUM_ERROR,
                  'num_skipped': NUM_SKIPPED,
                  'num_passed': NUM_PASSED
            }

        If there are no test results for the browser,
        returns counts that are all 0.
        """
        stats = {
            'num_failed': 0, 'num_error': 0,
            'num_skipped': 0, 'num_passed': 0
        }

        for test_result in self._result_dict[browser_name]:
            status = test_result.get('status')
            stats_key = self.STATS_KEY_MAP.get(status)

            if stats_key is not None:
                stats[stats_key] += 1

            else:
                msg = "Invalid test result status: '{0}'".format(status)
                LOGGER.warning(msg)

        return stats

    def all_passed(self):
        """
        Return True only if all tests passed in all browsers.
        Otherwise, return False.

        If no results are available, return True.
        """
        for browser_name in self.browsers():
            stats = self.stats(browser_name)

            if (stats.get('num_failed', 0) + stats.get('num_error', 0)) > 0:
                return False

        return True


class BaseResultReporter(object):
    """
    Base class for generating test result reports.
    """

    __metaclass__ = ABCMeta

    def __init__(self, output_file):
        """
        Initialize the reporter to write its
        report to `output_file` (a file-like object).
        """
        self._output_file = output_file

    def write_report(self, test_results):
        """
        Create a report of test results.
        `test_results` is a list of `ResultData` objects.

        Writes the report to the `output_file` configured
        in the initializer
        """
        pass

    @abstractmethod
    def generate_report(self, test_results):
        """
        Return a unicode string representation of
        `test_results`, a list of `ResultData` objects.

        Concrete subclasses implement this.
        """
        pass


class ConsoleResultReporter(BaseResultReporter):
    """
    Generate a report that can be printed to the console.
    """
    pass


class XUnitResultReporter(BaseResultReporter):
    """
    Generate an XUnit XML report.
    """
    pass
