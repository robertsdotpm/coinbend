"""
A module of miscellaneous functions mostly related to working with raw transactions.
"""

import os
import platform
import netifaces
import random
import socket
import ipaddress
import ntplib
import time
import urllib.request
import select
import bitcoin
import hashlib
import random
import datetime
import binascii
import decimal
import re

from bitcoin import SelectParams
from bitcoin.core import b2x, b2lx, lx, x, COIN, COutPoint, CTxOut, CTxIn, CTransaction, Hash160, Serializable, str_money_value
from bitcoin.core.script import CScript, OP_DUP, OP_NUMEQUAL, OP_DROP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, SIGHASH_ANYONECANPAY, SIGHASH_SINGLE, OP_IF, OP_CHECKMULTISIGVERIFY, OP_NOTIF, OP_ELSE, OP_ENDIF, OP_VERIFY, OP_SHA256, OP_CHECKSIGVERIFY, OP_EQUAL, OP_FALSE, OP_3, OP_0, OP_1, OP_2, OP_5, OP_4, OP_TOALTSTACK, OP_TRUE, OP_DEPTH
from bitcoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from bitcoin.wallet import CBitcoinAddress, CBitcoinSecret
from bitcoin.core.key import CPubKey
from .ipgetter import *

def mutate_tx(tx_hex):
    """
    Mutates a raw transaction using TX malleability in the scriptSig (specifically, the OP codes.) This function shouldn't be used beyond testing as it uses an ugly eval() hack.

    https://en.bitcoin.it/wiki/Transaction_Malleability
    """
    tx = CTransaction.deserialize(binascii.unhexlify(tx_hex))
    script_sig = repr(tx.vin[0].scriptSig)[9:]
    script_sig = eval("CScript([OP_1, OP_DROP, " + script_sig)
    tx.vin[0].scriptSig = script_sig
    return b2x(tx.serialize())
              
def analyze_key_pair(key_pair):
    """
    Converts a key pair to different formats which is useful
    for working with Bitcoin Script.
    """
    if "priv" not in key_pair:
        key_pair["priv"] = None
    pub = CPubKey(x(key_pair["pub"]))

    addr = None
    if "addr" in key_pair:
        addr = key_pair["addr"]
    """
    The Hash160 function in Python-bitcoin lib actually
    wraps around sha256 hash so every call to Hash160
    also sha256 hashes the input before ripemd160 hashing,
    meaning it the output is valid for address hashes.
    """
    return {
        "addr": {
            "base58": addr
        },
        "pub": {
            "hash": Hash160(pub),
            "hex": key_pair["pub"],
            "bin": pub
        },
        "priv": {
            "wif": key_pair["priv"],
            "hex": None,
            "bin": None
        }
    }

def key_pair_from_address(coin_rpc, address):
    """
    Generates a pub and priv key pair for a given address by
    making RPC calls against a coin's standard client.
    """
    key_pair = {
        "addr": address,
        "pub": "",
        "priv": ""
    }
    key_pair["pub"] = coin_rpc.validateaddress(address)["pubkey"]
    key_pair["priv"] = coin_rpc.dumpprivkey(address)
    key_pair = analyze_key_pair(key_pair)
    return key_pair

def hash160_script(script):
    bin_hash = Hash160(script["bin"])
    return {
        "hex": binascii.hexlify(bin_hash).decode("ascii"),
        "bin": bin_hash
    }

def script_to_address(self, script, person):
    try:
        #Programming is the art of laziness.
        address = str(self.jsonrpc[person].decodescript(script["hex"])["p2sh"])
    except:
        raise Exception("Unable to generate p2sh address.")
    return address

def calculate_tx_fees(coins, currency, tx_hex):
    #Process source TX.
    rpc = coins[currency]["rpc"]["sock"]
    tx = CTransaction.deserialize(binascii.unhexlify(tx_hex))

    #Tally input coins.
    input_total = decimal.Decimal(0)
    for vin in tx.vin:
        txid = b2lx(vin.prevout.hash) 
        vin_tx_hex = rpc.getrawtransaction(txid)
        vin_tx = CTransaction.deserialize(binascii.unhexlify(vin_tx_hex))
        input_value = vin_tx.vout[vin.prevout.n].nValue
        input_total += decimal.Decimal(str_money_value(input_value))

    #Tally output coins.
    output_total = decimal.Decimal(0)
    for vout in tx.vout:
        output_value = decimal.Decimal(str_money_value(vout.nValue))
        output_total += output_value

    #TX fees are the difference between the source and 
    fees = input_total - output_total
    
    #Return totals and fees.
    return [input_total, output_total, fees]

def compare_transactions(tx_hex1, tx_hex2):
    """
    This function compares two transactions. It is required
    because attackers can change serialized transactions without
    invalidating the transaction by modifying a scriptSig or
    by changing a signature which would change the transaction
    ID. This function considers transactions equivalent if
    they share the same inputs and outputs. The scriptSig
    doesn't matter for the purposes of this function. The
    risk of replacing a valid transaction with an invalid
    one with false scriptSigs doesn't occur as subsequent
    code [in this module] only replaces transactions if
    they have at least 1 confirmation. I'm sure Bitcoind
    also wouldn't allow invalid transactions into the
    mempool, disk, etc.
    """
    try:
        if tx_hex1 == tx_hex2:
            #Well, that was easy. Now for the hard part.
            return 1
        
        tx1 = CTransaction.deserialize(binascii.unhexlify(tx_hex1))
        tx2 = CTransaction.deserialize(binascii.unhexlify(tx_hex2))
        
        #Compare number of inputs.
        if len(tx1.vin) != len(tx2.vin):
            return 0
        
        #Compare number of outputs.
        if len(tx1.vout) != len(tx2.vout):
            return 0
            
        #Compare nVersion.
        if tx1.nVersion != tx2.nVersion:
            return 0
            
        #Compare nLockTime.
        if tx1.nLockTime != tx2.nLockTime:
            return 0
            
        #Compare inputs.
        for i in range(0, len(tx1.vin)):
            #Compare sequences.
            #To keep it simple: tx replacement isn't supported.
            if tx1.vin[i].nSequence != tx2.vin[i].nSequence:
                return 0
            
            #Compare outpoints.
            if tx1.vin[i].prevout.hash != tx2.vin[i].prevout.hash:
                return 0
            if tx1.vin[i].nSequence != tx2.vin[i].nSequence:
                return 0

        #Compare outputs.
        for i in range(0, len(tx2.vout)):
            if tx1.vout[i] != tx2.vout[i]:
                return 0

        #Sighash and sigs aren't checked as this code is run on TXs returned from *coind.
        
        return 1
    except:
        return 0

def reverse_hex(hex_str):
    hex_str_len = len(hex_str)
    backwards_man = ""        
    
    #Check if bytes are in correct hex format.
    if hex_str_len % 2:
        raise Exception("Unable to reverse hex_str")
        
    #Reverse hex bytes.
    for i in list(reversed(range(1, int(hex_str_len / 2) + 1))):
        byte_me = hex_str[(i * 2) - 2:i * 2]
        backwards_man += byte_me
    
    #Returns a hex string with correct txid.    
    return backwards_man

def calculate_txid(tx_hex):
    #Txid is double sha256 hash of serialized transaction.
    single = binascii.unhexlify(hashlib.sha256(binascii.unhexlify(tx_hex)).hexdigest())
    double = hashlib.sha256(single).hexdigest()
    return reverse_hex(double) #Litte endian.

