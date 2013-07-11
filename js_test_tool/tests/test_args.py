import unittest
from js_test_tool.tool import parse_args
import tempfile
import os


class ParseArgsTest(unittest.TestCase):

    def test_parse_test_suite_file(self):
        argv = ['test_suite.yaml', '--use-phantomjs']
        arg_dict = parse_args(argv)

        self.assertEqual(arg_dict.get('test_suite_paths'), ['test_suite.yaml'])
        self.assertIs(arg_dict.get('coverage_xml'), None)
        self.assertIs(arg_dict.get('coverage_html'), None)

    def test_parse_test_suite_multiple_files(self):
        argv = ['test_suite_1.yaml', 'test_suite_2.yaml', '--use-chrome']
        arg_dict = parse_args(argv)

        self.assertEqual(arg_dict.get('test_suite_paths'),
                         ['test_suite_1.yaml', 'test_suite_2.yaml'])

    def test_parse_coverage_xml(self):
        argv = ['test_suite.yaml', '--coverage-xml',
                'coverage.xml', '--use-firefox']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('coverage_xml'), 'coverage.xml')

    def test_parse_coverage_html(self):
        argv = ['test_suite.yaml', '--coverage-html', 'coverage.html',
                '--use-firefox']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('coverage_html'), 'coverage.html')

    def test_parse_coverage_xml_and_html(self):
        argv = ['test_suite.yaml',
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
            argv = ['test_suite.yaml', browser_arg]
            arg_dict = parse_args(argv)
            self.assertEqual(arg_dict.get('browser_names'), [browser_name])

    def test_parse_all_browsers(self):

        argv = ['test_suite.yaml', '--use-phantomjs',
                '--use-chrome', '--use-firefox']

        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('browser_names'),
                         ['phantomjs', 'chrome', 'firefox'])

    def test_parse_invalid_arg(self):

        invalid_argv = [
            # No arguments
            [],

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
        ]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_args(argv)
