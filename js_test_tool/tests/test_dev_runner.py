from unittest import TestCase
import mock
import webbrowser
import os
from js_test_tool.suite_server import SuitePageServer
from js_test_tool.suite import SuiteDescription, SuiteRenderer
from js_test_tool.dev_runner import SuiteDevRunner, SuiteDevRunnerFactory
from js_test_tool.tests.helpers import TempWorkspaceTestCase


class SuiteDevRunnerTest(TestCase):

    SUITE_URL = 'http://localhost:1234/suite/0'

    def setUp(self):

        # Create mock dependencies
        self.mock_page_server = mock.MagicMock(SuitePageServer)
        self.mock_page_server.suite_url_list.return_value = [self.SUITE_URL]
        self.mock_webbrowser = mock.MagicMock(webbrowser)

        # Create the runner instance, and configure it to
        # exit immediately.
        self.runner = SuiteDevRunner(self.mock_page_server,
                                     webbrowser_module=self.mock_webbrowser,
                                     stop_fast=True)

    def test_run(self):

        # Run the tests in dev mode
        self.runner.run()

        # Expect that the page server was started/stopped
        self.mock_page_server.start.assert_called_once_with()
        self.mock_page_server.stop.assert_called_once_with()

        # Expect that the webbrowser opened the suite URL
        self.mock_webbrowser.open_new.assert_called_once_with(self.SUITE_URL)

    def test_no_urls(self):

        # This should get caught by argument validation, but check anyway
        self.mock_page_server.suite_url_list.return_value = []

        with self.assertRaises(ValueError):
            self.runner.run()

    def test_multiple_urls(self):

        # This should get caught by argument validation, but check anyway
        self.mock_page_server.suite_url_list.return_value = [self.SUITE_URL] * 5

        # Run the tests in dev mode
        self.runner.run()

        # Expect that the webbrowser opened only the first URL
        self.mock_webbrowser.open_new.assert_called_once_with(self.SUITE_URL)


class SuiteDevRunnerFactoryTest(TempWorkspaceTestCase):

    def setUp(self):

        # Call superclass implementation to create the workspace
        super(SuiteDevRunnerFactoryTest, self).setUp()

        # Create mock instances to be returned by the constructors
        # of each mock class.
        self.mock_desc = mock.MagicMock(SuiteDescription)
        self.mock_renderer = mock.MagicMock(SuiteRenderer)
        self.mock_server = mock.MagicMock(SuitePageServer)
        self.mock_runner = mock.MagicMock(SuiteDevRunner)

        # Create mocks for each class that the factory will instantiate
        self.mock_desc_class = mock.MagicMock(return_value=self.mock_desc)
        self.mock_renderer_class = mock.MagicMock(return_value=self.mock_renderer)
        self.mock_server_class = mock.MagicMock(return_value=self.mock_server)
        self.mock_runner_class = mock.MagicMock(return_value=self.mock_runner)

        # Create the factory
        self.factory = SuiteDevRunnerFactory(
            desc_class=self.mock_desc_class,
            renderer_class=self.mock_renderer_class,
            server_class=self.mock_server_class)

    def test_build_runner(self):

        # Create fake suite description file
        suite_path = 'test_suite.yml'
        with open(suite_path, 'w') as suite_file:
            suite_file.write('test file')

        # Build the runner instance
        runner = self.factory.build_runner('test_suite.yml')

        # Should get a runner
        self.assertTrue(isinstance(runner, SuiteDevRunner))

        # Retrieve the arguments used to initialize the suite description
        call_args_list = self.mock_desc_class.call_args_list
        self.assertEqual(len(call_args_list), 1)
        args, _ = call_args_list[0]
        file_handle = args[0]
        root_dir = args[1]

        # Expect that the file handle points to the right file
        self.assertEqual(suite_path, file_handle.name)

        # Root directory should be the location of the suite file
        self.assertEqual(os.path.realpath(root_dir),
                         os.path.realpath(self.temp_dir))

        # Expect that the renderer is configured to render the
        # dev mode version of the test runner page
        self.mock_renderer_class.assert_called_once_with(dev_mode=True)

        # Expect that the server was configured with the renderer
        # and suite description
        self.mock_server_class.assert_called_with([self.mock_desc],
                                                  self.mock_renderer,
                                                  jscover_path=None)
