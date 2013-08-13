"""
Steps for the Lettuce BDD specs.
"""

from lettuce import step, world
from nose.tools import assert_true


TEST_SUITE_DESC_PATH = 'jasmine/test_suite.yaml'
PASSING_SUITE_DESC_PATH = 'passing/test_suite.yaml'
FAILING_SUITE_DESC_PATH = 'failing/test_suite.yaml'

ACTUAL_COVERAGE_XML = 'js_coverage.xml'
ACTUAL_COVERAGE_HTML = 'js_coverage.html'
EXPECTED_COVERAGE_XML = 'expected/expected_js_coverage.xml'
EXPECTED_COVERAGE_HTML = 'expected/expected_js_coverage.html'
EXPECTED_TEST_REPORT = 'expected/expected_test_report.txt'


@step(u'When I run js-test-tool without coverage')
def run_tool_with_no_coverage(step):
    world.run_tool_with_args(['run', TEST_SUITE_DESC_PATH,
                              '--timeout', '2'])


@step(u'When I run js-test-tool with XML coverage')
def run_tool_with_xml_coverage(step):
    args = ['run', TEST_SUITE_DESC_PATH,
            '--coverage-xml', ACTUAL_COVERAGE_XML,
            '--timeout', '2']
    world.run_tool_with_args(args)


@step(u'When I run js-test-tool with HTML coverage')
def run_tool_with_html_coverage(step):
    args = ['run', TEST_SUITE_DESC_PATH,
            '--coverage-html', ACTUAL_COVERAGE_HTML,
            '--timeout', '2']
    world.run_tool_with_args(args)


@step(u'When I run js-test-tool with XML and HTML coverage')
def run_tool_with_html_coverage(step):
    args = ['run', TEST_SUITE_DESC_PATH,
            '--coverage-html', ACTUAL_COVERAGE_HTML,
            '--coverage-xml', ACTUAL_COVERAGE_XML,
            '--timeout', '2']
    world.run_tool_with_args(args)


@step(u'When I run js-test-tool with a passing test suite')
def run_tool_with_passing_test_suite(step):
    world.run_tool_with_args(['run', PASSING_SUITE_DESC_PATH])


@step(u'When I run js-test-tool with a failing test suite')
def run_tool_with_failing_test_suite(step):
    world.run_tool_with_args(['run', FAILING_SUITE_DESC_PATH,
                              '--timeout', '2'])


@step(u'When I run js-test-tool in dev mode')
def run_tool_in_dev_mode(step):

    # Patch the call to webbrowser.open_new()
    # Use this to raise a KeyboardInterrupt (so the tool terminates)
    # while checking that the page loads correctly
    def load_page_and_exit(url):
        world.load_page(url)
        raise KeyboardInterrupt

    world.mock_webbrowser.open_new.side_effect = load_page_and_exit
    world.run_tool_with_args(['dev', TEST_SUITE_DESC_PATH])


@step(u'Then An XML coverage report is generated')
def check_xml_coverage_report(step):
    world.compare_files_at_paths(ACTUAL_COVERAGE_XML, EXPECTED_COVERAGE_XML)


@step(u'Then An HTML coverage report is generated')
def check_html_coverage_report(step):
    world.compare_files_at_paths(ACTUAL_COVERAGE_HTML, EXPECTED_COVERAGE_HTML)


@step(u'Then No coverage reports are generated')
def check_no_coverage_report(step):
    world.assert_no_file(ACTUAL_COVERAGE_XML)
    world.assert_no_file(ACTUAL_COVERAGE_HTML)


@step(u'Then I see the test suite results')
def check_test_suite_results(step):
    world.assert_tool_stdout(EXPECTED_TEST_REPORT)


@step(u'Given Coverage dependencies are configured')
def configure_coverage_dependencies(step):
    world.set_jscover(True)


@step(u'Given Coverage dependencies are missing')
def disable_coverage_dependencies(step):
    world.set_jscover(False)


@step(u'Then The tool exits with status "([^"]*)"')
def exits_with_status(step, status_code):
    world.assert_exit_code(status_code)


@step(u'When I run js-test-tool init')
def when_i_run_js_test_tool_init(step):
    args = ['init', 'js_test_suite.yml']
    world.run_tool_with_args(args)


@step(u'Then A default test suite description is created')
def then_a_default_test_suite_description_is_created(step):
    world.assert_file_exists('js_test_suite.yml')


@step(u'Then An HTML report of test results opens in the default browser')
def display_html_report_in_browser(step):

    # Our patched `webbrowser.open_new()` should have used
    # `world.browser()` (a Splinter browser) to load the dev
    # test suite page.

    # Verify that the Jasmine HTMLReporter ran
    assert_true(world.browser.is_element_present_by_id('HTMLReporter'))
