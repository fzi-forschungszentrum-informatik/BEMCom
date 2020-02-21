var objease = require('./../index.js');



module.exports = {
    name: 'getProp comparison',
    maxTime: 2,
    tests: {
        "if      - undefined": function() {
            var obj;
            var tmp;
            if (obj && obj.a && obj.a.b && obj.a.b.c) tmp = obj.a.b.c.d;
        },
        "getProp - undefined": function() {
            var obj;
            var tmp = objease.getProp('a.b.c.d');
        },
        "if      - {a:null}": function() {
            var obj = {a:null};
            var tmp;
            if (obj && obj.a && obj.a.b && obj.a.b.c) tmp = obj.a.b.c.d;
        },
        "getProp - {a:null}": function() {
            var obj = {a:null};
            var tmp = objease.getProp('a.b.c.d');
        },
        "if      - {a:{b:{}}}": function() {
            var obj = {a:{b:{}}};
            var tmp;
            if (obj && obj.a && obj.a.b && obj.a.b.c) tmp = obj.a.b.c.d;
        },
        "getProp - {a:{b:{}}}": function() {
            var obj = {a:{b:{}}};
            var tmp = objease.getProp('a.b.c.d');
        }, 
        "if      - {a:{b:{c:{d:true}}}}": function() {
            var obj = {a:{b:{c:{d:true}}}};
            var tmp;
            if (obj && obj.a && obj.a.b && obj.a.b.c) tmp = obj.a.b.c.d;
        },
        "getProp - {a:{b:{c:{d:true}}}}": function() {
            var obj = {a:{b:{c:{d:true}}}};
            var tmp = objease.getProp('a.b.c.d');
        },
        

    }
};