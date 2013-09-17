"""
Steps for the Lettuce BDD specs.
"""

from lettuce import step, world
from nose.tools import assert_true

RUNNER_ALIASES = {
    "requirejs": "jasmine_requirejs",
}


def config_path(runner="jasmine", suite="base"):
    normalized = RUNNER_ALIASES.get(runner.lower(), runner.lower())
    return "{runner}/{suite}/test_suite.yaml".format(
        runner=normalized, suite=suite)


def test_report_path(runner="jasmine"):
    normalized = RUNNER_ALIASES.get(runner.lower(), runner.lower())
    return "expected/{runner}_test_report.txt".format(runner=normalized)


def coverage_path(runner="jasmine", format="xml", actual=False):
    if actual:
        tpl = "js_coverage.{format}"
    else:
        tpl = "expected/{runner}_js_coverage.{format}"
    normalized = RUNNER_ALIASES.get(runner.lower(), runner.lower())
    return tpl.format(runner=normalized, format=format.lower())


@step(u'When I run js-test-tool on (Jasmine|requirejs) without coverage')
def run_tool_with_no_coverage(step, runner):
    world.scenario["runner"] = runner
    world.run_tool_with_args(['run', config_path(runner),
                              '--timeout', '2'])


@step(u'When I run js-test-tool on (Jasmine|requirejs) with (XML|HTML) coverage')
def run_tool_with_coverage(step, runner, format):
    world.scenario["runner"] = runner
    args = ['run', config_path(runner),
            '--coverage-{format}'.format(format=format.lower()),
            coverage_path(runner, format, actual=True),
            '--timeout', '2']
    world.run_tool_with_args(args)


@step(u'When I run js-test-tool on (Jasmine|requirejs) with (XML and HTML|HTML and XML) coverage')
def run_tool_with_html_xml_coverage(step, runner, _ordering):
    world.scenario["runner"] = runner
    args = ['run', config_path(runner),
            '--coverage-html', coverage_path(runner, "html", actual=True),
            '--coverage-xml', coverage_path(runner, "xml", actual=True),
            '--timeout', '2']
    world.run_tool_with_args(args)


@step(u'When I run js-test-tool with a passing test suite')
def run_tool_with_passing_test_suite(step):
    world.run_tool_with_args(['run', config_path("jasmine", "passing")])


@step(u'When I run js-test-tool with a failing test suite')
def run_tool_with_failing_test_suite(step):
    world.run_tool_with_args(['run', config_path("jasmine", "failing"),
                              '--timeout', '2'])


@step(u'When I run js-test-tool on (Jasmine|requirejs) in dev mode')
def run_tool_in_dev_mode(step, runner):
    world.scenario["runner"] = runner

    # Patch the call to webbrowser.open_new()
    # Use this to raise a KeyboardInterrupt (so the tool terminates)
    # while checking that the page loads correctly
    def load_page_and_exit(url):
        world.load_page(url)
        raise KeyboardInterrupt

    world.mock_webbrowser.open_new.side_effect = load_page_and_exit
    world.run_tool_with_args(['dev', config_path(runner)])


@step(u'Then An? (XML|HTML) coverage report is generated')
def check_coverage_report(step, format):
    runner = world.scenario["runner"]
    world.compare_files_at_paths(
        coverage_path(runner, format, actual=False),
        coverage_path(runner, format, actual=True),
    )


@step(u'Then No coverage reports are generated')
def check_no_coverage_report(step):
    runner = world.scenario["runner"]
    world.assert_no_file(coverage_path(runner, "xml", actual=True))
    world.assert_no_file(coverage_path(runner, "html", actual=True))


@step(u'Then I see the test suite results')
def check_test_suite_results(step):
    runner = world.scenario["runner"]
    world.assert_tool_stdout(test_report_path(runner))


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
