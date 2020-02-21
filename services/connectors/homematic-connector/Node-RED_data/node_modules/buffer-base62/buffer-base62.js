let BufferBase62 = module.exports = {}
var BigNumber = require('big-number');
var reverseInplace = require("buffer-reverse/inplace")
var _ = require('underscore');



let m_base62Mapping = new Array(
	'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A',
	'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
	'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
	'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e',
	'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
	'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'
);

let m_base62MappingRev = new Map(
	[['0' , 0 ],
    ['1' , 1 ],
    ['2' , 2 ],
    ['3' , 3 ],
    ['4' , 4 ],
    ['5' , 5 ],
    ['6' , 6 ],
    ['7' , 7 ],
    ['8' , 8 ],
    ['9' , 9 ],
    ['A' , 10],
	['B' , 11],
    ['C' , 12],
    ['D' , 13],
    ['E' , 14],
    ['F' , 15],
    ['G' , 16],
    ['H' , 17],
    ['I' , 18],
    ['J' , 19],
    ['K' , 20],
	['L' , 21],
    ['M' , 22],
    ['N' , 23],
    ['O' , 24],
    ['P' , 25],
    ['Q' , 26],
    ['R' , 27],
    ['S' , 28],
    ['T' , 29],
    ['U' , 30],
	['V' , 31],
    ['W' , 32],
    ['X' , 33],
    ['Y' , 34],
    ['Z' , 35],
    ['a' , 36],
    ['b' , 37],
    ['c' , 38],
    ['d' , 39],
    ['e' , 40],
	['f' , 41],
    ['g' , 42],
    ['h' , 43],
    ['i' , 44],
    ['j' , 45],
    ['k' , 46],
    ['l' , 47],
    ['m' , 48],
    ['n' , 49],
    ['o' , 50],
	['p' , 51],
    ['q' , 52],
    ['r' , 53],
    ['s' , 54],
    ['t' , 55],
    ['u' , 56],
    ['v' , 57],
    ['w' , 58],
    ['x' , 59],
    ['y' , 60],
    ['z' , 61]]
);

function setBase62Mapping(arrayMapping) {
    m_base62Mapping = arrayMapping;
    m_base62MappingRev = new Map();
    for (let i = 0; i < m_base62Mapping.length; i++) {
        m_base62MappingRev.set(m_base62Mapping[i], i);
    }
}

BufferBase62.setBase62Mapping = setBase62Mapping;


function fromBase62(str) {
    let number = BigNumber(0);
    for (let i = 0; i < str.length; i++) {
        let curNum = m_base62MappingRev.get(str[i]);
        let pos = str.length-i-1;
        number = number.plus(BigNumber(62).pow(pos).multiply(curNum));
    }
    let retBuffer = Buffer.alloc(512);
    let offset = 0;
    while(number.gt(255)) {
        let cur = number.mod(256);
        retBuffer.writeUInt8(cur, offset++);
    }
    retBuffer.writeUInt8(parseInt(number.val()), offset++);
    retBuffer = retBuffer.slice(0, offset);
    reverseInplace(retBuffer);
    return retBuffer;
}
BufferBase62.fromBase62 = fromBase62;

function toBase62(buffer) {
    let number = toBigNumber(buffer);
    let outArray = new Array();
	while (number.gt(61)) {
		let cur = number.mod(62);
		outArray.push(m_base62Mapping[cur]);
	}
	outArray.push(m_base62Mapping[parseInt(number.val())]);
    outArray.reverse();
	return outArray.join('');
}
BufferBase62.toBase62 = toBase62;

function toBigNumber(buffer) {
    let number = BigNumber(0);
    for (let offset = 0; offset < buffer.length; offset++) {
        let curNum = buffer.readUInt8(offset);
        let pos = buffer.length-offset-1;
        number = number.plus(BigNumber(256).pow(pos).multiply(curNum));
    }
    return number;
}
BufferBase62.toBigNumber = toBigNumber;
