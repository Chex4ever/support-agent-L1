// === Pattern: Sine Wave Generator for Linear Trend Testing ===
// Use in: Server project (init.js) to generate test data for Linear Trend widgets
//
// Server Tags written: sin1, sin2, sin3 (values between min/max)
// Configurable via Server Tags: sin{1..3}min, sin{1..3}max, sin-interval-ms
//
// Instructions:
// 1. Place in server project as init.js
// 2. Create Server Tags: sin1, sin2, sin3 (read on panel via Server.Tags.sin1 etc.)
// 3. Create Linear Trend widget bound to Server.Tags.sin1

var SIN_TICK = 6;

IR.AddListener(IR.EVENT_START, 0, function() {
    var interval = parseInt(IR.GetVariable("Server.Tags.sin-interval-ms")) || 1000;
    IR.SetInterval(interval, function() {
        for (var i = 1; i <= 3; i++) {
            var min  = parseFloat(IR.GetVariable("Server.Tags.sin" + i + "min")) || 0;
            var max  = parseFloat(IR.GetVariable("Server.Tags.sin" + i + "max")) || 3;
            var ph   = parseFloat(IR.GetVariable("Server.Tags.sin" + i + "phase"));
            if (isNaN(ph)) ph = i * SIN_TICK * 10;
            var mid  = (min + max) / 2;
            var amp  = (max - min) / 2;
            IR.GetServer().Set("sin" + i, mid + amp * Math.sin(ph * Math.PI / 180));
            ph += SIN_TICK;
            if (ph >= 360) ph -= 360;
            IR.GetServer().Set("sin" + i + "phase", ph);
        }
    });
});

IR.GetServer().Set("sin1", 0);
