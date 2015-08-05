from .globals import *
from .lib import *
import hashlib
import bitcoin.base58
from bitcoin.core import Hash160
import binascii

class PrivateKey():
    def __init__(self, coins=None, currency=None, version=None):
        self.coins = coins
        self.currency = currency
        self.version = version

        if coins != None and currency != None:
            if self.currency not in self.coins:
                raise Exception("You have no client loaded for this currency.")

            if version == None:
                self.version = self.extract_version()

    def extract_version(self):
        rpc = self.coins[self.currency]["rpc"]["sock"]
        addr = rpc.getaccountaddress("")
        priv = rpc.dumpprivkey(addr)
        priv = bitcoin.base58.decode(priv)
        return priv[0]

    def private_to_wif(self, priv, version=None, compressed=0):
        if version == None:
            version = self.version

        priv = bytes([version]) + priv
        if compressed:
            priv += b'\1'
        checksum = hashlib.sha256(priv).digest()
        checksum = hashlib.sha256(checksum).digest()
        checksum = checksum[0:4]
        priv = priv + checksum
        priv = bitcoin.base58.encode(priv)
        return [priv, version, compressed, checksum]

    def wif_to_private(self, priv, compressed=0):
        priv = bitcoin.base58.decode(priv)
        if len(priv) == 38:
            compressed = 1
        else:
            compressed = 0
        priv = priv[:37] #Remove compression flag.
        version = priv[0]
        checksum = priv[-4:]
        priv = priv[:-4]
        priv = priv[1:]
        return [priv, version, compressed, checksum]


if __name__ == "__main__":
    x = PrivateKey(coins, "bitcoin")
    priv = x.private_to_wif(binascii.unhexlify("0C28FCA386C7A227600B2FE50B7CAE11EC86D3BF1FBE471BE89827E19D72AA1D"))
    priv = binascii.hexlify(x.wif_to_private(priv))
    print(priv)


