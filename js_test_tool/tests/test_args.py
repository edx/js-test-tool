import unittest
from js_test_tool.tool import parse_args
import tempfile
import os


class ParseArgsTest(unittest.TestCase):

    TOOL_NAME = "js-test-tool"

    def test_init_command(self):
        argv = [self.TOOL_NAME, 'init', 'js_test_suite.yml']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('command'), 'init')
        self.assertEqual(arg_dict.get('test_suite_paths'), ['js_test_suite.yml'])

    def test_run_command(self):
        argv = [self.TOOL_NAME, 'run', 'test_suite.yaml', '--use-phantomjs']
        arg_dict = parse_args(argv)

        self.assertEqual(arg_dict.get('command'), 'run')
        self.assertEqual(arg_dict.get('test_suite_paths'), ['test_suite.yaml'])
        self.assertIs(arg_dict.get('coverage_xml'), None)
        self.assertIs(arg_dict.get('coverage_html'), None)
        self.assertIs(arg_dict.get('timeout'), None)

    def test_dev_command(self):
        argv = [self.TOOL_NAME, 'dev', 'test_suite.yaml']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('command'), 'dev')

    def test_parse_test_suite_multiple_files(self):
        argv = [self.TOOL_NAME, 'run', 'test_suite_1.yaml', 'test_suite_2.yaml', '--use-chrome']
        arg_dict = parse_args(argv)

        self.assertEqual(arg_dict.get('test_suite_paths'),
                         ['test_suite_1.yaml', 'test_suite_2.yaml'])

    def test_parse_coverage_xml(self):
        argv = [self.TOOL_NAME, 'run', 'test_suite.yaml', '--coverage-xml',
                'coverage.xml', '--use-firefox']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('coverage_xml'), 'coverage.xml')

    def test_parse_coverage_html(self):
        argv = [self.TOOL_NAME, 'run', 'test_suite.yaml', '--coverage-html', 'coverage.html',
                '--use-firefox']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('coverage_html'), 'coverage.html')

    def test_parse_coverage_xml_and_html(self):
        argv = [self.TOOL_NAME, 'run', 'test_suite.yaml',
                '--coverage-xml', 'coverage.xml',
                '--coverage-html', 'coverage.html',
                '--use-phantomjs']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('coverage_xml'), 'coverage.xml')
        self.assertEqual(arg_dict.get('coverage_html'), 'coverage.html')

    def test_parse_browser_names(self):

        cases = [('--use-phantomjs', 'phantomjs'),
                 ('--use-chrome', 'chrome'),
                 ('--use-firefox', 'firefox')]

        for (browser_arg, browser_name) in cases:
            argv = [self.TOOL_NAME, 'run', 'test_suite.yaml', browser_arg]
            arg_dict = parse_args(argv)
            self.assertEqual(arg_dict.get('browser_names'), [browser_name])

    def test_parse_all_browsers(self):

        argv = [self.TOOL_NAME, 'run', 'test_suite.yaml', '--use-phantomjs',
                '--use-chrome', '--use-firefox']

        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('browser_names'),
                         ['phantomjs', 'chrome', 'firefox'])

    def test_parse_timeout(self):

        argv = [self.TOOL_NAME, 'run',
                'test_suite.yaml', '--use-phantomjs',
                '--timeout_sec', '5.3']

        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('timeout_sec'), 5.3)

    def test_parse_invalid_arg(self):

        invalid_argv = [
            # No arguments
            [],

            # No browser, suite description, or command
            [self.TOOL_NAME],

            # No suite description
            [self.TOOL_NAME, 'run'],
            [self.TOOL_NAME, 'init'],

            # Invalid command name
            [self.TOOL_NAME, 'invalid_cmd', 'js_suite.yml'],

            # Invalid or missing timeout values
            [self.TOOL_NAME, 'run', '--use-chrome', '--timeout_sec', 'not_a_number', 'test.yml'],
            [self.TOOL_NAME, 'run', 'test.yml', '--use-chrome', '--timeout_sec'],

            # No browser
            ['test_suite.yaml', '--coverage-xml', 'coverage.xml'],

            # No test suite description
            ['--use-phantomjs', '--coverage-xml', 'coverage.xml'],

            # No test suite description
            ['--use-chrome', '--coverage-html', 'coverage.html'],

            # No test suite description
            ['--use-firefox', '--coverage-xml', 'coverage.xml',
             '--coverage-html', 'coverage.html'],

            # No test suite description
            ['--use-phantomjs', '--use-chrome', '--use-firefox'],

            # Dev mode with multiple suites
            [self.TOOL_NAME, 'dev', 'test_suite_1.yaml', 'test_suite_2.yaml'],
        ]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_args(argv)
