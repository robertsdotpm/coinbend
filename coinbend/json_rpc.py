"""
This module patches an error in the Bitcoin JSON RPC
library which caused a timeout error when doing some
operations. It wraps the original code and
auto-reconnects on timeout. 
"""

from .bitcoinrpc.authproxy import AuthServiceProxy
from .currency_type import *
from decimal import Decimal
import socket

class JsonRpc(object):
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.connect()
            
        self.valid_func_names = [
            "addmultisigaddress",
            "addnode",
            "backupwallet",
            "createmultisig",
            "createrawtransaction",
            "decoderawtransaction",
            "decodescript",
            "dumpprivkey",
            "encryptwallet",
            "getaccount",
            "getaccountaddress",
            "getaddednodeinfo",
            "getaddressesbyaccount",
            "getbalance",
            "getbestblockhash",
            "getblock",
            "getblockcount",
            "getblockhash",
            "getblocknumber",
            "getblocktemplate",
            "getconnectioncount",
            "getdifficulty",
            "setgenerate",
            "gethashespersec",
            "getinfo",
            "getmemorypool",
            "getmininginfo",
            "getnewaddress",
            "getpeerinfo",
            "getrawchangeaddress",
            "getrawmempool",
            "getrawtransaction",
            "getreceivedbyaccount",
            "getreceivedbyaddress",
            "gettransaction",
            "gettxout",
            "gettxoutsetinfo",
            "getwork",
            "help",
            "importprivkey",
            "keypoolrefill",
            "listaccounts",
            "listaddressgroupings",
            "listreceivedbyaccount",
            "listreceivedbyaddress",
            "listsinceblock",
            "listtransactions",
            "listunspent",
            "listlockunspent",
            "lockunspent",
            "move",
            "sendfrom",
            "sendmany",
            "sendrawtransaction",
            "sendtoaddress",
            "setaccount",
            "setgenerate",
            "settxfee",
            "signmessage",
            "signrawtransaction",
            "stop",
            "submitblock",
            "validateaddress",
            "decodescript",
            "verifymessage",
            "walletlock",
            "walletpassphrase",
            "walletpassphrasechange"
        ]
        
        self.func_name = None

    def connect(self):
        self.close()
        self.rpc = AuthServiceProxy(self.endpoint)

    def close(self):
        self.rpc = None

    def batch(self, commands):
        try:
            return self.rpc.batch_(commands)
        except socket.timeout:
            self.connect()
            return self.rpc.batch_(commands)
        
    def __getattr__(self, attr):
        if attr.startswith('__') and attr.endswith('__'):
            raise AttributeError

        self.func_name = attr
        return self
        
    def __call__(self, *args):
        self.connect()
        if self.func_name in self.valid_func_names:
            #Parse decimal and C types to float.
            args = list(args)
            index = 0
            for arg in args:
                if type(arg) == C or type(arg) == decimal.Decimal:
                    args[index] = float(str(arg))
                index += 1
            args = tuple(args)

            try:
                temp_rpc = self.rpc.__getattr__(self.func_name)
                return temp_rpc.__call__(*args)
            except socket.timeout:
                """
                This whole wrapper has been to patch this one error.
                This library seems to randomly throw a socket.timeout exception
                where immediately reconnecting and issuing the same call works.
                Whether this is a problem with a part in the library or
                Bitcoind is unkown at this point.
                
                If the same exception is thrown after this point - assume it's
                down for real.
                """
                self.close()
                self.rpc = AuthServiceProxy(self.endpoint)
                temp_rpc = self.rpc.__getattr__(self.func_name)
                return temp_rpc.__call__(*args)
                

if __name__ == "__main__":
    endpoint = "http://litecoinrpc:HMEr5XDxaY23v3tDqTxzEocEQkTmhpRPTAkjd4hAZvnS@127.0.0.1:9332"
    x = JsonRpc(endpoint)
    print(x.getrawtransaction("ff007700"))
    x.close()
    exit()
    print(x.batch([["getnetworkhashps", 1, 4], ["getbalance"], ["getblock", "a6b1f07b2bdbfe4e697bda1249cb7228f7fb367521e388d2bc9b276c7807895a"], ["sendtoaddress", "mj8zK5JyMA6CoWapd6KyMD2A7ADDkmzV7k", "0.0005"]]))
    

    """
    x = AuthServiceProxy(endpoint)
    print(x.getbalance())
    print(x.getnewaddress())
    print(x.sendtoaddress("mzE7mQJpxXbjXjWXVfzRX7feodwrM8vhRa", 0.005))
    print(x.sendtoaddress("mzE7mQJpxXbjXjWXVfzRX7feodwrM8vhRa", Decimal(0.005)))
    """





