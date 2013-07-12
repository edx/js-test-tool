Feature: Report test suite results
    In order to improve software quality
    As a JavaScript developer
    I want to run JavaScript unit tests and view test results.

    Scenario: Jasmine tests
        When I run js-test-tool without coverage
        Then I see the test suite results
