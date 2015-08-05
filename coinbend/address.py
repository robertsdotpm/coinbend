"""
This module is used to build custom send addresses between different altcoins which simplifies a lot of funding logic. The main problem it solves is determining address version between altcoins, networks, and p2sh types.
"""

from .globals import *
from .lib import *
from .ecdsa_crypt import *

import hashlib
import bitcoin.base58
from bitcoin import SelectParams
from bitcoin.core import b2x, lx, x, COIN, COutPoint, CTxOut, CTxIn, CTransaction, Hash160, Serializable, str_money_value
from bitcoin.core.script import CScript, OP_DUP, OP_NUMEQUAL, OP_DROP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, SIGHASH_ANYONECANPAY, SIGHASH_SINGLE, OP_IF, OP_CHECKMULTISIGVERIFY, OP_NOTIF, OP_ELSE, OP_ENDIF, OP_VERIFY, OP_SHA256, OP_CHECKSIGVERIFY, OP_CHECKMULTISIG, OP_EQUAL, OP_FALSE, OP_3, OP_0, OP_1, OP_2, OP_5, OP_4, OP_TOALTSTACK, OP_TRUE, OP_DEPTH
from bitcoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from bitcoin.wallet import CBitcoinAddress, CBitcoinSecret
import binascii

def deconstruct_address(addr):
    try:
        #Deconstruct.
        raw_addr = bitcoin.base58.decode(addr)
        version = bytes([raw_addr[0]])
        addr_hash = raw_addr[1:-4]
        checksum = raw_addr[-4:]

        #Check checksum.
        valid_checksum = hashlib.sha256(raw_addr[0:-4]).digest()
        valid_checksum = hashlib.sha256(valid_checksum).digest()
        valid_checksum = checksum[0:4]
        if checksum == valid_checksum:
            is_valid = 1
    except:
        is_valid = 0
        checksum = addr_hash = version = "unknown"

    return {
        "is_valid": is_valid,
        "address": addr,
        "version": version,
        "hash": addr_hash,
        "checksum": checksum
    }

class Address():
    def __init__(self, addr=None, currency=None, coins=None, version=None, is_p2sh=0):
        self.is_p2sh = is_p2sh
        self.addr = addr
        self.coins = coins
        self.currency = currency
        if self.coins != None and self.currency != None:
            if self.currency not in self.coins:
                raise Exception("You have no client loaded for this currency.")

        #Extract version.
        if version == None:
            self.version = self.extract_version(self.addr)
        else:
            self.version = version

    def extract_version(self, addr=None):
        if addr == None:
            if self.coins == None:
                return None

            rpc = self.coins[self.currency]["rpc"]["sock"]
            addr = rpc.getaccountaddress("")

        #Handle p2sh addresses too.
        if self.is_p2sh:
            address_parts = deconstruct_address(addr)
            p2sh = rpc.createmultisig(1, ["0491bba2510912a5bd37da1fb5b1673010e43d2c6d812c514e91bfa9f2eb129e1c183329db55bd868e209aac2fbc02cb33d98fe74bf23f0c235d6126b1d8334f86"])
            addr = bitcoin.base58.decode(p2sh["address"])
        else:
            #Otherwise just use a normal p2pkh address.
            addr = bitcoin.base58.decode(addr)

        version = bytes([addr[0]])
        return version

    def construct_address(self, plaintext, version=None, hashed=0):
        if not self.is_p2sh:
            if len(plaintext) == 32 or len(plaintext) == 64:
                raise Exception("No prefix byte for pub key in construct addr")

        if version == None:
            version = self.version

        if not hashed:
            hash1 = hashlib.sha256(plaintext).digest()
            hash2 = hashlib.new('ripemd160', hash1).digest()
        else:
            hash2 = plaintext
        addr = version + hash2
        checksum = hashlib.sha256(addr).digest()
        checksum = hashlib.sha256(checksum).digest()
        checksum = checksum[0:4]
        addr = addr + checksum
        addr = bitcoin.base58.encode(addr)
        return addr

    def addresses_from_pub_key(self, pub_key_1):
        """
        A public key can be represented as either compressed or
        uncompressed. Each style has a different public key hash which
        produces a completely different address. The purpose of this
        function is to produce both addresses for a given public key
        for the purposes of internal matching for some algorithms.

        Input: bytes.
        Output: [str addr_1, str addr_2]
        """
        
        if len(pub_key_1) == 32 or len(pub_key_1) == 64:
            raise Exception("No prefix byte for pub key in addresses_from_pub_key")
        ecdsa_crypt = ECDSACrypt()
        addr_1 = Address(self.addr, self.currency, self.coins, self.version)
        addr_2 = Address(self.addr, self.currency, self.coins, self.version)
        addresses = [addr_1.construct_address(pub_key_1)]
        if ecdsa_crypt.validate_public_key(pub_key_1):
            pub_key_2 = ecdsa_crypt.decompress_public_key(pub_key_1)
        else:
            pub_key_2 = ecdsa_crypt.compress_public_key(pub_key_1)
        addresses.append(addr_2.construct_address(pub_key_2))

        return addresses


if __name__ == "__main__":
    x = Address(currency="dogecoin", coins=coins, is_p2sh=1)

    #grep -Ril "deconstruct_address" .
    print(x.deconstruct_address("njofjnnCwrPttnpZs6eszmJ8EQ3XE9DGra"))

    exit()
    bin_pub_key = b'\x02y\x16\xcf\xa9\x93\x0cM\xcf\x90<\x17HL=\xd8\xdb\xf9\xa0\xd0\xc1\xd0c^\x80\xba\x94[\xb6\xd1\x86\x17\xa1'
    print(x.construct_address(CScript([1, bin_pub_key, 1, OP_CHECKMULTISIG])))
    x = Address(currency="bitcoin", coins=coins)
    print(x.construct_address(bin_pub_key))




    exit()
    #x = Address(coins, "litecoin")

    addr = "n4irHaRwBi92T5DQcyKQerTwQnkkzMSgWb"
    x = Address(addr, "bitcoin", coins)
    pub_key = binascii.unhexlify("0202d606524ea8335a915364594452017b88ee8257a24306d6f6d5aa976ab56668")
    print(x.addresses_from_pub_key(pub_key))
    exit()

    #print(x.deconstruct_address("n4irHaRwBi92T5DQcyKQerTwQnkkzMSgWb"))
    #print(x.validate_address(addr))
    

    #print(x.version)
    #y = "cU71A7TfDaz6mLuc5ZNWQN52kJmtNkMaNynsVJ6kTx7SpPAdiWgd"
    #x.construct_address(binascii.unhexlify("0450863AD64A87AE8A2FE83C1AF1A8403CB53F53E486D8511DAD8A04887E5B23522CD470243453A299FA9E77237716103ABC11A1DF38855ED6F2EE187E9C582BA6"), b'\0')
    #print(x.brute_force_version())

    #print(x.deconstruct_wif(y))

