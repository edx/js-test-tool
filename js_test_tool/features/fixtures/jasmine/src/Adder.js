function Adder() {
    this.sum = 0;
};

Adder.prototype.add = function(num) {
    this.sum += num;
};

Adder.prototype.output = function() {
    $('#adder_output').html(this.sum)
}
