Feature: Execute test suite in dev mode
    In order to debug JavaScript tests
    As a JavaScript developer
    I want to view test results and set script breakpoints in a browser.

    Scenario: Dev mode
        When I run js-test-tool in dev mode
        Then An HTML report of test results opens in the default browser
