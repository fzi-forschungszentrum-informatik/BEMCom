# obj-ease

[![NPM version](https://badge.fury.io/js/obj-ease.svg)](http://badge.fury.io/js/obj-ease)
[![Dependency Status](https://img.shields.io/gemnasium/hobbyquaker/obj-ease.svg?maxAge=2592000)](https://gemnasium.com/github.com/hobbyquaker/obj-ease)
[![Build Status](https://travis-ci.org/hobbyquaker/obj-ease.svg?branch=master)](https://travis-ci.org/hobbyquaker/obj-ease)
[![Coverage Status](https://coveralls.io/repos/github/hobbyquaker/obj-ease/badge.svg?branch=master)](https://coveralls.io/github/hobbyquaker/obj-ease?branch=master)
[![XO code style](https://img.shields.io/badge/code_style-XO-5ed9c7.svg)](https://github.com/sindresorhus/xo)
[![License][mit-badge]][mit-url]

[mit-badge]: https://img.shields.io/badge/License-MIT-blue.svg?style=flat
[mit-url]: LICENSE

> handle javascript objects with ease :surfer:


## Purpose

get/set/delete properties by dot-notation, clone, extend and compare objects.

> Why reinvent the wheel? There are more than enough modules solving the same problems!

Most of the implementations I found didn't suite my needs at 100% (e.g. useful return values, see below) and this module 
has also some educational purpose - I want to improve my js skills, so I would be glad and thankful to hear your opinion 
and critics on this implementation or - even better - get some pull requests that help to optimize performance, 
function, tooling, style and documentation of this module.


## Usage Examples

```Javascript
var oe = require('obj-ease');

var obj1 = {a: {b: {c: true}}};
console.log(oe.getProp(obj1, 'a.b.c')); // true
console.log(oe.getProp(obj1, 'a.b.missing')); // undefined

var obj2 = oe.clone(obj1);
console.log(oe.equal(obj1, obj2)); // true

oe.setProp(obj2, 'a.b.c', false);
console.log(oe.equal(obj1, obj2)); // false
console.log(oe.getProp(obj1, 'a.b.c')); // true

oe.extend(obj1, {a: {b: {bla: 'blub'}}});
console.log(obj1); // { a: { b: { c: true, bla: 'blub' } } }

oe.setProp(obj1, 'a.b', {c: null});
console.log(obj1); // { a: { b: { c: null } } }

oe.delProp(obj1, 'a.b');
console.log(obj1); // { a: {} }
```

## Advanced usage

### Return values

#### setProp 

setProp tells you if it really did a change on the object. So ```oe.setProp({a:1}, 'a', 1)``` will return false and ```oe.setProp({a:1}, 'a', 2)``` will return true. 


#### extend

extend returns an object containing all properties that changed on the target or undefined if no change happened. So ```oe.extend({a: {b: {x: 1, y: 2}}}, {a: {b: {x: 1, y: 3}}})``` will return ```{ a: { b: { y: 3 } } }```


### alternative usage on objects

You can attach the methods of obj-ease as non-enumerable properties to an object or an object prototype:

```Javascript
var db = {};
require('obj-ease').attach(db);

db.setProp('a.b.c', 'test!');
console.log(db); // { a: { b: { c: 'test!' } } }
```
Obviously the first param of all methods has to be omitted if used on an object.

One could also extend Object.prototype (really?): ```require('obj-ease').attach(Object.prototype);```


### Escaping

You can access properties with dots in their names simply by escaping them with backslashes.

```Javascript
var oe = require('obj-ease');

oe.setProp(obj, 'key\\.containing\\.dots.key\\\\containing\\\\backslashes\\.and\\.dots', 'test!');
console.log(obj); // { 'key.containing.dots': { 'key\\containing\\backslashes.and.dots': 'test!' } }
```


### Special Objects

This module works with Array and Buffer objects too. 

Until now it can not handle Function objects (see Todo). Handling of Date and RegExp objects is untested also.


## API
## Classes

<dl>
<dt><a href="#objease">objease</a></dt>
<dd></dd>
</dl>

## Functions

<dl>
<dt><a href="#attach
extends an object (prototype) with the obj-ease functions (non-enumerable)">attach
extends an object (prototype) with the obj-ease functions (non-enumerable)(obj)</a></dt>
<dd></dd>
<dt><a href="#split
Split str by . - supports backslash escaped delimiters">split
Split str by . - supports backslash escaped delimiters(str)</a> ⇒ <code>Array.&lt;string&gt;</code></dt>
<dd></dd>
<dt><a href="#delProp
delete an objects property. supports nested properties through dot-notation, dots may be escaped by backslash.">delProp
delete an objects property. supports nested properties through dot-notation, dots may be escaped by backslash.(obj, prop)</a> ⇒ <code>boolean</code></dt>
<dd></dd>
<dt><a href="#setProp
set an objects property. supports nested properties through dot-notation, dots may be escaped by backslash.">setProp
set an objects property. supports nested properties through dot-notation, dots may be escaped by backslash.(obj, prop, val)</a> ⇒ <code>boolean</code></dt>
<dd></dd>
<dt><a href="#getProp
get an objects property. supports nested properties through dot-notation, dots may be escaped by backslash">getProp
get an objects property. supports nested properties through dot-notation, dots may be escaped by backslash(obj, prop)</a> ⇒ <code>all</code></dt>
<dd></dd>
<dt><a href="#equal
compare objects by value">equal
compare objects by value(obj1, obj2)</a> ⇒ <code>boolean</code></dt>
<dd></dd>
<dt><a href="#clone
clone obj">clone
clone obj(obj)</a> ⇒ <code>Object</code> | <code>Array</code></dt>
<dd></dd>
<dt><a href="#extend
extend that by obj. observes if a change happens while extending">extend
extend that by obj. observes if a change happens while extending(that, obj)</a> ⇒ <code>undefined</code> | <code>Object</code></dt>
<dd></dd>
</dl>

<a name="objease"></a>

## objease
**Kind**: global class  
<a name="attach
extends an object (prototype) with the obj-ease functions (non-enumerable)"></a>

## attach
extends an object (prototype) with the obj-ease functions (non-enumerable)(obj)
**Kind**: global function  

| Param | Type | Description |
| --- | --- | --- |
| obj | <code>object</code> | object to extend |

<a name="split
Split str by . - supports backslash escaped delimiters"></a>

## split
Split str by . - supports backslash escaped delimiters(str) ⇒ <code>Array.&lt;string&gt;</code>
**Kind**: global function  

| Param | Type |
| --- | --- |
| str | <code>string</code> | 

<a name="delProp
delete an objects property. supports nested properties through dot-notation, dots may be escaped by backslash."></a>

## delProp
delete an objects property. supports nested properties through dot-notation, dots may be escaped by backslash.(obj, prop) ⇒ <code>boolean</code>
**Kind**: global function  
**Returns**: <code>boolean</code> - - true if property was found and deleted  

| Param | Type |
| --- | --- |
| obj | <code>Object</code> | 
| prop | <code>string</code> | 

<a name="setProp
set an objects property. supports nested properties through dot-notation, dots may be escaped by backslash."></a>

## setProp
set an objects property. supports nested properties through dot-notation, dots may be escaped by backslash.(obj, prop, val) ⇒ <code>boolean</code>
**Kind**: global function  
**Returns**: <code>boolean</code> - - true if a change on obj happened  

| Param | Type |
| --- | --- |
| obj | <code>Object</code> | 
| prop | <code>string</code> | 
| val | <code>all</code> | 

<a name="getProp
get an objects property. supports nested properties through dot-notation, dots may be escaped by backslash"></a>

## getProp
get an objects property. supports nested properties through dot-notation, dots may be escaped by backslash(obj, prop) ⇒ <code>all</code>
**Kind**: global function  
**Returns**: <code>all</code> - the properties value or undefined  

| Param | Type |
| --- | --- |
| obj | <code>Object</code> | 
| prop | <code>string</code> | 

<a name="equal
compare objects by value"></a>

## equal
compare objects by value(obj1, obj2) ⇒ <code>boolean</code>
**Kind**: global function  
**Returns**: <code>boolean</code> - true if both objects are equal  

| Param | Type |
| --- | --- |
| obj1 | <code>object</code> | 
| obj2 | <code>object</code> | 

<a name="clone
clone obj"></a>

## clone
clone obj(obj) ⇒ <code>Object</code> \| <code>Array</code>
**Kind**: global function  
**Returns**: <code>Object</code> \| <code>Array</code> - the cloned object  

| Param | Type |
| --- | --- |
| obj | <code>Object</code> \| <code>Array</code> | 

<a name="extend
extend that by obj. observes if a change happens while extending"></a>

## extend
extend that by obj. observes if a change happens while extending(that, obj) ⇒ <code>undefined</code> \| <code>Object</code>
**Kind**: global function  
**Returns**: <code>undefined</code> \| <code>Object</code> - undefined if no change happened - otherwise an object containing the changes is returned  

| Param | Type |
| --- | --- |
| that | <code>Object</code> | 
| obj | <code>Object</code> | 


## Todo

* Handling of Date and RegExp objects
* Handle function objects in a useful manner
* Gulp task bumping version and publishing to npm and bower
* More and better tests
* Better Readme
* optimize get/set/delProp performance by integrated split method (could break prop string loop earlier)
* Auto-generate markdown from benchmark results and insert into Readme
* More and better benchmarks


## License

MIT © [Sebastian Raff](https://github.com/hobbyquaker)
