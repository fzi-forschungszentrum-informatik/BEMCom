#!/usr/bin/env node

let BufferBase62 = require('./buffer-base62');

let rawData = "let's have a try, this is a text that not encrypted";
{
    let bufferRawData = Buffer.from(rawData);
    console.log('bufferRawData', bufferRawData);
    let base62Data = BufferBase62.toBase62(bufferRawData);
    console.log('base62Data', base62Data);
    let restoreData = BufferBase62.fromBase62(base62Data);
    console.log('restoreData', restoreData.toString('utf-8'));
}
