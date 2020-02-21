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

