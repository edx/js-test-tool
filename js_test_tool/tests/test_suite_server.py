"""
Tests for the suite page server.
"""

from js_test_tool.tests.helpers import TempWorkspaceTestCase
import mock
import re
import requests
import os
from js_test_tool.suite import SuiteDescription, SuiteRenderer
from js_test_tool.suite_server import SuitePageServer


class SuitePageServerTest(TempWorkspaceTestCase):

    NUM_SUITE_DESC = 2

    def setUp(self):

        # Call the superclass implementation to create the temp workspace
        super(SuitePageServerTest, self).setUp()

        # Create mock suite descriptions
        self.suite_desc_list = [mock.MagicMock(SuiteDescription) 
                                for _ in range(self.NUM_SUITE_DESC)]

        # Configure the mock suite descriptions to have no dependencies
        for suite in self.suite_desc_list:
            suite.lib_paths.return_value = []
            suite.src_paths.return_value = []
            suite.spec_paths.return_value = []

        # Create a mock suite renderer
        self.suite_renderer = mock.MagicMock(SuiteRenderer)

        # Create the server
        self.server = SuitePageServer(self.suite_desc_list,
                                      self.suite_renderer)

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
            expected_url = self.server.root_url() + u'suite/{}'.format(suite_num)
            self.assertIn(expected_url, url_list)

    def test_serve_suite_pages(self):

        # Configure the suite renderer to return a test string
        expected_page = u'test suite mock'
        self.suite_renderer.render_to_string.return_value = expected_page

        # Check that we can load each page in the suite
        for url in self.server.suite_url_list():
            self._assert_page_equals(url, expected_page)

    def test_serve_lib_js(self):

        # Configure the suite description to contain JS dependencies
        lib_paths = ['lib/1.js', 'lib/subdir/2.js']
        self.suite_desc_list[0].lib_paths.return_value = lib_paths

        # Create fake files to serve
        os.makedirs('lib/subdir')
        expected_page = u'test lib file'
        self._create_fake_files(lib_paths, expected_page)

        # Expect that the server sends us the files
        for path in lib_paths:
            url = self.server.root_url() + path
            self._assert_page_equals(url, expected_page)

    def test_serve_src_js(self):

        # Configure the suite description to contain JS source files
        src_paths = ['src/1.js', 'src/subdir/2.js']
        self.suite_desc_list[0].src_paths.return_value = src_paths

        # Create fake files to serve
        os.makedirs('src/subdir')
        expected_page = u'test src file'
        self._create_fake_files(src_paths, expected_page)

        # Expect that the server sends us the files
        for path in src_paths:
            url = self.server.root_url() + path
            self._assert_page_equals(url, expected_page)

    def test_serve_spec_js(self):

        # Configure the suite description to contain JS spec files
        spec_paths = ['spec/1.js', 'spec/subdir/2.js']
        self.suite_desc_list[0].src_paths.return_value = spec_paths

        # Create fake files to serve
        os.makedirs('spec/subdir')
        expected_page = u'test spec file'
        self._create_fake_files(spec_paths, expected_page)

        # Expect that the server sends us the files
        for path in spec_paths:
            url = self.server.root_url() + path
            self._assert_page_equals(url, expected_page)

    def test_404_pages(self):

        # Try a URL that is not one of the suite urls
        root_url = self.server.root_url()
        bad_url_list = [root_url + 'invalid',
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

    def _assert_page_equals(self, url, expected_content):
        """
        Assert that the page at `url` contains `expected_content`.
        Uses a GET HTTP request to retrieve the page and expects
        a 200 status code, with UTF-8 encoding.
        """

        # HTTP GET request for the page
        response = requests.get(url)

        # Expect that we get a success result code
        self.assertEqual(response.status_code, requests.codes.ok, msg=url)

        # Expect that the content is what we rendered
        self.assertIn(expected_content, response.content, msg=url)

        # Expect that the encoding is UTF-8
        self.assertEqual(response.encoding, 'utf-8', msg=url)

    @staticmethod
    def _create_fake_files(path_list, contents):
        """
        For each path in `path_list`, create a file containing `contents`
        (a string).
        """

        for path in path_list:
            with open(path, 'w') as fake_file:
                fake_file.write(contents)
