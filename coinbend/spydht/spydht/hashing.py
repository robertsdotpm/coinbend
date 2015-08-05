import hashlib
import random

id_bits = 256

def hash_function(data):
    return int(hashlib.sha256(data).hexdigest(), 16)
    
def random_id(seed=None):
    if seed:
        random.seed(seed)
    return random.randint(0, (2 ** id_bits)-1)

def id_from_addr(host, port):
    #2 hex bytes for every byte hence * 2.
    max_bytes = int((id_bits / 8) * 2)
    s = str(host) + "I liek mudkips" + str(port)
    s = hashlib.sha256(s.encode("ascii")).hexdigest()
    s = int(s[0:max_bytes], 16)

    return s
