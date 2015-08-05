from spydht.spydht import DHT

import nacl.signing
import time
import hashlib

key1 = nacl.signing.SigningKey.generate()

host1, port1 = 'localhost', 3100
dht1 = DHT(host1, port1, key1, wan_ip="127.0.0.1")


time.sleep(10)
print(dht1["899826c9c46f25fc70ed08b5811dbb2bddf3e6b932e44c6a6a9dc5285057e9db"])


while True:
    time.sleep(1)
    
