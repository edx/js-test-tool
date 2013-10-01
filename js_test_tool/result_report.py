"""
Generate report of test results.
"""

from abc import ABCMeta, abstractmethod
from collections import defaultdict
from jinja2 import Environment, PackageLoader
from xml.sax.saxutils import escape, quoteattr


import logging
LOGGER = logging.getLogger(__name__)


# Set up the template environment
TEMPLATE_LOADER = PackageLoader(__package__)
TEMPLATE_ENV = Environment(
    loader=TEMPLATE_LOADER,
    trim_blocks=True,
    lstrip_blocks=True,
    extensions=['jinja2.ext.with_']
)


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
                  'num_tests': NUM_TESTS
            }

        `NUM_TESTS` is the total number of tests (the sum
        of failed, errored, skipped, and passed tests).

        If there are no test results for the browser,
        returns counts that are all 0.

        If `browser_name` is `None`, returns aggregate
        results for all browers.
        """
        stats = {
            'num_failed': 0, 'num_error': 0,
            'num_skipped': 0, 'num_passed': 0,
            'num_tests': 0
        }

        # If no browser name specified, aggregate results
        # across all browsers.
        if browser_name is None:
            browser_list = self.browsers()

        # Otherwise, get results only for the specified browser
        else:
            browser_list = [browser_name]

        for browser in browser_list:
            for test_result in self._result_dict[browser]:
                status = test_result.get('status')
                stats_key = self.STATS_KEY_MAP.get(status)

                if stats_key is not None:
                    stats[stats_key] += 1
                    stats['num_tests'] += 1

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

    def write_report(self, result_data):
        """
        Create a report of test results.
        `result_data` is a `ResultData` object.

        Writes the report to the `output_file` configured
        in the initializer
        """
        report_str = self.generate_report(result_data)
        self._output_file.write(report_str)

    @abstractmethod
    def generate_report(self, results_data):
        """
        Return a unicode string representation of
        `results_data`, a `ResultData` object.

        Concrete subclasses implement this.
        """
        pass


class ConsoleResultReporter(BaseResultReporter):
    """
    Generate a report that can be printed to the console.
    """
    REPORT_TEMPLATE_NAME = 'console_report.txt'

    def generate_report(self, results_data):
        """
        See base class.
        """
        context_dict = {
            'browser_results': [
                {
                    'browser_name': browser_name,
                    'test_results': results_data.test_results(browser_name),
                    'stats': results_data.stats(browser_name)
                } for browser_name in results_data.browsers()
            ],
            'stats': results_data.stats(None),
            'all_passed': results_data.all_passed()
        }

        template = TEMPLATE_ENV.get_template(self.REPORT_TEMPLATE_NAME)
        return template.render(context_dict)


class XUnitResultReporter(BaseResultReporter):
    """
    Generate an XUnit XML report.
    """
    REPORT_TEMPLATE_NAME = 'xunit_report.txt'

    def generate_report(self, results_data):
        """
        See base class.
        """
        context_dict = {
            'browser_results': [
                {
                    'browser_name': browser_name,
                    'test_results': results_data.test_results(browser_name),
                    'stats': results_data.stats(browser_name)
                } for browser_name in results_data.browsers()
            ],
            'stats': results_data.stats(None),
            'all_passed': results_data.all_passed()
        }

        template = TEMPLATE_ENV.get_template(self.REPORT_TEMPLATE_NAME)
        return template.render(self._sanitize_context_dict(context_dict))

    def _sanitize_context_dict(self, context):
        """
        Sanitize the strings in the context dict for XML.
        """
        for browser_dict in context.get('browser_results', []):
            browser_dict['browser_name'] = self._sanitize_attr(browser_dict['browser_name'])

            for result_dict in browser_dict.get('test_results', []):
                result_dict['test_group'] = self._sanitize_attr(result_dict['test_group'])
                result_dict['test_name'] = self._sanitize_attr(result_dict['test_name'])

        return context

    def _sanitize_attr(self, string):
        """
        Replace characters that can cause XML parse errors in attributes.
        """
        # Escape <, &, and > to corresponding entity references
        # Escape quotes (for attributes)
        return escape(string, {'"': '&quot;', "'": "&quot;"})
