Feature: Report test suite results
    In order to improve software quality
    As a JavaScript developer
    I want to run JavaScript unit tests and view test results.

    Scenario: Jasmine tests
        When I run js-test-tool on Jasmine without coverage
        Then I see the test suite results

    Scenario: Jasmine-Requirejs tests
        When I run js-test-tool on requirejs without coverage
        Then I see the test suite results

    Scenario: XUnit reports
        When I run js-test-tool and specify an XUnit report path
        Then An XUnit report is generated
