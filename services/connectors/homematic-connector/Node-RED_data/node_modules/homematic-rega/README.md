# homematic-rega

[![NPM version](https://badge.fury.io/js/homematic-rega.svg)](http://badge.fury.io/js/homematic-rega)
[![dependencies Status](https://david-dm.org/hobbyquaker/homematic-rega/status.svg)](https://david-dm.org/hobbyquaker/homematic-rega)
[![Build Status](https://travis-ci.org/hobbyquaker/homematic-rega.svg?branch=master)](https://travis-ci.org/hobbyquaker/homematic-rega)
[![XO code style](https://img.shields.io/badge/code_style-XO-5ed9c7.svg)](https://github.com/sindresorhus/xo)
[![License][mit-badge]][mit-url]

> Node.js Homematic CCU ReGaHSS Remote Script Interface

This module encapsulates the communication with the "ReGaHSS" - the logic layer of the Homematic CCU. 

* execute arbitrary scripts
* get names and ids of devices and channels
* get variables including their value und meta data
* set variable values
* get programs
* execute programs
* activate/deactivate programs
* get rooms and functions including assigned channels
* rename objects

i18n placeholders (e.g. `${roomKitchen}`) are translated by default.

You can find offical and inoffical documentation of the homematic scripting language at 
[wikimatic.de](http://www.wikimatic.de/wiki/Script_Dokumentation).

Pull Requests welcome! :)


## Install

`$ npm install homematic-rega`


## Usage Example

```javascript
const Rega = require('homematic-rega');

const rega = new Rega({host: '192.168.2.105'});

rega.exec('string x = "Hello";\nWriteLine(x # " World!");', (err, output, objects) => {
    if (err) {
        throw err;
    } 
    console.log('Output:', output);
    console.log('Objects:', objects);
});

rega.getVariables((err, res) => {
    console.log(res);
});
```


## API

<a name="Rega"></a>

## Rega
**Kind**: global class  

* [Rega](#Rega)
    * [new Rega(options)](#new_Rega_new)
    * _instance_
        * [.exec(script, [callback])](#Rega+exec)
        * [.script(file, [callback])](#Rega+script)
        * [.getChannels(callback)](#Rega+getChannels)
        * [.getValues(callback)](#Rega+getValues)
        * [.getPrograms(callback)](#Rega+getPrograms)
        * [.getVariables(callback)](#Rega+getVariables)
        * [.getRooms(callback)](#Rega+getRooms)
        * [.getFunctions(callback)](#Rega+getFunctions)
        * [.setVariable(id, val, [callback])](#Rega+setVariable)
        * [.startProgram(id, [callback])](#Rega+startProgram)
        * [.setProgram(id, active, [callback])](#Rega+setProgram)
        * [.setName(id, name, [callback])](#Rega+setName)
    * _inner_
        * [~scriptCallback](#Rega..scriptCallback) : <code>function</code>

<a name="new_Rega_new"></a>

### new Rega(options)

| Param | Type | Default | Description |
| --- | --- | --- | --- |
| options | <code>object</code> |  |  |
| options.host | <code>string</code> |  | hostname or IP address of the Homematic CCU |
| [options.language] | <code>string</code> | <code>&quot;de&quot;</code> | language used for translation of placeholders in variables/rooms/functions |
| [options.disableTranslation] | <code>boolean</code> | <code>false</code> | disable translation of placeholders |
| [options.tls] | <code>boolean</code> | <code>false</code> | Connect using TLS |
| [options.inSecure] | <code>boolean</code> | <code>false</code> | Ignore invalid TLS Certificates |
| [options.auth] | <code>boolean</code> | <code>false</code> | Use Basic Authentication |
| [options.user] | <code>string</code> |  | Auth Username |
| [options.pass] | <code>string</code> |  | Auth Password |
| [options.port] | <code>number</code> | <code>8181</code> | rega remote script port. Defaults to 48181 if options.tls is true |

<a name="Rega+exec"></a>

### rega.exec(script, [callback])
Execute a rega script

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type | Description |
| --- | --- | --- |
| script | <code>string</code> | string containing a rega script |
| [callback] | [<code>scriptCallback</code>](#Rega..scriptCallback) |  |

<a name="Rega+script"></a>

### rega.script(file, [callback])
Execute a rega script from a file

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type | Description |
| --- | --- | --- |
| file | <code>string</code> | path to script file |
| [callback] | [<code>scriptCallback</code>](#Rega..scriptCallback) |  |

<a name="Rega+getChannels"></a>

### rega.getChannels(callback)
Get all devices and channels

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| callback | <code>Rega~channelCallback</code> | 

<a name="Rega+getValues"></a>

### rega.getValues(callback)
Get all devices and channels values

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| callback | <code>Rega~valuesCallback</code> | 

<a name="Rega+getPrograms"></a>

### rega.getPrograms(callback)
Get all programs

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| callback | <code>Rega~programsCallback</code> | 

<a name="Rega+getVariables"></a>

### rega.getVariables(callback)
Get all variables

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| callback | <code>Rega~variablesCallback</code> | 

<a name="Rega+getRooms"></a>

### rega.getRooms(callback)
Get all rooms

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| callback | <code>Rega~roomsCallback</code> | 

<a name="Rega+getFunctions"></a>

### rega.getFunctions(callback)
Get all functions

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| callback | <code>Rega~functionsCallback</code> | 

<a name="Rega+setVariable"></a>

### rega.setVariable(id, val, [callback])
Set a variables value

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| id | <code>number</code> | 
| val | <code>number</code> \| <code>boolean</code> \| <code>string</code> | 
| [callback] | <code>function</code> | 

<a name="Rega+startProgram"></a>

### rega.startProgram(id, [callback])
Execute a program

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| id | <code>number</code> | 
| [callback] | <code>function</code> | 

<a name="Rega+setProgram"></a>

### rega.setProgram(id, active, [callback])
Activate/Deactivate a program

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| id | <code>number</code> | 
| active | <code>boolean</code> | 
| [callback] | <code>function</code> | 

<a name="Rega+setName"></a>

### rega.setName(id, name, [callback])
Rename an object

**Kind**: instance method of [<code>Rega</code>](#Rega)  

| Param | Type |
| --- | --- |
| id | <code>number</code> | 
| name | <code>string</code> | 
| [callback] | <code>function</code> | 

<a name="Rega..scriptCallback"></a>

### Rega~scriptCallback : <code>function</code>
**Kind**: inner typedef of [<code>Rega</code>](#Rega)  

| Param | Type | Description |
| --- | --- | --- |
| err | <code>Error</code> |  |
| output | <code>string</code> | the scripts output |
| variables | <code>Object.&lt;string, string&gt;</code> | contains all variables that are set in the script (as strings) |


## Related projects

* [node-red-contrib-ccu](https://github.com/hobbyquaker/node-red-contrib-ccu) - Node-RED nodes for the Homematic CCU.
* [homematic-manager](https://github.com/hobbyquaker/homematic-manager) - Cross-platform App to manage Homematic devices 
and links.
* [hm2mqtt.js](https://github.com/hobbyquaker/hm2mqtt.js) - Interface between Homematic and MQTT.
* [binrpc](https://github.com/hobbyquaker/binrpc) - Node.js client/server for the Homematic BINRPC protocol.
* [homematic-xmlrpc](https://github.com/hobbyquaker/homematic-xmlrpc) - Node.js client/server for the Homematic XMLRPC 
protocol.


## License

MIT (c) Sebastian Raff

[mit-badge]: https://img.shields.io/badge/License-MIT-blue.svg?style=flat
[mit-url]: LICENSE
