# buffer-base62
This library will transform the binary buffer to base62 string that used 62 character to describe any data

# Usage

```javascript
let BufferBase62 = require('./buffer-base62');

let rawData = "let's have a try, this is a text that not encrypted";
{
    let bufferRawData = Buffer.from(rawData);
    console.log('bufferRawData', bufferRawData);  //output: bufferRawData <Buffer 6c 65 74 27 73 20 68 61 76 65 20 61 20 74 72 79 2c 20 74 68 69 73 20 69 73 20 61 20 74 65 78 74 20 74 68 61 74 20 6e 6f 74 20 65 6e 63 72 79 70 74 65 ... >
    let base62Data = BufferBase62.toBase62(bufferRawData);
    console.log('base62Data', base62Data); //output: base62Data 3fO7Uqb2oHZjEALizByUEmtsJq86GWI6W3h0OxRZZXVGqiBeoM4bwZf7DuKh4EpfaHcEG
    let restoreData = BufferBase62.fromBase62(base62Data);
    console.log('restoreData', restoreData.toString('utf-8')); //output restoreData let's have a try, this is a text that not encrypted
}
```

