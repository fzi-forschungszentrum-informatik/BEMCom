var objease = require('./../index.js');

module.exports = {
    name: 'split comparison',
    maxTime: 2,
    tests: {
        "split 3x3": function() {
            'abc.def.ghi'.split('.');
        },
        "objease.split 3x3": function() {
            objease.split('abc.def.ghi');
        },
        "objease.split 3x3 escaped": function() {
            objease.split('abc.d\\.f.ghi');
        },
        'objease split 8x3 with many backslashes': function () {
            objease.split('\\\\a\\\\.bbb.ccc.ddd.e\\.e.fff.ggg.h\\.h.\\\\\\');
        }
        /*
        "split 3x26": function() {
            'abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz'.split('.');
        },
        "oe.split 3x26": function() {
            oe.split('abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz');
        },
        "split 24x3": function() {
            'abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi'.split('.');
        },
        "oe.split 24x3": function() {
            oe.split('abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi.abc.def.ghi');
        },
        "split 24x26": function() {
            'abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz'.split('.');
        },
        "oe.split 24x26": function() {
            oe.split('abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz');
        }
*/
    }
};