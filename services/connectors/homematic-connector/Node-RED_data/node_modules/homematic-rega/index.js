const fs = require('fs');
const path = require('path');

const tempDir = require('temp-dir');
const request = require('request');
const iconv = require('iconv-lite');
const parseXml = require('xml2js').parseString;

class Rega {
    /**
     * @param {object} options
     * @param {string} options.host - hostname or IP address of the Homematic CCU
     * @param {string} [options.language=de] - language used for translation of placeholders in variables/rooms/functions
     * @param {boolean} [options.disableTranslation=false] - disable translation of placeholders
     * @param {boolean} [options.tls=false] - Connect using TLS
     * @param {boolean} [options.inSecure=false] - Ignore invalid TLS Certificates
     * @param {boolean} [options.auth=false] - Use Basic Authentication
     * @param {string} [options.user] - Auth Username
     * @param {string} [options.pass] - Auth Password
     * @param {number} [options.port=8181] - rega remote script port. Defaults to 48181 if options.tls is true
     */
    constructor(options) {
        this.language = options.language || 'de';
        this.disableTranslation = options.disableTranslation;
        this.host = options.host;
        this.tls = options.tls;
        this.port = options.port || (this.tls ? 48181 : 8181);
        this.inSecure = options.inSecure;
        this.auth = options.auth;
        this.user = options.user;
        this.pass = options.pass;
        this.url = (this.tls ? 'https' : 'http') + '://' + this.host + ':' + this.port + '/rega.exe';
        this.encoding = 'iso-8859-1';
        this.requestOptions = {
            method: 'POST',
            url: this.url,
            encoding: null
        };
        if (this.auth) {
            this.requestOptions.auth = {
                user: this.user,
                pass: this.pass,
                sendImmediately: true
            };
        }

        if (this.tls) {
            this.requestOptions.strictSSL = !this.inSecure;
        }
    }

    /**
     * @callback Rega~scriptCallback
     * @param {?Error} err
     * @param {string} output - the scripts output
     * @param {Object.<string, string>} variables - contains all variables that are set in the script (as strings)
     */

    _parseResponse(res, callback) {
        const ERROR_XML_MISSING = new Error('xml in rega response missing');
        if (res) {
            const outputEnd = res.lastIndexOf('<xml>');
            if (outputEnd === -1) {
                callback(ERROR_XML_MISSING);
            } else {
                const output = res.slice(0, outputEnd);
                const xml = res.slice(outputEnd);
                if (xml) {
                    parseXml(xml, {explicitArray: false}, (err, res) => {
                        if (err) {
                            callback(err, output);
                        } else if (res) {
                            callback(null, output, res.xml);
                        } else {
                            callback(ERROR_XML_MISSING);
                        }
                    });
                } else {
                    callback(ERROR_XML_MISSING);
                }
            }
        } else {
            callback(new Error('empty rega response'));
        }
    }

    /**
     * Execute a rega script
     * @method Rega#exec
     * @param {string} script - string containing a rega script
     * @param {Rega~scriptCallback} [callback]
     */
    exec(script, callback) {
        if (typeof callback !== 'function') {
            callback = () => {};
        }

        script = iconv.encode(script, this.encoding);
        request(Object.assign(this.requestOptions, {
            body: script,
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Content-Length': script.length
            }
        }), (err, res, body) => {
            if (!err && body) {
                if (res.statusCode === 401) {
                    callback(new Error('401 Unauthorized'));
                } else {
                    body = iconv.decode(body, this.encoding);
                    this._parseResponse(body, callback);
                }
            } else {
                callback(err);
            }
        });
    }

    /**
     * Execute a rega script from a file
     * @method Rega#script
     * @param {string} file - path to script file
     * @param {Rega~scriptCallback} [callback]
     */
    script(file, callback) {
        // TODO cache files
        fs.readFile(file, (err, res) => {
            if (err) {
                if (typeof callback === 'function') {
                    callback(err);
                }
            } else {
                this.exec(res.toString(), callback);
            }
        });
    }

    _jsonScript(file, callback) {
        this.script(file, (err, res) => {
            if (err) {
                callback(err);
            } else {
                try {
                    callback(null, JSON.parse(res));
                } catch (_) {
                    const debugFile = path.join(tempDir, path.basename(file) + '.failed.json');
                    fs.writeFile(debugFile, res, () => {});
                    callback(new Error('JSON.parse failed. Saved debug data to ' + debugFile));
                }
            }
        });
    }

    /**
     * Get all devices and channels
     * @method Rega#getChannels
     * @param {Rega~channelCallback} callback
     */
    getChannels(callback) {
        this._jsonScript(path.join(__dirname, 'scripts', 'channels.rega'), (err, res) => {
            if (err) {
                callback(err, res);
            } else {
                res.forEach((channel, index) => {
                    channel.name = unescape(channel.name);
                    res[index] = channel;
                });
                callback(null, res);
            }
        });
    }

    /**
     * Get all devices and channels values
     * @method Rega#getValues
     * @param {Rega~valuesCallback} callback
     */
    getValues(callback) {
        this._jsonScript(path.join(__dirname, 'scripts', 'values.rega'), (err, res) => {
            if (err) {
                callback(err, res);
            } else {
                res.forEach((ch, index) => {
                    ch.name = unescape(ch.name);
                    if (typeof ch.value === 'string') {
                        ch.value = unescape(ch.value);
                    }

                    res[index] = ch;
                });
                callback(null, res);
            }
        });
    }

    /**
     * Get all programs
     * @method Rega#getPrograms
     * @param {Rega~programsCallback} callback
     */
    getPrograms(callback) {
        this._jsonScript(path.join(__dirname, 'scripts', 'programs.rega'), (err, res) => {
            if (err) {
                callback(err, res);
            } else {
                res.forEach((prg, index) => {
                    prg.name = unescape(prg.name);
                    prg.info = unescape(prg.info);
                    res[index] = prg;
                });
                callback(null, res);
            }
        });
    }

    _getTranslations(callback) {
        const url = 'http://' + this.host + '/webui/js/lang/' + this.language + '/translate.lang.extension.js';
        this.translations = {};
        request({
            method: 'GET',
            url,
            encoding: null
        }, (err, res, body) => {
            if (!err && body) {
                this._parseTranslations(iconv.decode(body, this.encoding));
            }

            callback();
        });
    }

    _parseTranslations(body) {
        const lines = body.split('\n');
        lines.forEach(line => {
            const match = line.match(/\s*"((func|room|sysVar)[^"]+)"\s*:\s*"([^"]+)"/);
            if (match) {
                this.translations[match[1]] = unescape(match[3]); // TODO replace deprecated unescape
            }
        });
    }

    _translate(item) {
        if (!this.disableTranslation) {
            let key = item;
            if (key.startsWith('${') && key.endsWith('}')) {
                key = key.slice(2, item.length - 1);
            }

            if (this.translations[key]) {
                item = this.translations[key];
            }
        }

        return item;
    }

    _translateNames(res) {
        if (!this.disableTranslation) {
            Object.keys(res).forEach(id => {
                const obj = res[id];
                obj.name = this._translate(unescape(obj.name));
                if (obj.info) {
                    obj.info = this._translate(unescape(obj.info));
                }
            });
        }

        return res;
    }

    _translateEnum(values) {
        if (!this.disableTranslation) {
            values.forEach((val, i) => {
                values[i] = this._translate(val);
            });
        }

        return values;
    }

    _translateJsonScript(file, callback) {
        if (this.translations || this.disableTranslation) {
            this._jsonScript(file, (err, res) => {
                if (err) {
                    callback(err);
                } else {
                    callback(null, this.disableTranslation ? res : this._translateNames(res));
                }
            });
        } else {
            this._getTranslations(() => {
                this._translateJsonScript(file, callback);
            });
        }
    }

    /**
     * Get all variables
     * @method Rega#getVariables
     * @param {Rega~variablesCallback} callback
     */
    getVariables(callback) {
        this._translateJsonScript(path.join(__dirname, 'scripts', 'variables.rega'), (err, res) => {
            if (err) {
                callback(err);
            } else {
                res.forEach((sysvar, index) => {
                    if (sysvar.type === 'string') {
                        sysvar.val = unescape(sysvar.val);
                    }

                    if (sysvar.enum === '') {
                        sysvar.enum = [];
                    } else {
                        sysvar.enum = this._translateEnum(unescape(sysvar.enum).split(';'));
                    }

                    res[index] = sysvar;
                });
                callback(null, res);
            }
        });
    }

    /**
     * Get all rooms
     * @method Rega#getRooms
     * @param {Rega~roomsCallback} callback
     */
    getRooms(callback) {
        this._translateJsonScript(path.join(__dirname, 'scripts', 'rooms.rega'), callback);
    }

    /**
     * Get all functions
     * @method Rega#getFunctions
     * @param {Rega~functionsCallback} callback
     */
    getFunctions(callback) {
        this._translateJsonScript(path.join(__dirname, 'scripts', 'functions.rega'), callback);
    }

    /**
     * Set a variables value
     * @method Rega#setVariable
     * @param {number} id
     * @param {number|boolean|string} val
     * @param {function} [callback]
     */
    setVariable(id, val, callback) {
        const script = 'dom.GetObject(' + id + ').State(' + JSON.stringify(val) + ');';
        this.exec(script, callback);
    }

    /**
     * Execute a program
     * @method Rega#startProgram
     * @param {number} id
     * @param {function} [callback]
     */
    startProgram(id, callback) {
        const script = 'dom.GetObject(' + id + ').ProgramExecute();';
        this.exec(script, callback);
    }

    /**
     * Activate/Deactivate a program
     * @method Rega#setProgram
     * @param {number} id
     * @param {boolean} active
     * @param {function} [callback]
     */
    setProgram(id, active, callback) {
        const script = 'dom.GetObject(' + id + ').Active(' + Boolean(active) + ');';
        this.exec(script, callback);
    }

    /**
     * Rename an object
     * @method Rega#setName
     * @param {number} id
     * @param {string} name
     * @param {function} [callback]
     */
    setName(id, name, callback) {
        const script = 'dom.GetObject(' + id + ').Name("' + name + '");';
        this.exec(script, callback);
    }
}

module.exports = Rega;
