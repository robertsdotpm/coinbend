spydht
==========

Forked from [kohlrabi23/spydht](https://github.com/kohlrabi23/spydht)

Python 2 and Python 3 implementation of the Kademlia DHT data store.

Useful for distributing a key-value store in a decentralized manner.

This is a more secure rewrite of the original spydht code (itself forked from [isaaczafuta/pydht](https://github.com/isaaczafuta/pydht).)

###Improvements over the original project include:
* Node IDs switched to SHA256 to avoid collisions with MD5.
* Node IDs dereived from the network addr (host + port) to help prevent Sybil attacks (choosing IDs to cluster around a certain key.)
* Routing tables tightened up significantly - two possible entries per IP and restricted to certain ports. This avoids spam.
* Proof of work required for all store messages. Helps avoid spam.
* Size restrictions on DHT messages (currently 5 KB.)
* Proper signature validations!
* Ping commands implemented to keep routing tables fresh.
* Built in data integrity using SHA256 fingerprinting - no more spoofed responses. (Although this means that key indexing is less convenient and you can't update keys but you can delete old keys if you prove ownership.)
* Optional expiry for messages - helps prevent abuse.

I'm not an expert with DHT security so these are just basic things. Sybil attacks are always going to be a problem even with these precautions.

####Example: a two node DHT

Node 1:
```python
from spydht.spydht import DHT

import nacl.signing
import time
import hashlib

key1 = nacl.signing.SigningKey.generate()
host1, port1 = 'localhost', 3100
dht1 = DHT(host1, port1, key1, wan_ip="127.0.0.1")

content = "x"
id = "test"
dht1[id] = content
```

Node 2:
```python
from spydht.spydht import DHT

import nacl.signing
import time
import hashlib

host1, port1 = 'localhost', 3100
key2 = nacl.signing.SigningKey.generate()
host2, port2 = 'localhost', 3101
dht2 = DHT(host2, port2, key2, boot_host=host1, boot_port=port1,  wan_ip="127.0.0.1")

#key = hashlib.sha256(id.encode("ascii") + content.encode("ascii")).hexdigest()
key = "899826c9c46f25fc70ed08b5811dbb2bddf3e6b932e44c6a6a9dc5285057e9db"
print(dht2[key])
```

See remote_example.py for bootstrapping from a remote DHT.

Note: that its likely the combination of a low node DHT with the UDP protocol will produce seemingly random / unreliable results (and out of order responses even on localhost.) If this happens to you a UDP datagram might have been lost. In a large scale network this issue is mitigated by sending multiple queries to multiple hosts so it's less of an issue.

