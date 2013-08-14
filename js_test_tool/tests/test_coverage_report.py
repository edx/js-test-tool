from lxml import etree
from textwrap import dedent
import os
from js_test_tool.tests.helpers import TempWorkspaceTestCase
from js_test_tool.coverage import CoverageData
from js_test_tool.coverage_report import HtmlCoverageReporter, XmlCoverageReporter


class BaseCoverageReporterTest(TempWorkspaceTestCase):
    """
    Base test case used to test coverage reporters.
    """

    # Subclasses override this to specify
    # the reporter class under test
    REPORTER_CLASS = None

    # Subclasses override this to specify the expected
    # output file name.
    OUTPUT_FILE_NAME = None

    # Dummy source file data to be created in the workspace
    SRC_FILES = ["root_dir/src1.js", "root_dir/src2.js"]
    SRC_LENGTH = 10
    SRC_CONTENT = "\n".join([u'\u026Eine {}'.format(num)
                             for num in range(1, SRC_LENGTH + 1)])

    def setUp(self):
        """
        Create the reporter and create dummy source files
        in the workspace.
        """

        # Let the superclass set up
        super(BaseCoverageReporterTest, self).setUp()

        # Create the reporter instance
        self.reporter = self.REPORTER_CLASS(self.OUTPUT_FILE_NAME)

        # Create the dummy source data in the temp workspace
        os.mkdir('root_dir')

        for src_path in self.SRC_FILES:
            with open(src_path, "w") as src_file:
                src_file.write(self.SRC_CONTENT.encode('utf8'))

    def assert_output_equals(self, coverage_dict, expected_output):
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

        This assumes that the output is XML-parseable; it will
        parse the XML to ignore whitespace between elements.
        """

        # Munge the dict into the right format
        coverage_dict = {src_path: {'lineData': line_data}
                         for src_path, line_data in coverage_dict.items()}

        # Create a `CoverageData` instance.
        # Since this involves no network or filesystem access
        # we don't bother mocking it.
        data = CoverageData()
        data.load_from_dict('root_dir', '', coverage_dict)

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


class HtmlCoverageReporterTest(BaseCoverageReporterTest):

    REPORTER_CLASS = HtmlCoverageReporter
    OUTPUT_FILE_NAME = "coverage.html"

    HTML_HEADER = dedent("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
        <html>
            <head>
                <meta http-equiv='Content-Type' content='text/html; charset=utf-8' />
                <title>JavaScript Coverage Report</title>
            </head>
            <body>
                <h1>JavaScript Coverage Report</h1>
    """).strip()

    HTML_FOOTER = dedent("""
            </body>
        </html>
    """).strip('\n')

    # Number of spaces to indent the content, to keep
    # it aligned with the header and footer.
    NUM_INDENT_SPACES = 8

    def test_empty_report(self):
        coverage = {}
        expected = self._build_html(u"""
            <p>No coverage information was reported.</p>
        """)

        self.assert_output_equals(coverage, expected)

    def test_one_src_file(self):
        coverage = {'src1.js': [None, 1, 1, 0, None, 1]}
        expected = self._build_html(u"""
            <div class="src">
                <div class="src_desc"><b>Source:</b> src1.js (75.0%)</div>
                <div class="src_display">
                    <table>
                        <tr><td>1</td><td><pre>\u026Eine 1</pre></td></tr>
                        <tr><td>2</td><td class="covered"><pre>\u026Eine 2</pre></td></tr>
                        <tr><td>3</td><td class="covered"><pre>\u026Eine 3</pre></td></tr>
                        <tr><td>4</td><td class="uncovered"><pre>\u026Eine 4</pre></td></tr>
                        <tr><td>5</td><td><pre>\u026Eine 5</pre></td></tr>
                        <tr><td>6</td><td class="covered"><pre>\u026Eine 6</pre></td></tr>
                        <tr><td>7</td><td><pre>\u026Eine 7</pre></td></tr>
                        <tr><td>8</td><td><pre>\u026Eine 8</pre></td></tr>
                        <tr><td>9</td><td><pre>\u026Eine 9</pre></td></tr>
                        <tr><td>10</td><td><pre>\u026Eine 10</pre></td></tr>
                    </table>
                </div>
            </div>
            <div class="summary">
                <h2>Summary</h2>
                <p><b>Total coverage</b>: 75.0%</p>
            </div>
        """)

        self.assert_output_equals(coverage, expected)

    def test_multiple_src_files(self):
        coverage = {'src1.js': [None, 1, 1, 0, None, 1], 'src2.js': [1, 1]}
        expected = self._build_html(u"""
            <div class="src">
                <div class="src_desc"><b>Source:</b> src1.js (75.0%)</div>
                <div class="src_display">
                    <table>
                        <tr><td>1</td><td><pre>\u026Eine 1</pre></td></tr>
                        <tr><td>2</td><td class="covered"><pre>\u026Eine 2</pre></td></tr>
                        <tr><td>3</td><td class="covered"><pre>\u026Eine 3</pre></td></tr>
                        <tr><td>4</td><td class="uncovered"><pre>\u026Eine 4</pre></td></tr>
                        <tr><td>5</td><td><pre>\u026Eine 5</pre></td></tr>
                        <tr><td>6</td><td class="covered"><pre>\u026Eine 6</pre></td></tr>
                        <tr><td>7</td><td><pre>\u026Eine 7</pre></td></tr>
                        <tr><td>8</td><td><pre>\u026Eine 8</pre></td></tr>
                        <tr><td>9</td><td><pre>\u026Eine 9</pre></td></tr>
                        <tr><td>10</td><td><pre>\u026Eine 10</pre></td></tr>
                    </table>
                </div>
            </div>
            <div class="src">
                <div class="src_desc"><b>Source:</b> src2.js (100.0%)</div>
                <div class="src_display">
                    <table>
                        <tr><td>1</td><td class="covered"><pre>\u026Eine 1</pre></td></tr>
                        <tr><td>2</td><td class="covered"><pre>\u026Eine 2</pre></td></tr>
                        <tr><td>3</td><td><pre>\u026Eine 3</pre></td></tr>
                        <tr><td>4</td><td><pre>\u026Eine 4</pre></td></tr>
                        <tr><td>5</td><td><pre>\u026Eine 5</pre></td></tr>
                        <tr><td>6</td><td><pre>\u026Eine 6</pre></td></tr>
                        <tr><td>7</td><td><pre>\u026Eine 7</pre></td></tr>
                        <tr><td>8</td><td><pre>\u026Eine 8</pre></td></tr>
                        <tr><td>9</td><td><pre>\u026Eine 9</pre></td></tr>
                        <tr><td>10</td><td><pre>\u026Eine 10</pre></td></tr>
                    </table>
                </div>
            </div>
            <div class="summary">
                <h2>Summary</h2>
                <p><b>Total coverage</b>: 83.3%</p>
            </div>
        """)

        self.assert_output_equals(coverage, expected)

    def test_src_not_found(self):
        coverage = {'not_found.js': [None, 1, 1, 0, None, 1]}
        expected = self._build_html(u"""
            <div class="src">
                <div class="src_desc"><b>Source:</b> not_found.js (75.0%)</div>
                <div class="src_display">
                    Error: Source file not found.
                </div>
            </div>
            <div class="summary">
                <h2>Summary</h2>
                <p><b>Total coverage</b>: 75.0%</p>
            </div>
        """)

        self.assert_output_equals(coverage, expected)

    def test_full_coverage(self):
        coverage = {'src1.js': [1, 1], 'src2.js': [1, 1]}
        expected = self._build_html(u"""
            <div class="src">
                <div class="src_desc"><b>Source:</b> src1.js (100.0%)</div>
                <div class="src_display">
                    <table>
                        <tr><td>1</td><td class="covered"><pre>\u026Eine 1</pre></td></tr>
                        <tr><td>2</td><td class="covered"><pre>\u026Eine 2</pre></td></tr>
                        <tr><td>3</td><td><pre>\u026Eine 3</pre></td></tr>
                        <tr><td>4</td><td><pre>\u026Eine 4</pre></td></tr>
                        <tr><td>5</td><td><pre>\u026Eine 5</pre></td></tr>
                        <tr><td>6</td><td><pre>\u026Eine 6</pre></td></tr>
                        <tr><td>7</td><td><pre>\u026Eine 7</pre></td></tr>
                        <tr><td>8</td><td><pre>\u026Eine 8</pre></td></tr>
                        <tr><td>9</td><td><pre>\u026Eine 9</pre></td></tr>
                        <tr><td>10</td><td><pre>\u026Eine 10</pre></td></tr>
                    </table>
                </div>
            </div>
            <div class="src">
                <div class="src_desc"><b>Source:</b> src2.js (100.0%)</div>
                <div class="src_display">
                    <table>
                        <tr><td>1</td><td class="covered"><pre>\u026Eine 1</pre></td></tr>
                        <tr><td>2</td><td class="covered"><pre>\u026Eine 2</pre></td></tr>
                        <tr><td>3</td><td><pre>\u026Eine 3</pre></td></tr>
                        <tr><td>4</td><td><pre>\u026Eine 4</pre></td></tr>
                        <tr><td>5</td><td><pre>\u026Eine 5</pre></td></tr>
                        <tr><td>6</td><td><pre>\u026Eine 6</pre></td></tr>
                        <tr><td>7</td><td><pre>\u026Eine 7</pre></td></tr>
                        <tr><td>8</td><td><pre>\u026Eine 8</pre></td></tr>
                        <tr><td>9</td><td><pre>\u026Eine 9</pre></td></tr>
                        <tr><td>10</td><td><pre>\u026Eine 10</pre></td></tr>
                    </table>
                </div>
            </div>
            <div class="summary">
                <h2>Summary</h2>
                <p><b>Total coverage</b>: 100.0%</p>
            </div>
        """)

        self.assert_output_equals(coverage, expected)

    def test_no_coverage(self):
        coverage = {'src1.js': [0, 0], 'src2.js': [0, 0]}
        expected = self._build_html(u"""
            <div class="src">
                <div class="src_desc"><b>Source:</b> src1.js (0.0%)</div>
                <div class="src_display">
                    <table>
                        <tr><td>1</td><td class="uncovered"><pre>\u026Eine 1</pre></td></tr>
                        <tr><td>2</td><td class="uncovered"><pre>\u026Eine 2</pre></td></tr>
                        <tr><td>3</td><td><pre>\u026Eine 3</pre></td></tr>
                        <tr><td>4</td><td><pre>\u026Eine 4</pre></td></tr>
                        <tr><td>5</td><td><pre>\u026Eine 5</pre></td></tr>
                        <tr><td>6</td><td><pre>\u026Eine 6</pre></td></tr>
                        <tr><td>7</td><td><pre>\u026Eine 7</pre></td></tr>
                        <tr><td>8</td><td><pre>\u026Eine 8</pre></td></tr>
                        <tr><td>9</td><td><pre>\u026Eine 9</pre></td></tr>
                        <tr><td>10</td><td><pre>\u026Eine 10</pre></td></tr>
                    </table>
                </div>
            </div>
            <div class="src">
                <div class="src_desc"><b>Source:</b> src2.js (0.0%)</div>
                <div class="src_display">
                    <table>
                        <tr><td>1</td><td class="uncovered"><pre>\u026Eine 1</pre></td></tr>
                        <tr><td>2</td><td class="uncovered"><pre>\u026Eine 2</pre></td></tr>
                        <tr><td>3</td><td><pre>\u026Eine 3</pre></td></tr>
                        <tr><td>4</td><td><pre>\u026Eine 4</pre></td></tr>
                        <tr><td>5</td><td><pre>\u026Eine 5</pre></td></tr>
                        <tr><td>6</td><td><pre>\u026Eine 6</pre></td></tr>
                        <tr><td>7</td><td><pre>\u026Eine 7</pre></td></tr>
                        <tr><td>8</td><td><pre>\u026Eine 8</pre></td></tr>
                        <tr><td>9</td><td><pre>\u026Eine 9</pre></td></tr>
                        <tr><td>10</td><td><pre>\u026Eine 10</pre></td></tr>
                    </table>
                </div>
            </div>
            <div class="summary">
                <h2>Summary</h2>
                <p><b>Total coverage</b>: 0.0%</p>
            </div>
        """)

        self.assert_output_equals(coverage, expected)

    def _build_html(self, content):
        """
        Add a header/footer before/after `content` (a string)
        and return the result.

        Whitespace is stripped at the start and end of `content`.
        """
        # Fix the indentation of the content
        no_indent = dedent(content).strip()
        content = "\n".join([(" " * self.NUM_INDENT_SPACES) + line
                             for line in no_indent.split('\n')])

        # Add the header and footer
        return u"{}\n{}\n{}".format(self.HTML_HEADER, content, self.HTML_FOOTER)


class XmlCoverageReporterTest(BaseCoverageReporterTest):

    REPORTER_CLASS = XmlCoverageReporter
    OUTPUT_FILE_NAME = "coverage.xml"

    def test_empty_report(self):

        coverage = {}
        expected = dedent("""
            <?xml version="1.0" ?>
            <!DOCTYPE coverage
              SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
            <packages>
            </packages>
        """).strip()

        self.assert_output_equals(coverage, expected)

    def test_one_src_file(self):

        coverage = {'src1.js': [None, 1, 1, 0, None, 1]}
        expected = dedent("""
            <?xml version="1.0" ?>
            <!DOCTYPE coverage
              SYSTEM 'http://cobertura.sourceforge.net/xml/coverage-03.dtd'>
            <packages>
                <package branch-rate="0" complexity="0" line-rate="0.75" name="">
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
                </package>
            </packages>
        """).strip()

        self.assert_output_equals(coverage, expected)

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

        self.assert_output_equals(coverage, expected)

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

        self.assert_output_equals(coverage, expected)

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

        self.assert_output_equals(coverage, expected)
