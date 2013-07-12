describe("Failer", function() {

    it('should have one test that passes', function() {
        expect(1 + 1).toEqual(2);
    });

    it('should have one test that fails', function() {
        expect(2 + 2).toEqual(5);
    });
});
