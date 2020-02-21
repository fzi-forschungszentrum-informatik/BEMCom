# nextport

> Node.js module to get the next free port

## Install

```
$ npm install nextport
```

## Usage

```javascript
const nextPort = require('getport');

nextPort(2000, port => {
    if (port) {
        console.log('next free port:', port);
    } else {
        console.log('no free port >= 2000 found');
    }
});

```

## License

MIT (c) Sebastian Raff
