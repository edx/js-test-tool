Feature: Exit code indicates success
    In order to use the tool in Continuous Integration
    As a Test Engineer
    I want the exit code to indicate whether all tests passed.

    Scenario: All tests pass
        When I run js-test-tool with a passing test suite
        Then The tool exits with status "0"

    Scenario: Some tests fail
        When I run js-test-tool with a failing test suite
        Then The tool exits with status "1"
