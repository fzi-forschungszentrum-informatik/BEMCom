/*
Copyright 2017 Tiago Machado

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/

module.exports = function (RED) {
    "use strict";

    var iconv = require('iconv-lite');

    function Converter(config) {
        RED.nodes.createNode(this, config);
        this.from = config.from;
        var node = this;

        this.on('input', function (msg) {

            if (iconv.encodingExists(node.from)) {
                if (msg.hasOwnProperty("payload")) {
                    if (Buffer.isBuffer(msg.payload)) {
                        msg.payload = iconv.decode(msg.payload, node.from);
                        node.send(msg);
                    } else if (typeof msg.payload === "string") {
                        msg.payload = iconv.encode(msg.payload, node.from)
                        node.send(msg);
                    } else {
                        node.error(RED._("converter.error.type"), msg);
                    }
                } else {
                    node.error(RED._("converter.error.payload"), msg);
                }
            } else {
                node.error(RED._("converter.error.encoding") + node.from, msg);
            }
        });
    }
    RED.nodes.registerType("converter", Converter);
}