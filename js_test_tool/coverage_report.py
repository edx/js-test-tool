"""
Report coverage information in different formats.
"""

from abc import ABCMeta, abstractmethod
from jinja2 import Environment, PackageLoader

# Set up the template environment
TEMPLATE_LOADER = PackageLoader(__package__)
TEMPLATE_ENV = Environment(loader=TEMPLATE_LOADER,
                           trim_blocks=True,
                           lstrip_blocks=True)


class BaseCoverageReporter(object):
    """
    Generate coverage reports for JavaScript.
    """

    __metaclass__ = ABCMeta

    def __init__(self, output_path):
        """
        Initialize the reporter to write reports to `output_path`.
        """
        self._output_path = output_path

    def write_report(self, coverage_data):
        """
        Write the report to the path specified in the constructor.
        Overwrites files if they already exist.

        `coverage_data` is a `CoverageData` instance.

        Delegates to the concrete subclass's `generate_report()` method.
        """

        # Generate the report (delegate to subclass)
        report_str = self.generate_report(coverage_data)

        # Write the report to the output file
        with open(self._output_path, "w") as output_file:
            output_file.write(report_str)

    @abstractmethod
    def generate_report(self, coverage_data):
        """
        Return a unicode string report for `coverage_data`.
        """
        pass


class TemplateCoverageReporter(BaseCoverageReporter):
    """
    Generate a report using a template.
    """

    # Subclasses override this variable to specify
    # the template to use.
    TEMPLATE_NAME = None

    def generate_report(self, coverage_data):
        """
        See base class docstring.
        """

        if self.TEMPLATE_NAME is not None:

            # Create the context for the template
            template_context = self._build_context(coverage_data)

            # Render the template
            template = TEMPLATE_ENV.get_template(self.TEMPLATE_NAME)
            return template.render(template_context)

        else:
            return u""

    def _build_context(self, coverage_data):
        """
        Build the context dict to pass to the template, using
        `coverage_data` (a `CoverageData` instance).

        The context dict has the form:

            {
                'total_coverage': TOTAL_COVERAGE (decimal),
                'sources': {
                    SRC_PATH: { 
                        'src_coverage': SRC_COVERAGE (decimal),
                        'lines': {
                            LINE_NUM: True | False
                        }
                    }
                }
            }
        """
        return {
            'total_coverage': coverage_data.total_coverage(),
            'sources': {
                coverage_data.rel_src_path(full_path): {
                   'src_coverage': coverage_data.coverage_for_src(full_path),
                   'lines': coverage_data.line_dict_for_src(full_path)
                } for full_path in coverage_data.src_list()
            }
        }


class HtmlCoverageReporter(TemplateCoverageReporter):
    """
    Generate an HTML coverage report.
    """

    TEMPLATE_NAME = "coverage_html_report.html"


class XmlCoverageReporter(TemplateCoverageReporter):
    """
    Generate an XML coverage report.
    """

    TEMPLATE_NAME = "coverage_xml_report.xml"
