"""
Run test suites and generate coverage reports.
"""
from js_test_tool.suite import SuiteDescription, SuiteRenderer
from js_test_tool.suite_server import SuitePageServer
from js_test_tool.coverage import CoverageReporter


class SuiteRunner(object):
    """
    Run test suites and generate coverage reports.
    """

    def __init__(self, suite_page_server, coverage_reporter):
        """
        Configure the suite runner to retrieve test suite pages
        from `suite_page_server` (`SuitePageServer` instance)
        and collect coverage info using `coverage_reporter`
        (`CoverageReporter` instance).
        """
        pass

    def test_report(self):
        """
        Execute each available test suite page and record whether
        each test passed/failed.  Return test results as a unicode string.
        """
        pass

    def write_coverage_reports(self):
        """
        Generate coverage reports by running each available test suite page.
        The location and format of the reports is controlled by
        how the `CoverageReporter` is configured.

        Note: this may not create any reports if JSCover is not configured
        or no report paths were specified.
        """
        pass


class SuiteRunnerFactory(object):
    """
    Configure `SuiteRunner` instances.
    """

    def __init__(self, 
                 desc_class=SuiteDescription, 
                 renderer_class=SuiteRenderer,
                 server_class=SuitePageServer, 
                 coverage_class=CoverageReporter, 
                 runner_class=SuiteRunner):
        """
        Configure the factory to use the provided classes.
        You should only ever override the defaults when testing.
        """
        pass

    def build(self, suite_desc_file, coverage_xml_path, coverage_html_path):
        """
        Configure a `SuiteRunner` instance to:
        
        * Run the test suite described in 
          `suite_desc_file` (a file-like object).

        * Write coverage reports to `coverage_xml_path` (Cobertura XML format)
          and `coverage_html_path` (HTML).

        If the coverage paths are `None`, that report will not be generated.

        Returns the configured `SuiteRunner` instance.
        """
        pass
