"""
Report coverage information for JavaScript.
"""


class CoverageReporter(object):
    """
    Generate coverage reports for JavaScript.
    """

    def __init__(self, html_report_path, xml_report_path):
        """
        Initialize the reporter to write reports to `html_report_path`
        and `xml_report_path`.

        If either path is `None`, that report will not be generated.
        """
        pass

    def generate_reports(self, url_list):
        """
        Write the HTML and XML coverage reports to the paths
        specified in the constructor.  Overwrites files if they already
        exist.

        Collects JavaScript coverage for the JS included in each url
        specified in `url_list`.

        If JSCover is not configured correctly or no paths were
        specified, this will do nothing.
        """
        pass
