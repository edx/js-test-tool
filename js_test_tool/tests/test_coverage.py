import unittest
import mock
import requests
import re
from textwrap import dedent
from js_test_tool.coverage import SrcInstrumenter, SrcInstrumenterError, CoverageData


class SrcInstrumenterTest(unittest.TestCase):

    TEST_ROOT_DIR = '/tmp/test'
    TEST_TOOL_PATH = '/usr/bin/jscover'
    TEST_INSTRUMENTED_SRC = 'instrumented JS src'

    ADDRESS_IN_USE_ERROR = dedent("""
        Exception in thread "main" java.lang.RuntimeException: java.net.BindException: Address already in use
            at jscover.Main.runServer(Main.java:470)
            at jscover.Main.runMain(Main.java:420)
            at jscover.Main.main(Main.java:411)
        Caused by: java.net.BindException: Address already in use
            at java.net.PlainSocketImpl.socketBind(Native Method)
            at java.net.PlainSocketImpl.bind(PlainSocketImpl.java:383)
            at java.net.ServerSocket.bind(ServerSocket.java:328)
            at java.net.ServerSocket.<init>(ServerSocket.java:194)
            at java.net.ServerSocket.<init>(ServerSocket.java:106)
            at jscover.server.WebDaemon.start(WebDaemon.java:356)
            at jscover.Main.runServer(Main.java:468)
            ... 2 more
    """).strip()

    def setUp(self):

        # Mock the subprocess module
        self.subprocess = mock.Mock()
        self.process = mock.Mock()
        self.subprocess.Popen = mock.Mock(return_value=self.process)
        self.process.communicate = mock.Mock()

        # Configure the tool to return non-error
        self._configure_tool()

        # Mock the requests module
        self.requests = mock.Mock()

        # Set wait between attempts to very short to speed up the tests
        # Since we are using mocks, this shouldn't be an issue
        self._old_wait_between_attempts = SrcInstrumenter.WAIT_BETWEEN_ATTEMPTS
        SrcInstrumenter.WAIT_BETWEEN_ATTEMPTS = 0.01

        # Create, but do not start, the service
        self.instrumenter = SrcInstrumenter(self.TEST_ROOT_DIR,
                                            tool_path=self.TEST_TOOL_PATH,
                                            subprocess_module=self.subprocess,
                                            requests_module=self.requests)

    def tearDown(self):

        # Reset the old wait time between attempts
        SrcInstrumenter.WAIT_BETWEEN_ATTEMPTS = self._old_wait_between_attempts

    def test_start_service(self):

        # Start the service
        self.instrumenter.start()

        # Expect that the service process was started
        self._assert_jscover_called(self.TEST_TOOL_PATH,
                                    self.TEST_ROOT_DIR)

        # Stop the instrumenter service
        self.instrumenter.stop()

        # Expect that the service process was terminated
        self.process.terminate.assert_called_once_with()

    def test_get_instrumented_src(self):

        # Configure the `requests` HTTP library to return a
        # pre-defined response
        self._configure_http_response(200, self.TEST_INSTRUMENTED_SRC)

        # Try to instrument a source
        result = self.instrumenter.instrumented_src('src.js')

        # Expect that the type we get back is unicode
        self.assertTrue(isinstance(result, unicode))

        # Expect that we get the right source back
        self.assertEqual(result, self.TEST_INSTRUMENTED_SRC)

        # Expect that a GET request was made at the correct URL
        args, _ = self.requests.get.call_args
        self.assertEqual(len(args), 1)

        matches = re.match(r'http://127.0.0.1:\d+/src.js', args[0])
        self.assertIsNot(matches, None)

    def test_multiple_instances_unique_ip(self):

        # Start the first service
        self.instrumenter.start()

        # Start a second service
        other = SrcInstrumenter(self.TEST_ROOT_DIR,
                                tool_path=self.TEST_TOOL_PATH,
                                subprocess_module=self.subprocess,
                                requests_module=self.requests)
        other.start()

        # Expect that the service process was started twice,
        # with different ports
        self._assert_jscover_called(self.TEST_TOOL_PATH,
                                    self.TEST_ROOT_DIR,
                                    num_calls=2)

    def test_retry_on_port_conflict(self):

        # Configure the tool to return an error the first time
        # because something else is running on this port
        self._configure_tool(error_msg=self.ADDRESS_IN_USE_ERROR,
                             first_failure=True)

        # Start the service
        self.instrumenter.start()

        # Expect that the service process was started twice,
        # with different ports.
        self._assert_jscover_called(self.TEST_TOOL_PATH,
                                    self.TEST_ROOT_DIR,
                                    num_calls=2)

    def test_max_retry_port_conflict(self):

        # Configure the tool to always return an error
        self._configure_tool(error_msg=self.ADDRESS_IN_USE_ERROR)

        # Start the service
        with self.assertRaises(SrcInstrumenterError):
            self.instrumenter.start()

        # Expect that the tool was called several times with different
        # port numbers.
        self._assert_jscover_called(self.TEST_TOOL_PATH,
                                    self.TEST_ROOT_DIR,
                                    num_calls=SrcInstrumenter.MAX_START_ATTEMPTS)

    def test_command_not_found(self):

        # Configure the tool to raise an OSError (tool path not found)
        self.subprocess.Popen.side_effect = OSError

        # Expect an error
        with self.assertRaises(SrcInstrumenterError):
            self.instrumenter.start()

        # Expect that we only called the process exactly once
        self._assert_jscover_called(self.TEST_TOOL_PATH,
                                    self.TEST_ROOT_DIR,
                                    num_calls=1)

    def test_http_not_found_error(self):

        # Configure the `requests` HTTP library to return a
        # 404 not found response
        self._configure_http_response(404, "")

        # Try to instrument a source
        with self.assertRaises(SrcInstrumenterError):
            self.instrumenter.instrumented_src('src.js')

    def test_http_connection_refused_retry(self):

        # Raise a connection error on the first connection
        # Then return a success on the second attempt
        self._configure_http_response(200, self.TEST_INSTRUMENTED_SRC)
        self.requests.get.side_effect = [requests.exceptions.ConnectionError,
                                         self.requests.get.return_value]

        # Get the instrumented source (expect a retry on the first failure)
        result = self.instrumenter.instrumented_src('/src.js')

        # Expect that we get the right source back
        self.assertEqual(result, self.TEST_INSTRUMENTED_SRC)

    def test_http_connection_refused_max_retry(self):

        # Raise a connection error on every attempt
        self.requests.get.side_effect = requests.exceptions.ConnectionError

        # Expect that the instrumenter eventually gives up and raises an error
        with self.assertRaises(SrcInstrumenterError):
            self.instrumenter.instrumented_src('/src.js')

    def _configure_http_response(self, status_code, content):
        """
        Configure the `requests` library to respond with the given
        HTTP `status_code` and `content`.
        """
        response_mock = mock.MagicMock(requests.models.Response)
        response_mock.status_code = status_code
        response_mock.text = content
        self.requests.get.return_value = response_mock

    def _configure_tool(self, error_msg=None, first_failure=False):
        """
        Configure the JSCover subprocess to either continue running
        indefinitely (like JSCover will if it can start successfully)
        or terminate and output to stderr.

        `error_msg` is the error for the tool to return.
        If `first_failure` is `True`, configure the tool to return
        an error the first time it's called but succeed afterwards.
        Otherwise, always return an error.

        For testing purposes, the tool will not block indefinitely;
        it will raise an `Exception` indicating that the software
        under test would deadlock.
        """

        # Configure the tool to continue running indefinitely
        if error_msg is None:
            self.process.poll.return_value = None
            msg = "Do not call communicate() -- it will block indefinitely!"
            self.process.communicate.side_effect = Exception(msg)

        # Configure the tool to return immediately and have
        # an error return value
        else:

            # Fail the first time, then succeed
            if first_failure:
                self.process.communicate.side_effect = [("", error_msg), ("", "")]
                self.process.poll.side_effect = [1, None]

            # Always return an error
            else:
                self.process.communicate.side_effect = None
                self.process.communicate.return_value = ("", error_msg)
                self.process.poll.return_value = 1

    def _assert_jscover_called(self, tool_path, document_root, num_calls=1):
        """
        Assert that the JSCover tool was called `num_calls` times
        and configured to serve files in `document_root` to a local port.

        If called multiple times, expect that a unique port number was used.
        """

        # Check that we have the correct number of calls
        self.assertEqual(len(self.subprocess.Popen.call_args_list), num_calls)

        # Keep track of the ports we've already used
        used_ports = []

        # Verify that each call has the correct form
        for args, kwargs in self.subprocess.Popen.call_args_list:

            # First arg should be the list of call components
            self.assertEqual(len(args), 1)
            call = args[0]

            # Should send stdout and stderr back to the caller
            self.assertEqual(kwargs, {'stdout': None,
                                      'stderr': self.subprocess.PIPE})

            # Should be correct number of args
            self.assertEqual(len(call), 6)

            # First arguments specify the tool
            self.assertEqual(call[0:4],
                             ['java', '-jar', tool_path, '-ws'])

            # Next argument should be the local port
            ports = re.findall(r'--port=(\d+)', call[4])
            self.assertEqual(len(ports), 1)
            port_num = int(ports[0])
            self.assertTrue(10000 <= port_num <= 40000)
            self.assertFalse(port_num in used_ports)

            # Then the document root
            self.assertEqual(call[5], '--document-root=' + document_root)

            # Remember that we've seen this port
            used_ports.append(port_num)


class CoverageDataTest(unittest.TestCase):

    TEST_COVERAGE_DICT = {
        '/src1.js': {
            'lineData': [2, None, 1, 0, None, 2],
            'functionData': ['not used'],
            'branchData': ['not used']
        },
        '/subdir/src2.js': {
            'lineData': [1, 1, 1, 0],
            'functionData': ['not used'],
            'branchData': ['not used']
        }
    }

    def test_load_from_dict(self):

        # Load the data
        coverage_data = CoverageData()
        coverage_data.load_from_dict('/root_dir', self.TEST_COVERAGE_DICT)

        # Check that it gets parsed correctly
        self.assertEqual(coverage_data.src_list(),
                         [u'/root_dir/src1.js', u'/root_dir/subdir/src2.js'])

        self.assertEqual(coverage_data.line_dict_for_src('/root_dir/src1.js'),
                         {0: True, 2: True, 3: False, 5: True})

        self.assertEqual(coverage_data.line_dict_for_src('/root_dir/subdir/src2.js'),
                         {0: True, 1: True, 2: True, 3: False})

    def test_multiple_load_from_dict(self):

        # Load the data
        coverage_data = CoverageData()
        coverage_data.load_from_dict('/root_dir', self.TEST_COVERAGE_DICT)

        # Load additional data covering the lines that were uncovered
        lines = [0, 1, 0, 1, 1, None]
        coverage_data.load_from_dict('/root_dir', {'/src1.js': {'lineData': lines}})

        # Check that the two sources are combined correctly
        expected = {0: True, 1: True, 2: True, 3: True, 4: True, 5: True}
        self.assertEqual(coverage_data.line_dict_for_src('/root_dir/src1.js'), expected)

    def test_different_root_dirs(self):

        # Load data from two different root dirs
        coverage_data = CoverageData()
        coverage_data.load_from_dict('/root_1', self.TEST_COVERAGE_DICT)
        coverage_data.load_from_dict('/root_2', self.TEST_COVERAGE_DICT)

        # We should get two separate sources
        self.assertEqual(coverage_data.src_list(),
                         ['/root_1/src1.js', '/root_1/subdir/src2.js',
                          '/root_2/src1.js', '/root_2/subdir/src2.js'])

        # But the data in each should be the same
        expected = {0: True, 2: True, 3: False, 5: True}
        self.assertEqual(coverage_data.line_dict_for_src('/root_1/src1.js'),
                         expected)
        self.assertEqual(coverage_data.line_dict_for_src('/root_2/src1.js'),
                         expected)

    def test_suite_num_list(self):

        # Report data from two suites
        coverage_data = CoverageData()
        coverage_data.add_suite_num(2)
        coverage_data.add_suite_num(3)
        coverage_data.add_suite_num(3)

        self.assertEqual(coverage_data.suite_num_list(), [2, 3])

    def test_invalid_dict(self):

        # Pass in some invalid data
        for invalid in ["", "invalid", ["list"], 5, None]:
            with self.assertRaises(ValueError):
                coverage_data = CoverageData()
                coverage_data.load_from_dict('root_dir', invalid)

    def test_missing_key(self):

        # Load data with a JSON dict that is missing the line keys
        coverage_data = CoverageData()
        coverage_data.load_from_dict('root_dir',
                                     {'/src1': {'missing key': True}})

        # Expect that no coverage information is loaded
        self.assertEqual(coverage_data.src_list(), [])
        self.assertIs(coverage_data.line_dict_for_src('root_dir/src1'), None)

    def test_coverage_for_src(self):
        coverage_data = CoverageData()
        coverage_data.load_from_dict('root_dir', self.TEST_COVERAGE_DICT)

        # The coverage for root_dir/src1.js is 3/4 = 0.75
        self.assertEqual(coverage_data.coverage_for_src('root_dir/src1.js'), 0.75)

    def test_total_coverage(self):
        coverage_data = CoverageData()
        coverage_data.load_from_dict('root_dir', self.TEST_COVERAGE_DICT)

        # Total coverage is 6/8 = 0.75
        self.assertEqual(coverage_data.total_coverage(), 0.75)

    def test_get_relative_src_path(self):

        # Load the data
        coverage_data = CoverageData()
        coverage_data.load_from_dict('/root_dir', self.TEST_COVERAGE_DICT)

        # Check that we can retrieve the relative source path
        self.assertEqual(coverage_data.rel_src_path(u'/root_dir/src1.js'), 'src1.js')
        self.assertEqual(coverage_data.rel_src_path(u'/root_dir/subdir/src2.js'), 'subdir/src2.js')

    def test_get_relative_unknown_path(self):

        # Load the data
        coverage_data = CoverageData()
        coverage_data.load_from_dict('/root_dir', self.TEST_COVERAGE_DICT)

        # Unknown path returns None, even if in the root dir
        self.assertIs(coverage_data.rel_src_path('unknown'), None)
        self.assertIs(coverage_data.rel_src_path('/root_dir/unknown'), None)
