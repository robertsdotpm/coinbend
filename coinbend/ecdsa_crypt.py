"""
Provides an ECDSA wrapper for generating, outputting, parsing, formatting and signing with Bitcoin style ECDSA keys. Compression and decompression of keys is also built in with all keys being internally converted to a decompressed format and outputted as compressed (unless overwritten) which makes working with ECDSA keys extremely easy.
"""

from .globals import *
from .database import *
from .lib import *
from .private_key import *
from .address import *
from bitcoin.core import x, Hash160
from bitcoin.core.key import CPubKey
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError
import base64
import binascii
import re

class ECDSACrypt:
    def __init__(self, public_key=None, private_key=None):
        self.id = 0
        self.public_key = auto_bytes(public_key)
        self.private_key = private_key
        self.addr_version = None
        self.use_compression = 1
        if private_key == "":
            private_key = None

        #Generate key pairs.
        if self.public_key == None and private_key == None:
            self.sign_key = SigningKey.generate(curve=SECP256k1)
            self.verify_key = self.sign_key.get_verifying_key()
            self.private_key = self.sign_key.to_string()
            self.public_key = self.verify_key.to_string()
            return

        #Init public key.
        self.old_verify_str = None
        if self.public_key != None:
            self.public_key = self.parse_public_key(self.public_key)
            self.verify_key = VerifyingKey.from_string(self.public_key, SECP256k1)
            self.sign_key = None
            self.old_verify_str = self.verify_key.to_string()

        #Init private key.
        if self.private_key != None:
            #Construct keys from private key.
            self.private_key = self.parse_private_key(private_key)
            self.sign_key = SigningKey.from_string(self.private_key, SECP256k1) 
            self.verify_key = self.sign_key.get_verifying_key()

            #Check private key corrosponds to public key.
            if self.old_verify_str != None:
                if self.old_verify_str != self.verify_key.to_string():
                    raise Exception("Private key doesn't corrospond to stored public key.")

    def save(self):
        with Transaction() as tx:
            sql = "INSERT INTO `ecdsa_pairs` (`public_key`, `private_key`) VALUES (?, ?)"

            private_key = ""
            if self.private_key != None:
                private_key = self.private_key
            tx.execute(sql, (self.get_public_key(), self.get_private_key()))
            self.id = tx.db.cur.lastrowid

    #Input = b58check || b64 || hex private key
    #Output = binary ECDSA private key.
    def parse_private_key(self, private_key):
        if type(private_key) == str:
            #Base58 string.
            if re.match("^[!][" + b58 + "]+$", private_key) != None:
                try:
                    priv, version, compressed, checksum = PrivateKey().wif_to_private(private_key[1:])
                    self.addr_version = version
                    return priv
                except:
                    pass

        return auto_bytes(private_key)

    #Input = b64encoded public key.
    #Output = ECDSA-style (non-prefixed) decompressed public key.
    def parse_public_key(self, public_key):
        public_key = auto_bytes(public_key)

        #Key is valid compressed key.
        if len(public_key) == 64:
            return public_key

        #Key is valid but contains prefix.
        if len(public_key) == 65:
            return public_key[1:]

        #Invalid compressed key.
        if len(public_key) == 32:
            raise Exception("Prefix byte for compressed pub key not known.")
            #public_key = bytes([3]) + public_key

        #Decompress the key.
        if len(public_key) == 33:
            return self.decompress_public_key(public_key)[1:]

        return public_key            

    #Input: str, str
    #Output: str b64 encoded sig
    def sign(self, msg, private_key=None):
        if private_key == None:
            sign_key = self.sign_key
        else:
            private_key = self.parse_private_key(private_key)
            sign_key = SigningKey.from_string(private_key, SECP256k1)

        if sign_key == None:
            raise Exception("Private key for ECDSA keypair not known.")

        if type(msg) == str:
            msg = msg.encode("ascii")

        return base64.b64encode(sign_key.sign(msg)).decode("utf-8")

    #Input: b64 encoded pub key, b64 encoded sig, str msg
    #Output: boolean
    def valid_signature(self, signature, msg, public_key=None):
        try:
            if type(msg) == str:
                msg = msg.encode("ascii")

            #Parse public key.
            if public_key == None:
                public_key = self.public_key
            else:
                public_key = self.parse_public_key(public_key)

            signature = auto_bytes(signature)
            msg = auto_bytes(msg)
            verify_key = VerifyingKey.from_string(public_key, SECP256k1)
            return verify_key.verify(signature, msg)
        except Exception as e:
            print(e)
            return 0

    #Input: compressed prefixed pub key bytes
    #Output: decompressed prefixed pub key bytes
    def decompress_public_key(self, public_key):
        #https://bitcointalk.org/index.php?topic=644919.0
        public_key = auto_bytes(public_key)
        public_key = binascii.hexlify(public_key)
        public_key = public_key.decode("utf-8")

        p = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
        y_parity = int(public_key[:2]) - 2
        x = int(public_key[2:], 16)

        a = (pow_mod(x, 3, p) + 7) % p
        y = pow_mod(a, (p+1)//4, p)
        if y % 2 != y_parity:
            y = -y % p
        x = "{0:0{1}x}".format(x, 64)
        y = "{0:0{1}x}".format(y, 64)

        ret = "04" + x + y

        return binascii.unhexlify(ret)

    #Input: decompressed prefixed pub key bytes
    #Output: decompressed prefixed pub key bytes
    def compress_public_key(self, public_key):
        #https://bitcointalk.org/index.php?topic=644919.0
        public_key = auto_bytes(public_key)
        public_key = binascii.hexlify(public_key).decode("utf-8")

        #Is there a prefix byte?
        if len(public_key) == 128:
            offset = 0
        else:
            offset = 2

        #Extract X from X, Y public key.
        x = int(public_key[offset:64 + offset], 16)
        y = int(public_key[65 + offset:], 16)

        if y % 2:
            prefix = "03"
        else:
            prefix = "02"

        #Return compressed public key.
        ret = prefix + "{0:0{1}x}".format(x, 64)
        return binascii.unhexlify(ret)

    #Input: prefixed pub key bytes
    #Output: boolean
    def validate_public_key(self, public_key):
        public_key = auto_bytes(public_key)
        public_key = binascii.hexlify(public_key).decode("utf-8")
        prefix = public_key[0:2]
        if prefix == "04":
            is_compressed = 0
        else:
            is_compressed = 1

        return is_compressed

    #Returns a Bitcoin style public_key (prefixed)
    def get_public_key(self, f="b64", public_key=None):
        if public_key == None:
            public_key = self.public_key

        #O4 = uncompressed.
        public_key_hex = "04" + binascii.hexlify(public_key).decode("utf-8")
        if self.use_compression:
            public_key = binascii.unhexlify(public_key_hex)
            public_key = self.compress_public_key(public_key)
            public_key_hex = binascii.hexlify(public_key).decode("utf-8")
        else:
            public_key = binascii.unhexlify(public_key_hex)

        cpub = CPubKey(x(public_key_hex))

        if f == "bin":
            return public_key

        elif f == "hex":
            return public_key_hex

        elif f == "cpub":
            return cpub

        elif f == "hash":
            return Hash160(cpub)

        else:
            return base64.b64encode(public_key).decode("utf-8")

    def load_db_private_key(self):
        with Transaction() as tx:
            sql = "SELECT * FROM `ecdsa_pairs` WHERE `public_key`=?;"
            tx.execute(sql, (self.get_public_key(),))
            rows = tx.fetchall()
            if not len(rows):
                return

            row = rows[0]
            self.private_key = self.parse_private_key(row["private_key"])
            self.sign_key = SigningKey.from_string(self.private_key, SECP256k1) 
            self.verify_key = self.sign_key.get_verifying_key()

    def get_private_key(self, f="b64"):
        if f == "bin":
            return self.private_key

        elif f == "hex":
            return binascii.hexlify(self.private_key).decode("utf-8")

        elif f == "wif":
            if self.addr_version == None:
                raise Exception("Addr version for priv key not known.")
            priv, version, compressed, checksum = PrivateKey().private_to_wif(self.private_key, self.addr_version, self.use_compression)
            return priv

        else:
            return base64.b64encode(self.private_key).decode("utf-8")

if __name__ == "__main__":
    ecdsa = ECDSACrypt()
    while 1:
        ecdsa_2 = ECDSACrypt(ecdsa.get_public_key(), ecdsa.get_private_key())
        ecdsa = ECDSACrypt()


    exit()

    pub_key = b'0\x8f\xbe\xc3\x00\x18\xde\xd7\xaf\xdb\xdc\xa5t\x02\xdci\xbc\xcf\xf1\x8c\x90\x15MH\xa9\x03\x0bf\xce\xd6\x16\x1e\xff\x99?\x18+-G\xb2\x17EL\x94\xaa\x00\xb55\x13\xe0\xa1Y\xa8\xf4\x81\xa2\x8e\xaf\xc4\xa8\xebU\xd6\xd1'

    ecdsa = ECDSACrypt(base64.b64encode(pub_key).decode("utf-8"))
    compressed = ecdsa.compress_public_key(pub_key)

    """
    pub_key = "#15d895fd7a4b91787572925d5f5a1e4aeb4f7c9795e2c9f62b1b7f66088c982c9311306682a89255a1926643f56ea0b87485fda89ed6c05de2c840280d8c0286"
    pub_key = b'\x15\xd8\x95\xfdzK\x91xur\x92]_Z\x1eJ\xebO|\x97\x95\xe2\xc9\xf6+\x1b\x7ff\x08\x8c\x98,\x93\x110f\x82\xa8\x92U\xa1\x92fC\xf5n\xa0\xb8t\x85\xfd\xa8\x9e\xd6\xc0]\xe2\xc8@(\r\x8c\x02\x86'
    ecdsa = ECDSACrypt(pub_key)
    compressed = ecdsa.compress_public_key(pub_key)
    #print(binascii.hexlify(compressed))



    source = "#0215d895fd7a4b91787572925d5f5a1e4aeb4f7c9795e2c9f62b1b7f66088c982c"
    source = binascii.hexlify(compressed)
    print("#" + source.decode("ascii"))

    print(binascii.hexlify(ecdsa.decompress_public_key("#" + source.decode("ascii"))))

    #print(binascii.hexlify(ecdsa.compress_public_key("#0415d895fd7a4b91787572925d5f5a1e4aeb4f7c9795e2c9f62b1b7f66088c982c9311306682a89255a1926643f56ea0b87485fda89ed6c05de2c840280d8c0286")).decode("utf-8") == source[1:])

    exit()
    """


    decompressed = ecdsa.decompress_public_key(compressed)
    decompressed = ecdsa.parse_public_key(decompressed)

    print(compressed)
    print(decompressed)
    print(ecdsa.public_key)
    


    exit()
    while 1:
        ecdsa_2 = ECDSACrypt(ecdsa.get_public_key(), ecdsa.get_private_key())
        ecdsa = ECDSACrypt()


    exit()

              
    bob_ecdsa_1 = ECDSACrypt("ApeDaYqkbr0IZYwoWb/sjTlPDFh89rAZaQqqC/X8CzA4", "UFo1Q4EfLR+KFuaS15cLhKDLmseXSnzVKj4Y2zGWfXg=")

    exit()


    priv = bob_ecdsa_1.get_private_key("bin")
    #print(bob_ecdsa_1.use_compression)

    #print(len(priv))
    #print(bob_ecdsa_1.get_public_key())

    msg = "test"
    sig = bob_ecdsa_1.sign(msg)
    #print(sig)
    print(bob_ecdsa_1.valid_signature(sig, msg))
    exit()


    exit()

    y = ECDSACrypt("AlJvArnP1j+OtDUEL2Wdh2eDOSwgfibAwOk+XZZ168w4")
    y = PrivateKey()
    priv, version, compressed, checksum = y.wif_to_private("cNs36nxy8u2q8dforgiUCo1nwdPL7P7TAxLXNpFmML69Wnh4UDqh")
    priv, version, compressed, checksum = y.private_to_wif(priv, version, 1)

    alice_ecdsa_1_public_key = "9wWR7tr4Fk/qNjtoR8eJt1L28+Vm/jI15Iq9VZa6zqJ44nZAsZTSr6dx+iMPzVjqX74ZA7ut7hNisEjUDfd6qw=="

    alice_ecdsa_1_private_key = "7Bpn5UeboyvUOeahJ2htOsEYjgHo6/3ezwTrSjh4Lvs="

    e = ECDSACrypt(alice_ecdsa_1_public_key, alice_ecdsa_1_private_key)
    print(e.get_public_key("cpub"))
    print(e.get_public_key("hash"))

    msg = "Test"
    sig = e.sign(msg)
    print(sig)
    print(e.valid_signature(sig, msg))


    #af2020dfd1f0c17b65ea3141443ce4585d7b55488c88e082212ef05baba03400
    #02af2020dfd1f0c17b65ea3141443ce4585d7b55488c88e082212ef05baba03400
    #023473af2020dfd1f0c17b65ea3141443ce4585d7b55488c88e082212ef05baba0
    #023473af2020dfd1f0c17b65ea3141443ce4585d7b55488c88e082212ef05baba0
    #303473af2020dfd1f0c17b65ea3141443ce4585d7b55488c88e082212ef05baba


    #303473af2020dfd1f0c17b65ea3141443ce4585d7b55488c88e082212ef05baba
    #034008e801c65536d5b756b01b4163b19166bdc66fbf5b15bc8c7bd8e56f3ffaba0 
    #034008e801c65536d5b756b01b4163b19166bdc66fbf5b15bc8c7bd8e56f3ffaba0

    e = ECDSACrypt("#0273af2020dfd1f0c17b65ea3141443ce4585d7b55488c88e082212ef05baba034", "!cNs36nxy8u2q8dforgiUCo1nwdPL7P7TAxLXNpFmML69Wnh4UDqh")
    print(e.use_compression)

    msg = "Test"
    sig = e.sign(msg)
    print(sig)
    print(e.valid_signature(sig, msg))
    print(e.get_private_key("wif"))
    print(e.get_public_key("hex"))
    exit()

    #print(base64.b64encode(ecdsa_crypt.public_key))
    #print()
    #print(base64.b64encode(ecdsa_crypt.private_key))


    """
    p = "0202d606524ea8335a915364594452017b88ee8257a24306d6f6d5aa976ab56668"
    p = binascii.unhexlify(p)
    un = binascii.hexlify(ecdsa_crypt.decompress_public_key(p))
    print(un)
    p = binascii.unhexlify(un)
    print(un)
    print(binascii.hexlify(ecdsa_crypt.compress_public_key(p)))
    exit()
    print(len(p))
    """
    exit()


    
    msg = "test"
    sig = ecdsa_crypt.sign(msg)
    public_key = ecdsa_crypt.get_public_key()
    #print(sig)
    #exit()
    print(public_key)
    print(ecdsa_crypt.valid_signature(public_key, sig, msg))
    #print(ecdsa_crypt.get_public_key())
    #print(ecdsa_crypt.get_private_key())


