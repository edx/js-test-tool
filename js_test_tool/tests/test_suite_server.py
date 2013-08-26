"""
Tests for the suite page server.
"""

from js_test_tool.tests.helpers import TempWorkspaceTestCase
import unittest
import mock
import re
import requests
import os
import pkg_resources
import json
from js_test_tool.suite import SuiteDescription, SuiteRenderer
from js_test_tool.suite_server import SuitePageServer, SuitePageHandler, \
    TimeoutError, DuplicateSuiteNameError
from js_test_tool.coverage import SrcInstrumenter


class SuitePageServerTest(TempWorkspaceTestCase):

    NUM_SUITE_DESC = 2

    def setUp(self):

        # Call the superclass implementation to create the temp workspace
        super(SuitePageServerTest, self).setUp()

        # Create mock suite descriptions
        self.suite_desc_list = [
            mock.MagicMock(SuiteDescription)
            for _ in range(self.NUM_SUITE_DESC)
        ]

        # Configure the mock suite descriptions to have no dependencies
        suite_num = 0
        for suite in self.suite_desc_list:
            suite.suite_name.return_value = 'test-suite-{}'.format(suite_num)
            suite.lib_paths.return_value = []
            suite.src_paths.return_value = []
            suite.spec_paths.return_value = []
            suite.fixture_paths.return_value = []
            suite.root_dir.return_value = os.getcwd()
            suite_num += 1

        # Create a mock suite renderer
        self.suite_renderer = mock.MagicMock(SuiteRenderer)

        # Create the server
        self.server = SuitePageServer(
            self.suite_desc_list, self.suite_renderer
        )

        # Start the server
        self.server.start()

    def tearDown(self):

        # Stop the server, which frees the port
        self.server.stop()

    def test_root_url(self):

        # Check that the root URL has the right form
        url_regex = re.compile('^http://127.0.0.1:[0-9]+/$')
        url = self.server.root_url()
        result = url_regex.match(url)
        self.assertIsNot(result, None,
                         msg="URL has incorrect format: '{}'".format(url))

    def test_suite_url_list(self):

        # Retrieve the urls for each test suite page
        url_list = self.server.suite_url_list()

        # Expect that we have the correct number of URLs
        self.assertEqual(len(url_list), self.NUM_SUITE_DESC)

        # Expect that the URLs have the correct form
        for suite_num in range(self.NUM_SUITE_DESC):
            expected_url = self.server.root_url() + u'suite/test-suite-{}'.format(suite_num)
            self.assertIn(expected_url, url_list)

    def test_enforce_unique_suite_names(self):

        # Try to create a suite server in which two suites have the same name
        suite_desc_list = [
            mock.MagicMock(SuiteDescription)
            for _ in range(4)
        ]

        suite_desc_list[0].suite_name.return_value = 'test-suite-1'
        suite_desc_list[1].suite_name.return_value = 'test-suite-2'
        suite_desc_list[2].suite_name.return_value = 'test-suite-1'
        suite_desc_list[3].suite_name.return_value = 'test-suite-3'

        # Expect an error when initializing the server
        with self.assertRaises(DuplicateSuiteNameError):
            SuitePageServer(suite_desc_list, self.suite_renderer)

    def test_serve_suite_pages(self):

        # Configure the suite renderer to return a test string
        expected_page = u'test suite mock'
        self.suite_renderer.render_to_string.return_value = expected_page

        # Check that we can load each page in the suite
        for url in self.server.suite_url_list():
            self._assert_page_equals(url, expected_page)

    def test_serve_suite_pages_ignore_get_params(self):

        # Configure the suite renderer to return a test string
        expected_page = u'test suite mock'
        self.suite_renderer.render_to_string.return_value = expected_page

        # Check that we can load each page in the suite,
        # even if we add additional GET params
        for url in self.server.suite_url_list():
            url = url + "?param=12345"
            self._assert_page_equals(url, expected_page)

    def test_serve_runners(self):

        for path in ['jasmine/jasmine.css',
                     'jasmine/jasmine.js',
                     'jasmine/jasmine-json.js',
                     'jasmine/jasmine-html.js']:

            pkg_path = 'runner/' + path
            expected_page = pkg_resources.resource_string('js_test_tool', pkg_path)
            url = self.server.root_url() + pkg_path
            self._assert_page_equals(url, expected_page)

    def test_ignore_runner_get_params(self):

        for path in ['jasmine/jasmine.css',
                     'jasmine/jasmine.js',
                     'jasmine/jasmine-json.js',
                     'jasmine/jasmine-html.js']:

            pkg_path = 'runner/' + path
            expected_page = pkg_resources.resource_string('js_test_tool', pkg_path)

            # Append GET params to the URL
            url = self.server.root_url() + pkg_path + "?param=abc.123&another=87"

            # Should still be able to load the page
            self._assert_page_equals(url, expected_page)

    def test_serve_lib_js(self):

        # Configure the suite description to contain JS dependencies
        lib_paths = ['lib/1.js', 'lib/subdir/2.js']
        self.suite_desc_list[0].lib_paths.return_value = lib_paths

        # Create fake files to serve
        os.makedirs('lib/subdir')
        expected_page = u'\u0236est \u023Dib file'
        self._create_fake_files(lib_paths, expected_page)

        # Expect that the server sends us the files
        for path in lib_paths:
            url = self.server.root_url() + 'suite/test-suite-0/include/' + path
            self._assert_page_equals(url, expected_page)

    def test_serve_src_js(self):

        # Configure the suite description to contain JS source files
        src_paths = ['src/1.js', 'src/subdir/2.js']
        self.suite_desc_list[0].src_paths.return_value = src_paths

        # Create fake files to serve
        os.makedirs('src/subdir')
        expected_page = u'test \u023Frc file'
        self._create_fake_files(src_paths, expected_page)

        # Expect that the server sends us the files
        for path in src_paths:
            url = self.server.root_url() + 'suite/test-suite-0/include/' + path
            self._assert_page_equals(url, expected_page)

    def test_serve_spec_js(self):

        # Configure the suite description to contain JS spec files
        spec_paths = ['spec/1.js', 'spec/subdir/2.js']
        self.suite_desc_list[0].spec_paths.return_value = spec_paths

        # Create fake files to serve
        os.makedirs('spec/subdir')
        expected_page = u'test spe\u023C file'
        self._create_fake_files(spec_paths, expected_page)

        # Expect that the server sends us the files
        for path in spec_paths:
            url = self.server.root_url() + 'suite/test-suite-0/include/' + path
            self._assert_page_equals(url, expected_page)

    def test_serve_text_fixtures(self):

        # Configure the suite description to contain test fixture files
        fixture_paths = ['fixtures/1.html', 'fixtures/subdir/2.html']
        self.suite_desc_list[0].fixture_paths.return_value = fixture_paths

        # Create fake files to serve
        os.makedirs('fixtures/subdir')
        expected_page = u'test fi\u039Eture'
        self._create_fake_files(fixture_paths, expected_page)

        # Expect that the server sends us the files
        for path in fixture_paths:
            url = self.server.root_url() + 'suite/test-suite-0/include/' + path
            self._assert_page_equals(url, expected_page)

    def test_serve_binary_fixtures(self):

        # Configure the suite description to contain binary fixture files
        fixture_paths = ['fixtures/test.mp4', 'fixtures/test.png']
        self.suite_desc_list[0].fixture_paths.return_value = fixture_paths

        # Create fake files to serve
        os.mkdir('fixtures')
        file_contents = '\x02\x03\x04\x05\x06'
        self._create_fake_files(fixture_paths, file_contents, encoding=None)

        # Expect that the server sends us the files as 
        # an un-decoded byte stream
        for path in fixture_paths:
            url = self.server.root_url() + 'suite/test-suite-0/include/' + path
            self._assert_page_equals(url, file_contents, encoding=None)

    def test_serve_byte_range_requests(self):

        # Configure the suite description to contain a binary fixture file
        fixture_paths = ['fixtures/test.mp4']
        self.suite_desc_list[0].fixture_paths.return_value = fixture_paths

        # Make this file fairly large, so we can access ranges of it
        file_size = 10000

        # Create a fake file to serve
        os.mkdir('fixtures')
        file_contents = '\x01' * file_size
        self._create_fake_files(fixture_paths, file_contents, encoding=None)

        # Check for byte range support
        url = self.server.root_url() + 'suite/test-suite-0/include/fixtures/test.mp4'
        resp = requests.get(url, headers={'Range': None})

        # Expect that the server supports byte ranges
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get('Accept-Ranges'), 'bytes')

        # Check that we can make requests for byte ranges
        # Examples taken from the RFC:
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.35.1
        test_cases = [
            ('0-499', 0, 499),
            ('0-', 0, 9999),
            ('9000-9999', 9000, 9999),
            ('9500-', 9500, 9999),
            ('-500', 9500, 9999),
        ]

        for byte_range, content_start, content_end in test_cases:

            print "Sending byte range '{0}'".format(byte_range)

            resp = requests.get(url, headers={'Range': 'bytes=' + byte_range})

            # Expect that we get a 206 (partial content)
            self.assertEqual(resp.status_code, 206)

            self.assertEqual(
                resp.headers.get('Content-Range'),
                'bytes {0}-{1}/{2}'.format(content_start, content_end, file_size)
            )

            content_len = content_end - content_start + 1
            self.assertEqual(resp.headers.get('Content-Length'), str(content_len))
            self.assertEqual(len(resp.content), content_len)

    def test_serve_multiple_byte_ranges(self):

        # Configure the suite description to contain a binary fixture file
        fixture_paths = ['fixtures/test.mp4']
        self.suite_desc_list[0].fixture_paths.return_value = fixture_paths

        # Create a fake file to serve
        # The file has \x01 as the first byte, \x02 as the middle bytes
        # and \x03 as the last byte
        os.mkdir('fixtures')
        file_contents = '\x01' * 10
        self._create_fake_files(fixture_paths, file_contents, encoding=None)

        # Make a request for multiple byte range
        byte_range = '0-3,4-7'
        url = self.server.root_url() + 'suite/test-suite-0/include/fixtures/test.mp4'
        resp = requests.get(url, headers={'Range': 'bytes=' + byte_range})

        # Expect that the request for multiple ranges is ignored
        # and the whole file is returned
        # (we don't implement this part of the protocol)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, file_contents)

    def test_invalid_byte_range(self):

        # Configure the suite description to contain a binary fixture file
        fixture_paths = ['fixtures/test.mp4']
        self.suite_desc_list[0].fixture_paths.return_value = fixture_paths

        # Make this file fairly large, so we can access ranges of it
        file_size = 10000

        # Create a fake file to serve
        os.mkdir('fixtures')
        file_contents = '\x01' * file_size
        self._create_fake_files(fixture_paths, file_contents, encoding=None)

        # Send invalid byte range headers and expect a 200 with the full file returned
        url = self.server.root_url() + 'suite/test-suite-0/include/fixtures/test.mp4'
        for invalid_range in ['not_bytes=0-10', 'bytes = space', 'bytes=text-text', 'bytes=-']:
            resp = requests.get(url, headers={'Range': invalid_range})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content, file_contents)

    def test_unsatisfiable_range(self):

        # Configure the suite description to contain a binary fixture file
        fixture_paths = ['fixtures/test.mp4']
        self.suite_desc_list[0].fixture_paths.return_value = fixture_paths

        # Make this file fairly large, so we can access ranges of it
        file_size = 10000

        # Create a fake file to serve
        os.mkdir('fixtures')
        file_contents = '\x01' * file_size
        self._create_fake_files(fixture_paths, file_contents, encoding=None)

        # Send unsatisfiable range (start > end) and expect a 406
        url = self.server.root_url() + 'suite/test-suite-0/include/fixtures/test.mp4'
        resp = requests.get(url, headers={'Range': 'bytes=10-2'})
        self.assertEqual(resp.status_code, 406)

    def test_serve_iso_encoded_dependency(self):
        
        # Configure the suite description to contain dependency files
        # that are ISO encoded
        dependencies = ['1.js', '2.js', '3.js', '4.js']
        self.suite_desc_list[0].lib_paths.return_value = [dependencies[0]]
        self.suite_desc_list[0].src_paths.return_value = [dependencies[1]]
        self.suite_desc_list[0].spec_paths.return_value = [dependencies[2]]
        self.suite_desc_list[0].fixture_paths.return_value = [dependencies[3]]

        # Create fake files to serve with ISO-8859-1 chars
        page_contents = '\xf6 \x9a \xa0'
        self._create_fake_files(dependencies, page_contents, encoding=None)

        # Expect that the server sends us the files,
        # ignoring any GET parameters we pass in the URL
        expected_page = u'\xf6 \x9a \xa0'
        for path in dependencies:
            url = self.server.root_url() + 'suite/test-suite-0/include/' + path + "?123456"
            self._assert_page_equals(url, expected_page, encoding='iso-8859-1')

    def test_ignore_dependency_get_params(self):

        # Configure the suite description to contain dependency files
        dependencies = ['1.js', '2.js', '3.js', '4.js']
        self.suite_desc_list[0].lib_paths.return_value = [dependencies[0]]
        self.suite_desc_list[0].src_paths.return_value = [dependencies[1]]
        self.suite_desc_list[0].spec_paths.return_value = [dependencies[2]]
        self.suite_desc_list[0].fixture_paths.return_value = [dependencies[3]]

        # Create fake files to serve
        expected_page = u'\u0236est dependency'
        self._create_fake_files(dependencies, expected_page)

        # Expect that the server sends us the files,
        # ignoring any GET parameters we pass in the URL
        for path in dependencies:
            url = self.server.root_url() + 'suite/test-suite-0/include/' + path + "?123456"
            self._assert_page_equals(url, expected_page)

    def test_different_working_dir(self):

        # Configure the suite description to contain JS dependencies
        spec_paths = ['spec/1.js']
        self.suite_desc_list[0].spec_paths.return_value = spec_paths

        # Create fake files to serve
        os.makedirs('spec/subdir')
        expected_page = u'test spec file'
        self._create_fake_files(spec_paths, expected_page)

        # Should be able to change the working directory and still
        # get the dependencies, because the suite description
        # contains the root directory for dependency paths.
        # The superclass `TemplateWorkspaceTestCase` will reset the working
        # directory on `tearDown()`
        os.mkdir('different_dir')
        os.chdir('different_dir')

        # Expect that we still get the files
        for path in spec_paths:
            url = self.server.root_url() + 'suite/test-suite-0/include/' + path
            self._assert_page_equals(url, expected_page)

    def test_404_pages(self):

        # Try a URL that is not one of the suite urls
        root_url = self.server.root_url()
        bad_url_list = [root_url + 'invalid',
                        root_url + 'runner/not_found.txt',
                        root_url + 'suite/{}'.format(self.NUM_SUITE_DESC + 1),
                        root_url + 'suite/{}'.format(-1)]

        # Expect that we get a page not found status
        for bad_url in bad_url_list:
            response = requests.get(bad_url)
            self.assertEqual(response.status_code,
                             requests.codes.not_found,
                             msg=bad_url)

    def test_missing_dependency(self):

        # Configure the suite description to contain a file
        self.suite_desc_list[0].src_paths.return_value = ['not_found.txt']

        # The file does not exist, so expect that we
        # get a not found response
        response = requests.get(self.server.root_url() + 'not_found.txt')
        self.assertEqual(response.status_code, requests.codes.not_found)

    def _assert_page_equals(self, url, expected_content, encoding='utf-8'):
        """
        Assert that the page at `url` contains `expected_content`.
        Uses a GET HTTP request to retrieve the page and expects
        a 200 status code, with UTF-8 encoding.

        `encoding` is the expected encoding.  If None, expect
        an unencoded byte string.
        """

        # HTTP GET request for the page
        response = requests.get(url)

        # Expect that we get a success result code
        self.assertEqual(response.status_code, requests.codes.ok, msg=url)

        # Expect that we got an accurate content length
        if encoding is None:
            expected_len = len(expected_content)
        else:
            expected_len = len(expected_content.encode(encoding))

        self.assertEqual(
            str(expected_len),
            response.headers.get('content-length')
        )

        # Expect that the content is what we rendered
        if encoding is not None:
            self.assertIn(
                expected_content,
                response.content.decode(encoding),
                msg=url
            )

        # If no encoding, just expect the byte string
        else:
            self.assertIn(expected_content, response.content, msg=url)

    @staticmethod
    def _create_fake_files(path_list, contents, encoding='utf8'):
        """
        For each path in `path_list`, create a file containing `contents`
        (a string).
        """

        for path in path_list:
            with open(path, 'w') as fake_file:

                # If an encoding is specified, use it to convert
                # the string to a byte str
                if encoding is not None:
                    encoded_contents = contents.encode(encoding)
                else:
                    encoded_contents = contents

                # Write the byte string to the file
                fake_file.write(encoded_contents)


class SuiteServerCoverageTest(TempWorkspaceTestCase):
    """
    Test that the suite page server correctly collects
    coverage info for JS source files.
    """

    JSCOVER_PATH = '/usr/local/jscover.jar'

    def setUp(self):

        # Create the temp workspace
        super(SuiteServerCoverageTest, self).setUp()

        # Configure the server to timeout quickly, to keep the test suite fast
        self._old_timeout = SuitePageServer.COVERAGE_TIMEOUT
        SuitePageServer.COVERAGE_TIMEOUT = 0.01

    def tearDown(self):

        # Tear down the temp workspace
        super(SuiteServerCoverageTest, self).tearDown()

        # Restore the old timeout
        SuitePageServer.COVERAGE_TIMEOUT = self._old_timeout

    @mock.patch('js_test_tool.suite_server.SrcInstrumenter')
    def test_creates_instrumenters_for_suites(self, instrumenter_cls):

        # Configure the instrumenter class to return mocks
        instr_mocks = [mock.MagicMock(SrcInstrumenter),
                       mock.MagicMock(SrcInstrumenter)]
        instrumenter_cls.side_effect = instr_mocks

        # Set up the descriptions
        mock_desc_list = [self._mock_suite_desc('test-suite-0', '/root_1', ['src1.js', 'src2.js']),
                          self._mock_suite_desc('test-suite-1', '/root_2', ['src3.js', 'src4.js'])]

        # Create a suite page server for those descriptions
        server = SuitePageServer(mock_desc_list,
                                 mock.MagicMock(SuiteRenderer),
                                 jscover_path=self.JSCOVER_PATH)

        # Start the server
        server.start()
        self.addCleanup(server.stop)

        # Expect that there is a SrcInstrumenter for each suite,
        # and it has been started.
        instr_dict = server.src_instr_dict
        self.assertEqual(len(instr_dict), len(mock_desc_list))

        for instr in instr_dict.values():
            instr.start.assert_called_once_with()

        # Stop the server
        # Expect that all the instrumenters are also stopped
        server.stop()
        for instr in instr_mocks:
            instr.stop.assert_called_once_with()

    @mock.patch('js_test_tool.suite_server.SrcInstrumenter')
    def test_serves_instrumented_source_files(self, instrumenter_cls):

        # Configure the instrumenter class to return a mock
        instr_mock = mock.MagicMock(SrcInstrumenter)
        instrumenter_cls.return_value = instr_mock

        # Configure the instrumenter to always return fake output
        fake_src = u"instr\u1205ented sr\u1239 output"
        instr_mock.instrumented_src.return_value = fake_src

        # Create a mock description with one source file
        mock_desc = self._mock_suite_desc('test-suite-0', '/root', ['src.js'])

        # Create a suite page server for those descriptions
        server = SuitePageServer([mock_desc],
                                 mock.MagicMock(SuiteRenderer),
                                 jscover_path=self.JSCOVER_PATH)

        # Start the server
        server.start()
        self.addCleanup(server.stop)

        # Access the page, expecting to get the instrumented source
        url = server.root_url() + "suite/test-suite-0/include/src.js"
        response = requests.get(url, timeout=0.1)

        self.assertEqual(response.text, fake_src)

    @mock.patch('js_test_tool.suite_server.SrcInstrumenter')
    def test_does_not_instrument_lib_or_spec_files(self, instrumenter_cls):

        # Configure the instrumenter class to return a mock
        instr_mock = mock.MagicMock(SrcInstrumenter)
        instrumenter_cls.return_value = instr_mock

        # Create a mock description with lib and spec files
        mock_desc = self._mock_suite_desc(
            'test-suite-0', '/root', ['src.js'],
            lib_paths=['lib.js'], spec_paths=['spec.js']
        )

        # Create a suite page server for the description
        server = SuitePageServer([mock_desc],
                                 mock.MagicMock(SuiteRenderer),
                                 jscover_path=self.JSCOVER_PATH)

        # Start the server
        server.start()
        self.addCleanup(server.stop)

        # Access the lib and spec pages
        url_list = [server.root_url() + "suite/test-suite-0/include/lib.js",
                    server.root_url() + "suite/test-suite-0/include/spec.js"]

        for url in url_list:
            requests.get(url, timeout=0.1)

        # Ensure that the instrumenter was NOT invoked,
        # since these are not source files
        self.assertFalse(instr_mock.instrumented_src.called)

    def test_collects_POST_coverage_info(self):

        # Start the page server
        server = SuitePageServer([self._mock_suite_desc('test-suite-0', '/root', ['src.js'])],
                                 mock.MagicMock(SuiteRenderer),
                                 jscover_path=self.JSCOVER_PATH)
        server.start()
        self.addCleanup(server.stop)

        # POST some coverage data to the src page
        # This test does NOT mock the CoverageData class created internally,
        # so we need to pass valid JSON data.
        # (Since CoverageData involves no network or file access, mocking
        # it is not worth the effort).
        coverage_data = {'/src.js': {'lineData': [1, 0, None, 2, 1, None, 0]}}

        requests.post(server.root_url() + "jscoverage-store/test-suite-0",
                      data=json.dumps(coverage_data),
                      timeout=0.1)

        # Get the results immediately from the server.
        # It's the server's responsibility to block until all results are received.
        result_data = server.all_coverage_data()

        # Check the result
        self.assertEqual(result_data.src_list(), ['/root/src.js'])
        self.assertEqual(result_data.line_dict_for_src('/root/src.js'),
                         {0: True, 1: False, 3: True, 4: True, 6: False})

    def test_uncovered_src(self):

        # Create the source file -- we need to do this
        # CoverageData can determine the number of uncovered
        # lines (every line in the file)
        num_lines = 5
        with open('src.js', 'w') as src_file:
            contents = '\n'.join(['test line' for _ in range(num_lines)])
            src_file.write(contents)

        # Start the page server
        root_dir = self.temp_dir
        server = SuitePageServer([self._mock_suite_desc('test-suite-0', root_dir, ['src.js'])],
                                 mock.MagicMock(SuiteRenderer),
                                 jscover_path=self.JSCOVER_PATH)
        server.start()
        self.addCleanup(server.stop)

        # POST empty coverage data back to the server
        # Since no coverage information is reported, we expect
        # that the source file in the suite description is
        # reported as uncovered.
        coverage_data = {}

        requests.post(server.root_url() + "jscoverage-store/test-suite-0",
                      data=json.dumps(coverage_data),
                      timeout=0.1)

        # Get the results immediately from the server.
        # It's the server's responsibility to block until all results are received.
        result_data = server.all_coverage_data()

        # Check the result -- expect that the source file
        # is reported as completely uncovered
        full_src_path = os.path.join(root_dir, 'src.js')
        self.assertEqual(result_data.src_list(), [full_src_path])
        self.assertEqual(result_data.line_dict_for_src(full_src_path),
                         {line_num: False for line_num in range(num_lines)})

    def test_timeout_if_missing_coverage(self):

        # Start the page server with multiple descriptions
        mock_desc_list = [self._mock_suite_desc('test-suite-0', '/root_1', ['src1.js', 'src2.js']),
                          self._mock_suite_desc('test-suite-1', '/root_2', ['src.js'])]

        server = SuitePageServer(mock_desc_list, mock.MagicMock(SuiteRenderer),
                                 jscover_path=self.JSCOVER_PATH)
        server.start()
        self.addCleanup(server.stop)

        # POST coverage data to one of the sources, but not the other
        coverage_data = {'/suite/test-suite-0/include/src1.js': {'lineData': [1]}}
        requests.post(server.root_url() + "jscoverage-store/test-suite-0",
                      data=json.dumps(coverage_data),
                      timeout=0.1)

        # Try to get the coverage data; expect it to timeout
        # We configured the timeout to be short in our setup method
        # so this should return quickly.
        with self.assertRaises(TimeoutError):
            server.all_coverage_data()

    @staticmethod
    def _mock_suite_desc(suite_name, root_dir, src_paths,
                         lib_paths=None, spec_paths=None):
        """
        Configure a mock `SuiteDescription` to have `root_dir` as its
        base directory and to list `src_paths` as its JavaScript
        sources.

        `suite_name` is the name of the suite, which determines
        the URL to access the suite pages.

        If `lib_paths` or `spec_paths` (lists of paths) are used,
        configure the description to use those lib and spec file paths.
        """
        mock_desc = mock.MagicMock(SuiteDescription)
        mock_desc.suite_name.return_value = suite_name
        mock_desc.root_dir.return_value = root_dir
        mock_desc.src_paths.return_value = src_paths

        if lib_paths is not None:
            mock_desc.lib_paths.return_value = lib_paths
        else:
            mock_desc.lib_paths.return_value = []

        if spec_paths is not None:
            mock_desc.spec_paths.return_value = spec_paths
        else:
            mock_desc.spec_paths.return_value = []

        return mock_desc


class SuitePageHandlerTest(unittest.TestCase):
    """
    Tests for utility methods in `SuitePageHandler`.
    """

    def test_safe_str_buffer(self):

        # We should be able to put in any bytestring and
        # get a buffer that we can safely typecast to a bytestring
        for str_input in [u'\u5890', u'\xf1\xfc]\x83', u'&R\xa2o']:

            # Create the string buffer
            str_buffer = SuitePageHandler.safe_str_buffer(str_input)

            # Try to read it as a byte string
            try:
                typecast = str(str_buffer.getvalue())

            except UnicodeEncodeError:
                self.fail("Could not encode {}".format(repr(str_input)))
