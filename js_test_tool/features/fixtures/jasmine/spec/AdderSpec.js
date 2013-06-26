describe("Adder", function() {

    var adder;

    beforeEach(function() {
        setFixtures('<div id="adder_output"></div>');
        adder = new Adder();
    });

    it('should start at zero', function() {
        expect(adder.sum).toEqual(0);
    });

    it('should add to the sum', function() {
        adder.add(5);
        expect(adder.sum).toEqual(5);
    });

    it('should keep a running total', function() {
        adder.add(2);
        adder.add(7);
        expect(adder.sum).toEqual(9);
    });

    it('should output to the DOM', function() {
        adder.add(3);
        adder.output();

        expect($('#adder_output').html()).toEqual('3');
    });
});
