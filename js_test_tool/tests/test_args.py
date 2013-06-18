import unittest
from js_test_tool.tool import parse_args
import tempfile
import os


class ParseArgsTest(unittest.TestCase):

    TEST_SUITE_DATA = 'Test suite description data.'

    def setUp(self):
        """
        Create a temporary test description file for the argument parser.
        """
        (_, self.test_file_path) = tempfile.mkstemp()

        # Write some data to the file
        with open(self.test_file_path, 'w') as test_file:
            test_file.write(self.TEST_SUITE_DATA)

    def tearDown(self):

        # Delete the temporary file we created earlier
        os.remove(self.test_file_path)

    def test_parse_test_suite_file(self):
        argv = [self.test_file_path]
        arg_dict = parse_args(argv)

        # Read the data from the file
        test_file = arg_dict.get('test_suite_desc')
        test_data = test_file.read()
        test_file.close()

        self.assertEqual(test_data, self.TEST_SUITE_DATA)
        self.assertIs(arg_dict.get('coverage_xml'), None)
        self.assertIs(arg_dict.get('coverage_html'), None)

    def test_parse_coverage_xml(self):
        argv = [self.test_file_path, '--coverage-xml', 'coverage.xml']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('coverage_xml'), 'coverage.xml')

    def test_parse_coverage_html(self):
        argv = [self.test_file_path, '--coverage-html', 'coverage.html']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('coverage_html'), 'coverage.html')

    def test_parse_coverage_xml_and_html(self):
        argv = [self.test_file_path,
                '--coverage-xml', 'coverage.xml',
                '--coverage-html', 'coverage.html']
        arg_dict = parse_args(argv)
        self.assertEqual(arg_dict.get('coverage_xml'), 'coverage.xml')
        self.assertEqual(arg_dict.get('coverage_html'), 'coverage.html')

    def test_no_such_file(self):
        argv = ['no_such_file.yaml']

        with self.assertRaises(IOError):
            parse_args(argv)

    def test_parse_invalid_arg(self):

        invalid_argv = [
            # No arguments
            [],

            # No test suite description
            ['--coverage-xml', 'coverage.xml'],

            # No test suite description
            ['--coverage-html', 'coverage.html'],

            # No test suite description
            ['--coverage-xml', 'coverage.xml',
            '--coverage-html', 'coverage.html'],

            # Too many test suite descriptions
            [self.test_file_path, self.test_file_path]]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_args(argv)
