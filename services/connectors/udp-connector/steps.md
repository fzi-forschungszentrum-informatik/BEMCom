## Code Outline

import socket

import yaml

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.connect((IP, PORT))

raw_data = s.recv(4096)

data = raw_data.encode("utf-8")

parsed_data = yaml.load(data, Loader=yaml.Loader)



## ARGS

* UDP/TCP
* IP
* PORT
* BUFFERSIZE
* ENCODING
* PARSER