const net = require('net');

function getPort(port, address, cb) {
    if (typeof address === 'function') {
        cb = address;
        address = '0.0.0.0'
    }
    const server = net.createServer();
    server.on('listening', function() {
        server.close();
    });
    server.on('close', () => {
        cb(port);
    });
    server.on('error', () => {
        port += 1;
        if (port <= 65535) {
            getPort(port, address, cb);
        } else {
            cb(null);
        }
    });
    server.listen(port, address)
}

module.exports = getPort;
