const net = require('net');
const dgram = require('dgram');
const binary = require('binary');
const async = require('async');

function checkservice(host, port, callback) {
    const c = net.connect({
        port,
        host,
        timeout: this.timeout
    }, () => {
        if (typeof callback === 'function') {
            callback(null, true);
            callback = null;
            c.end();
        }
    });
    c.on('error', () => {
        if (typeof callback === 'function') {
            callback(null, false);
            callback = null;
        }
    });
}

function hmDiscover(options, callback) {
    if (typeof options === 'function') {
        callback = options;
        options = {};
    } else if (typeof options !== 'object') {
        options = {};
    }

    const timeout = options.timeout || 1200;
    const remoteport = 43439;
    const message = Buffer.from([0x02, 0x8F, 0x91, 0xC0, 0x01, 'e', 'Q', '3', 0x2D, 0x2A, 0x00, 0x2A, 0x00, 0x49]);
    const found = [];
    const foundAddresses = [];
    const client = dgram.createSocket('udp4');
    client.on('message', (msg, remote) => {
        binary.parse(msg)
            .buffer('header', 5)
            .scan('type', Buffer.from([0x00]))
            .scan('serial', Buffer.from([0x00]))
            .word8('byte0')
            .word8('byte1')
            .word8('byte2')
            .scan('version', Buffer.from([0x00]))
            .tap(data => {
                if (data.header.toString('hex') === '028f91c001') {
                    const device = {
                        type: String(data.type),
                        serial: String(data.serial),
                        version: String(data.version),
                        address: remote.address
                    };
                    if (foundAddresses.indexOf(remote.address) === -1) {
                        foundAddresses.push(remote.address);
                        async.parallel({
                            ReGaHSS: callback => {
                                checkservice(remote.address, 1999, callback);
                            },
                            'BidCos-Wired': callback => {
                                checkservice(remote.address, 2000, callback);
                            },
                            'BidCos-RF': callback => {
                                checkservice(remote.address, 2001, callback);
                            },
                            'HmIP-RF': callback => {
                                checkservice(remote.address, 2010, callback);
                            },
                            VirtualDevices: callback => {
                                checkservice(remote.address, 9292, callback);
                            },
                            CUxD: callback => {
                                checkservice(remote.address, 8701, callback);
                            }
                        }, (err, res) => { // eslint-disable-line handle-callback-err
                            device.interfaces = res;
                            found.push(device);
                        });
                    }
                }
            });
    });

    client.bind(() => {
        client.setBroadcast(true);
        client.send(message, 0, message.length, remoteport, '255.255.255.255');
    });

    setTimeout(() => {
        client.close();
        callback(found);
    }, timeout);
}

module.exports = hmDiscover;
