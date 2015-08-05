from .lib import *
import base64
import nacl.utils
from nacl.public import PrivateKey, Box, PublicKey

class NaclCrypt():
    def __init__(self, public_key=None, private_key=None):
        self.public_key = auto_bytes(public_key)
        self.private_key = auto_bytes(private_key)

        #Generate.
        if self.public_key == None and self.private_key == None:
            self.sk = PrivateKey.generate()
            self.pk = self.sk.public_key
            self.private_key = bytes(self.sk)
            self.public_key = bytes(self.pk)
            return

        #Set public key.
        if self.public_key != None:
            self.sk = None
            self.pk = PublicKey(self.public_key)
            self.public_key = bytes(self.pk)
            self.private_key = None

        #Set private key.
        if self.private_key != None:
            self.sk = PrivateKey(self.private_key)
            self.pk = self.sk.public_key
            self.private_key = bytes(self.sk)
            self.public_key = bytes(self.pk)

    def encrypt(self, msg, public_key):
        try:
            if type(msg) == str:
                msg = msg.encode("ascii")

            public_key = PublicKey(auto_bytes(public_key))
            hai_my_name_is_bawsy = Box(self.sk, public_key)
            nonce = nacl.utils.random(Box.NONCE_SIZE)
            satoshi = bytes(hai_my_name_is_bawsy.encrypt(msg, nonce))
            return base64.b64encode(satoshi).decode("utf-8")
        except:
            return None

    def decrypt(self, msg, public_key):
        try:
            msg = auto_bytes(msg)
            public_key = PublicKey(auto_bytes(public_key))
            hai_my_name_is_bawsy = Box(self.sk, public_key)
            satoshi = hai_my_name_is_bawsy.decrypt(msg)
            return satoshi.decode("utf-8")
        except:
            return None

    def get_public_key(self, f="b64"):
        if f == "bin":
            return self.public_key
        elif f == "hex":
            return binascii.hexlify(self.public_key).decode("utf-8")
        else:
            return base64.b64encode(self.public_key).decode("utf-8")

    def get_private_key(self, f="b64"):
        if f == "bin":
            return self.private_key
        elif f == "hex":
            return binascii.hexlify(self.private_key).decode("utf-8")
        else:
            return base64.b64encode(self.private_key).decode("utf-8")
        

if __name__ == "__main__":
    alice = NaclCrypt()
    print(alice.get_public_key())
    print(alice.get_private_key())
    exit()
    bob = NaclCrypt()

    msg = "Test."
    msg = alice.encrypt(msg, bob.get_public_key())

    print(bob.decrypt(msg, alice.get_public_key()))


   
