from .lib import *
import base64

class NaclCrypt():
    def __init__(self, public_key=None, private_key=None):
        self.public_key = auto_bytes(public_key)
        self.private_key = auto_bytes(private_key)

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



   
