from unittest import TestCase
import json
from textwrap import dedent
from js_test_tool.browser import Browser, BrowserError
from js_test_tool.tests.helpers import StubServer


class BrowserTest(TestCase):

    def setUp(self):

        # Create a stub server on a local port
        self.stub_server = StubServer()

        # Create the browser (use PhantomJS)
        self.browser = Browser('phantomjs')

        # Configure the browser to have a shorter
        # timeout to speed up the test suite
        self._old_timeout = Browser.TIMEOUT
        Browser.TIMEOUT = 2.0

    def tearDown(self):

        # Stop the server and free the port
        self.stub_server.stop()

        # Stop the browser
        self.browser.quit()

        # Restore the old timeout
        Browser.TIMEOUT = self._old_timeout

    def test_get_page_results(self):

        # Configure the stub server to send a valid test results page
        results = [{'testGroup': "Adder%20tests",
                    'testName': "it%20should%20start%20at%20zero",
                    'testStatus': 'pass',
                    'testDetail': ''},
                   {'testGroup': 'Adder%20tests',
                    'testName': "it%20should%20add%20to%20the%20sum",
                    'testStatus': 'fail',
                    'testDetail': 'Stack%20trace'},
                   {'testGroup': 'Multiplier%20test',
                    'testName': 'it%20should%20multiply',
                    'testStatus': 'pass',
                    'testDetail': ''}]

        content = u'<div id="{}" class="{}">{}</div>'.format(Browser.RESULTS_DIV_ID,
                                                             Browser.DONE_DIV_CLASS,
                                                             json.dumps(results))
        self.stub_server.set_response(200, content)

        # Use the browser to load the page and parse the results
        server_url = self.stub_server.root_url()
        output_results = self.browser.get_page_results(server_url)

        # Check the results
        # Keys should be munged into Python-style var names
        expected_results = [{'test_group': 'Adder tests',
                             'test_name': 'it should start at zero',
                             'status': 'pass',
                             'detail': ''},
                            {'test_group': 'Adder tests',
                             'test_name': 'it should add to the sum',
                             'status': 'fail',
                             'detail': 'Stack trace'},
                            {'test_group': 'Multiplier test',
                             'test_name': 'it should multiply',
                             'status': 'pass',
                             'detail': ''}]

        self.assertEqual(expected_results, output_results)

    def test_result_control_chars(self):

        # Try sending a control char
        json_data = ('[{"testGroup":"when%20song%20has%20been%20paused",' +
                     '"testName":"should%20indicate%20that%20the%20song%20is%20currently%20paused",' +
                     '"testStatus":"fail",' +
                     '"testDetail":"Error:%20Expected%20true%20to%20be%20falsy.%0A%20at%20new%20jasmine.ExpectationResult"}]')

        content = u'<div id="{}" class="{}">{}</div>'.format(Browser.RESULTS_DIV_ID,
                                                             Browser.DONE_DIV_CLASS,
                                                             json_data)
        self.stub_server.set_response(200, content)

        # Use the browser to load the page and parse the results
        server_url = self.stub_server.root_url()
        output_results = self.browser.get_page_results(server_url)

        # Expect that we get the results back
        expected_results = [
            {u'test_group': u"when song has been paused",
             u'test_name': u"should indicate that the song is currently paused",
             u'status': u"fail",
             u'detail': u"Error: Expected true to be falsy.\n at new jasmine.ExpectationResult"}]

        self.assertEqual(expected_results, output_results)

    def test_result_html_chars(self):

        # Try sending unescaped HTML
        results = [{'testGroup': "%3Cdiv%3Ehtml%20%26%20%27%20%22%20%5C%20%3C/div%3E",
                    'testName': "%3Cb%3Emore%3C/b%3E%20%26%20%27%20%22%20%5C%20html",
                    'testStatus': "pass",
                    'testDetail': "%3Cb%3Eeven%20more%20%26%20%27%20%22%20%5C%20html"}]

        content = u'<div id="{}" class="{}">{}</div>'.format(Browser.RESULTS_DIV_ID,
                                                             Browser.DONE_DIV_CLASS,
                                                             json.dumps(results))
        self.stub_server.set_response(200, content)

        # Use the browser to load the page and parse the results
        server_url = self.stub_server.root_url()
        output_results = self.browser.get_page_results(server_url)

        # Expect that we get the results back
        expected_results = [
            {u'test_group': u"<div>html & ' \" \\ </div>",
             u'test_name': u"<b>more</b> & ' \" \\ html",
             u'status': u"pass",
             u'detail': u"<b>even more & ' \" \\ html"}]

        self.assertEqual(expected_results, output_results)

    def test_results_unicode(self):

        # Try sending unicode chars
        results = [{'testGroup': u'\u017C'.encode('utf8'),
                    'testName': u'\u0184'.encode('utf8'),
                    'testStatus': u'\u018A'.encode('utf8'),
                    'testDetail': u'\u02AA'.encode('utf8')}]

        content = u'<div id="{}" class="{}">{}</div>'.format(Browser.RESULTS_DIV_ID,
                                                             Browser.DONE_DIV_CLASS,
                                                             json.dumps(results))
        self.stub_server.set_response(200, content)

        # Use the browser to load the page and parse the results
        server_url = self.stub_server.root_url()
        output_results = self.browser.get_page_results(server_url)

        # Expect that we get the results back
        expected_results = [
            {u'test_group': u'\u017C',
             u'test_name': u'\u0184',
             u'status': u'\u018A',
             u'detail': u'\u02AA'}]

        self.assertEqual(expected_results, output_results)

    def test_no_results(self):
        # Configure the stub server to send an empty <div>
        content = u'<div id="{}" class="{}">[]</div>'.format(Browser.RESULTS_DIV_ID,
                                                             Browser.DONE_DIV_CLASS)
        self.stub_server.set_response(200, content)

        # Use the browser to load the page and parse the results
        server_url = self.stub_server.root_url()
        output_results = self.browser.get_page_results(server_url)

        # Expect we get an empty list back
        self.assertEqual(output_results, [])

    def test_slow_results(self):

        # Configure the stub server to fill in the <div>
        # after a long delay.
        delay_ms = 1000
        content = dedent(u"""
            <script type="text/javascript">
            setTimeout(function() {
                var json = ('[{"testGroup":"group", ' + 
                            '"testName":"name", ' +
                            '"testStatus":"fail", ' +
                            '"testDetail":"detail"}]');
                var el = document.getElementById("js_test_tool_results");
                el.innerText = json
                el.className = "%s"
            }, %d);
            </script>
            <div id="%s"></div>
            """ % (Browser.DONE_DIV_CLASS,
                   delay_ms,
                   Browser.RESULTS_DIV_ID)).strip()

        self.stub_server.set_response(200, content)

        # Use the browser to load the page and parse the results
        server_url = self.stub_server.root_url()
        output_results = self.browser.get_page_results(server_url)

        # Expect that we block until the results load
        expected_results = [
            {u'test_group': u"group",
             u'test_name': u"name",
             u'status': u"fail",
             u'detail': u"detail"}]
        self.assertEqual(expected_results, output_results)

    def test_error_conditions(self):

        div_id = Browser.RESULTS_DIV_ID
        error_responses = [(200, u'<div id="wrong_id"></div>'),
                           (200, u''),
                           (200, u'<div id="{}">Not JSON</div>'.format(div_id)),
                           (200, u'<div id="{}">[{"missing_keys":"val"}]</div>'),
                           (404, u'Not found'),
                           (500, u'Error occurred')]

        server_url = self.stub_server.root_url()

        for (status_code, content) in error_responses:

            # Configure the stub server to send an invalid response
            self.stub_server.set_response(status_code, content)

            # Expect an exception
            with self.assertRaises(BrowserError):
                self.browser.get_page_results(server_url)

    def test_no_response(self):

        # Configure the server to ignore requests
        self.stub_server.set_ignore_requests(True)

        server_url = self.stub_server.root_url()

        # Configure the Browser to timeout quickly
        old_timeout = Browser.TIMEOUT

        def cleanup():
            Browser.TIMEOUT = old_timeout
        self.addCleanup(cleanup)

        Browser.TIMEOUT = 0.2

        # Expect the Browser to give an error when it times out
        with self.assertRaises(BrowserError):
            self.browser.get_page_results(server_url)
