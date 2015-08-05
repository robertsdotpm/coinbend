from spydht.spydht import DHT

import nacl.signing
import time
import hashlib

host1, port1 = 'localhost', 31000
key2 = nacl.signing.SigningKey.generate()

host2, port2 = 'localhost', 3101
dht2 = DHT(host2, port2, key2, boot_host=host1, boot_port=port1,  wan_ip="127.0.0.1")


time.sleep(5)

content = "x"
id = "test"

dht2[id] = content

time.sleep(2)

print(dht2.buckets.buckets)

key = hashlib.sha256(id.encode("ascii") + content.encode("ascii")).hexdigest()

print("hererere")

print(dht2.data)

try:
    print(dht2[key])
except:
    pass

print("After .")



print("what key should be")
print(int(key, 16))


content = "new"
id = "new content"
dht2[{"old_key": int(key, 16), "id": "new content"}] = content



key = hashlib.sha256(id.encode("ascii") + content.encode("ascii")).hexdigest()

print("new key: ")
print(int(key, 16))

print(dht2[key])


while True:
    time.sleep(1)





