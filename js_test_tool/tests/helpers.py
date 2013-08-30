"""
Test helpers.
"""

import unittest
import tempfile
import shutil
import os
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import threading
import difflib
from nose.tools import ok_

import logging
LOGGER = logging.getLogger(__name__)


def assert_long_str_equal(expected, actual, strip=False):
    """
    Assert that two strings are equal and
    print the diff if they are not.

    If `strip` is True, strip both strings before comparing.
    """
    if strip:
        expected = expected.strip()
        actual = actual.strip()

    if expected != actual:

        # Print a human-readable diff
        diff = difflib.Differ().compare(
            expected.split('\n'), actual.split('\n')
        )

        # Fail the test
        ok_(False, '\n\n' + '\n'.join(diff))


class TempWorkspaceTestCase(unittest.TestCase):
    """
    Test case that creates a temporary directory that it uses
    as the working directory for the duration of the test.
    """

    def setUp(self):
        """
        Create the temporary directory and set it as the current
        working directory.
        """

        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Set the working directory to the temp dir, so we can
        # use relative paths within the directory.
        self._old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """
        Delete the temporary directory and restore the working directory.
        """
        shutil.rmtree(self.temp_dir)
        os.chdir(self._old_cwd)


class StubServer(HTTPServer):
    """
    Stub server that logs requests and returns a pre-defined response.
    """

    def __init__(self):
        """
        Start the server listening on an open local port.
        You can retrieve the address later with the
        `server_address` attribute.
        """

        # Start the server
        # Port 0 will cause the server to use an open port
        address = ('127.0.0.1', 0)
        HTTPServer.__init__(self, address, StubRequestHandler)
        self.start()

        # Create a list to hold logged requests
        self._requests = []

        # Set up the default response to requests
        self._status_code = 200
        self._content = ""
        self._ignore_requests = False

    def start(self):
        """
        Start the server listening on a local port.
        """
        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def stop(self):
        """
        Shutdown the server and close the socket so it can be re-used.
        """
        self.shutdown()
        self.socket.close()

    def log_request(self, request_type, path, content):
        """
        Store a request sent to the server.
        """
        self._requests.append((request_type, path, content))

    def requests(self):
        """
        Retrieve a record of all requests sent to the server.
        """
        return self._requests

    def set_response(self, status_code, content):
        """
        Set the response returned by the server.
        """
        self._status_code = status_code
        self._content = content

    def set_ignore_requests(self, ignore_requests):
        """
        Configure the server to stop responding to requests.
        `ignore_requests` is a bool.
        """
        self._ignore_requests = ignore_requests

    def status_code(self):
        return self._status_code

    def content(self):
        return self._content

    def ignore_requests(self):
        return self._ignore_requests

    def root_url(self):
        host, port = self.server_address
        return "http://{}:{}".format(host, port)


class StubRequestHandler(BaseHTTPRequestHandler):
    """
    Stub request handler, which logs requests and
    returns pre-defined responses.
    """

    protocol = "HTTP/1.1"

    def do_GET(self):
        """
        Respond to an HTTP GET request.
        Log the request to the server, then return
        the response configured for the server.
        """
        self.server.log_request('GET', self.path, self._content())
        self._send_server_response()

    def log_message(self, format_str, *args):
        """
        Override the base-class logger to avoid spamming the console.
        """
        LOGGER.debug("{} -- [{}] {}".format(self.client_address[0],
                                            self.log_date_time_string(),
                                            format_str % args))

    def _content(self):
        """
        Retrieve the content of the request.
        """
        try:
            length = int(self.headers.getheader('content-length'))
        except (TypeError, ValueError):
            return ""
        else:
            return self.rfile.read(length)

    def _send_server_response(self):
        """
        Send a server-defined response to the client.
        """
        if not self.server.ignore_requests():
            self.send_response(self.server.status_code())
            self.end_headers()
            self.wfile.write(self.server.content())
