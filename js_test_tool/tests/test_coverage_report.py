import unittest
import mock
from textwrap import dedent
from lxml import etree
from js_test_tool.tests.helpers import TempWorkspaceTestCase
from js_test_tool.coverage import CoverageData
from js_test_tool.coverage_report import HtmlCoverageReporter, XmlCoverageReporter


class HtmlCoverageReporterTest(unittest.TestCase):
    pass


class XmlCoverageReporterTest(TempWorkspaceTestCase):

    OUTPUT_FILE_NAME = "coverage.xml"

    def setUp(self):

        # Let the superclass set up
        super(XmlCoverageReporterTest, self).setUp()

        # Create the reporter instance
        self.reporter = XmlCoverageReporter(self.OUTPUT_FILE_NAME)

    def test_empty_report(self):

        coverage = {}
        expected = dedent("""
        <?xml version="1.0" ?>
        <!DOCTYPE coverage
          SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
        <packages>
        </packages>
        """).strip()

        self._assert_output_equals(coverage, expected)

    def test_one_src_file(self):

        coverage = {'src.js': [None, 1, 1, 0, None, 1]}
        expected = dedent("""
            <?xml version="1.0" ?>
            <!DOCTYPE coverage
              SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
            <packages>
                <package branch-rate="0" complexity="0" line-rate="0.75" name="">
                    <class branch-rate="0" complexity="0"
                           filename="src.js" line-rate="0.75"
                           name="src.js">
                        <methods />
                        <lines>
                            <line hits="1" number="1" />
                            <line hits="1" number="2" />
                            <line hits="0" number="3" />
                            <line hits="1" number="5" />
                        </lines>
                    </class>
                </package>
            </packages>
        """).strip()

        self._assert_output_equals(coverage, expected)

    def test_multiple_src_files(self):
        coverage = {'src1.js': [None, 1, 1, 0, None, 1], 'src2.js': [1, 1]}
        expected = dedent("""
            <?xml version="1.0" ?>
            <!DOCTYPE coverage
              SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
            <packages>
                <package branch-rate="0" complexity="0" line-rate="0.8333" name="">
                    <class branch-rate="0" complexity="0"
                           filename="src1.js" line-rate="0.75"
                           name="src1.js">
                        <methods />
                        <lines>
                            <line hits="1" number="1" />
                            <line hits="1" number="2" />
                            <line hits="0" number="3" />
                            <line hits="1" number="5" />
                        </lines>
                    </class>
                    <class branch-rate="0" complexity="0"
                           filename="src2.js" line-rate="1.0"
                           name="src2.js">
                        <methods />
                        <lines>
                            <line hits="1" number="0" />
                            <line hits="1" number="1" />
                        </lines>
                    </class>
                </package>
            </packages>
        """).strip()

        self._assert_output_equals(coverage, expected)

    def test_full_coverage(self):
        coverage = {'src1.js': [1, 1], 'src2.js': [1, 1]}
        expected = dedent("""
            <?xml version="1.0" ?>
            <!DOCTYPE coverage
              SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
            <packages>
                <package branch-rate="0" complexity="0" line-rate="1.0" name="">
                    <class branch-rate="0" complexity="0"
                           filename="src1.js" line-rate="1.0"
                           name="src1.js">
                        <methods />
                        <lines>
                            <line hits="1" number="0" />
                            <line hits="1" number="1" />
                        </lines>
                    </class>
                    <class branch-rate="0" complexity="0"
                           filename="src2.js" line-rate="1.0"
                           name="src2.js">
                        <methods />
                        <lines>
                            <line hits="1" number="0" />
                            <line hits="1" number="1" />
                        </lines>
                    </class>
                </package>
            </packages>
        """).strip()

        self._assert_output_equals(coverage, expected)

    def test_no_coverage(self):
        coverage = {'src1.js': [0, 0], 'src2.js': [0, 0]}
        expected = dedent("""
            <?xml version="1.0" ?>
            <!DOCTYPE coverage
              SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
            <packages>
                <package branch-rate="0" complexity="0" line-rate="0.0" name="">
                    <class branch-rate="0" complexity="0"
                           filename="src1.js" line-rate="0.0"
                           name="src1.js">
                        <methods />
                        <lines>
                            <line hits="0" number="0" />
                            <line hits="0" number="1" />
                        </lines>
                    </class>
                    <class branch-rate="0" complexity="0"
                           filename="src2.js" line-rate="0.0"
                           name="src2.js">
                        <methods />
                        <lines>
                            <line hits="0" number="0" />
                            <line hits="0" number="1" />
                        </lines>
                    </class>
                </package>
            </packages>
        """).strip()

        self._assert_output_equals(coverage, expected)

    def _assert_output_equals(self, coverage_dict, expected_output):
        """
        Asserts that the output from the coverage reporter
        is equal to `expected_output`.

        `coverage_dict` is a dict of the form:
            
            { SRC_PATH: [ COVER_INFO, ...]

        where COVER_INFO is either:

        * None: no coverage info
        * integer: number of times line was hit

        for example:

            { 'src.js': [ 1, 0, None, 1]}
        """

        # Munge the dict into the right format
        coverage_dict = {src_path: {'lineData': line_data}
                         for src_path, line_data in coverage_dict.items()}

        # Create a `CoverageData` instance.
        # Since this involves no network or filesystem access
        # we don't bother mocking it.
        data = CoverageData()
        data.load_from_dict('root_dir', coverage_dict)

        # Write the report to the output file in the temp directory
        self.reporter.write_report(data)

        # Read the data back in from the output file
        with open(self.OUTPUT_FILE_NAME) as output_file:
            output_str = output_file.read()

        # Run the reports through the XML parser to normalize format
        output_str = etree.tostring(etree.fromstring(output_str))
        expected_output = etree.tostring(etree.fromstring(expected_output))

        # Check that the the output matches what we expect
        self.assertEqual(output_str, expected_output)
