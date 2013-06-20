"""
Serve test runner pages and included JavaScript files on a local port.
"""

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import threading
import re

class SuitePageServer(HTTPServer):
    """
    Serve test suite pages and included JavaScript files.
    """

    def __init__(self, suite_desc_list, suite_renderer):
        """
        Initialize the server to serve test runner pages
        and dependencies described by `suite_desc_list`
        (list of `SuiteDescription` instances).

        Use `suite_renderer` (a `SuiteRenderer` instance) to
        render the test suite pages.
        """

        # Store dependencies
        self._desc_list = suite_desc_list
        self._renderer = suite_renderer

        # Using port 0 assigns us an unused port
        address = ('127.0.0.1', 0)
        HTTPServer.__init__(self, address, SuitePageRequestHandler)

    def start(self):
        """
        Start serving pages on an open local port.
        """
        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def stop(self):
        """
        Stop the server and free the port.
        """
        self.shutdown()
        self.socket.close()

    def suite_url_list(self):
        """
        Return a list of URLs (unicode strings), where each URL
        is a test suite page containing the JS code to run
        the JavaScript tests.
        """
        return [self.root_url() + u'suite/{}'.format(suite_num)
                for suite_num in range(len(self._desc_list))]

    def root_url(self):
        """
        Return the root URL (including host and port) for the server
        as a unicode string.
        """
        host, port = self.server_address
        return u"http://{}:{}/".format(host, port)

    def suite_page(self, suite_num):
        """
        Render the suite runner page for the suite description
        with index `suite_num`.

        Returns a unicode string.  If the suite number is invalid,
        returns None.
        """
        # Retrieve the suite description
        try:
            suite_desc = self._desc_list[suite_num]

        # If we could not find the suite, return None
        except IndexError:
            return None

        # Otherwise, render the page
        else:
            return self._renderer.render_to_string(suite_desc)

    def dependency_contents(self, path):
        """
        Return the contents of the dependency at `path`, if found.
        Otherwise, return None.

        Returns the contents as a `str` (not `unicode`).
        """

        # Strip the first forward slash to make it a relative path
        if path.startswith('/'):
            path = path[1:]

        # DEBUG
        print "checking path: {}".format(path)
                
        # Search for the dependency file
        if self._can_serve_path(path):

            # DEBUG
            print "serving path: {}".format(path)

            # Load the file
            try:

                with open(path) as js_file:
                    contents = js_file.read()

            # If we cannot open the file (e.g. because it's not found),
            # return None
            except IOError:
                return None

            # Return the contents (as a byte string)
            return contents

        # If we can't serve this path (because it's not a 
        # dependency specified by the test suite),
        # return None.
        else:
            return None

    def _can_serve_path(self, path):
        """
        Search for the dependency path within each test suite.
        If found, return the (relative) path to the file;
        otherwise return None.
        """

        # Iterate through each suite description
        for suite_desc in self._desc_list:

            all_paths = (suite_desc.lib_paths() +
                         suite_desc.src_paths() +
                         suite_desc.spec_paths())

            # If we find the path in the dependencies, we can serve it
            if path in all_paths:
                return True

        # Otherwise, we cannot serve this dependency
        return False


class SuitePageRequestHandler(BaseHTTPRequestHandler):
    """
    Handle HTTP requests to the `SuitePageServer`.
    """

    protocol = "HTTP/1.0"

    SUITE_PAGE_REGEX = re.compile('^/suite/([0-9]+)/?$')

    def do_GET(self):
        """
        Serve suite runner pages and JavaScript dependencies.
        """

        # Try to retrieve the suite number
        suite_num = self._parse_suite_num(self.path)

        # If a suite number is defined, serve the suite page
        if suite_num is not None:
            self._serve_suite(suite_num)

        # Otherwise, serve JS dependencies (lib, src, and spec files)
        else:
            self._serve_dependency(self.path)

        self._send_response(200, None)
    
    def _send_response(self, status_code, content):
        """
        Send a response to an HTTP request as UTF-8 encoded HTML.
        `content` can be empty, None, or a UTF-8 string.
        """

        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()

        if content:
            self.wfile.write(content)

    def _serve_suite(self, suite_num):
        """
        Serve the suite runner page with index `suite_num`,
        or file not found if no such suite is defined.
        """

        page = self.server.suite_page(suite_num)

        # If no page rendered, send a file not found
        if page is None:
            self._send_response(404, None)

        # Otherwise, send the page
        else:
            self._send_response(200, page)

    def _serve_dependency(self, path):
        """
        Serve the JavaScript dependency (lib, src, and spec files),
        or send a file not found response.
        """
        file_contents = self.server.dependency_contents(path)

        # If the file not found, send a file not found
        if file_contents is None:
            self._send_response(404, None)

        # Otherwise, send the contents of the file
        else:
            self._send_response(200, file_contents)

    @classmethod
    def _parse_suite_num(cls, path):
        """
        Return the suite number of the URL path, if it's valid.
        Otherwise, return None.
        """

        # Parse the path to retrieve the suite number
        result = cls.SUITE_PAGE_REGEX.match(path)

        # If no matches, this is not a valid suite path
        if result is None:
            return None

        # If we had a match, return the suite number
        else:
            return int(result.groups()[0])
