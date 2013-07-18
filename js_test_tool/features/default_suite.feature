Feature: Create default test suite description
    In order to quickly define new test suites
    As a JavaScript developer
    I want to create a default test suite description.

    Scenario: Create default suite description
        When I run js-test-tool init
        Then A default test suite description is created
