"""
This function is used to push raw transactions directly to the P2P
network of a cryptocurrency. It is needed because there is a bug in
sendrawtransaction https://github.com/bitcoin/bitcoin/issues/1414
that doesn't propogate certain transactions immediately (if at all)
causing delays on alt-coins that haven't merged the patch.

The downside of this library is that the network id / magic byte needs
to be manually configured in the config file but this is still only
for alt-coins that have this bug.
"""

import struct
import hashlib
import binascii
import time
import socket
import random
from .globals import *
from .sock import *
from .lib import *
from .coinlib import *

class TXPush():
    def __init__(self, config, coins):
        self.config = config
        self.coins = coins

        #Initialize node list.
        self.nodes = {}
        self.load_nodes()

    def load_nodes(self, include_remote=0, timeout=2):
        #Clear old details.
        self.nodes = {}
        for currency in coins:
            self.nodes[currency] = []
            rpc = coins[currency]["rpc"]["sock"]
            if rpc == None:
                continue

            #Get node list and record most common port.
            nodes = rpc.getpeerinfo()
            frequencies = {}
            most_common_port = None
            for node in nodes:
                #Connect.
                try:
                    addr, port = node["addr"].split(":")
                    port = int(port)
                    if include_remote:
                        s = Sock(addr, port, blocking=1, timeout=timeout)
                        node_info = {"addr": addr, "port": port, "con": s}
                        self.nodes[currency].append(node_info)
                except socket.error:
                    continue
                if port not in frequencies:
                    frequencies[port] = 0

                frequencies[port] += 1
                if most_common_port == None:
                    most_common_port = port
                else:
                    if frequencies[port] > frequencies[most_common_port]:
                        most_common_port = port

            #Insert a reference to localhost.
            try:
                addr = "127.0.0.1"
                s = Sock(addr, most_common_port, blocking=1, timeout=timeout)
                node_info = {"addr": addr, "port": most_common_port, "con": s}
                self.nodes[currency].append(s)
            except socket.error:
                return

    def make_msg(self, magic, command, payload):
        #Little endian.
        msg = binascii.unhexlify(reverse_hex(magic))
        msg += command
        msg += b"\x00" * (12 - len(command))
        msg += struct.pack("<I", len(payload))
        checksum = hashlib.sha256(payload).digest()
        checksum = hashlib.sha256(checksum).digest()
        msg += checksum[:4]
        msg += payload
        return msg

    def netaddr(self, ipaddr, port):
        if type(ipaddr) == str:
            ipaddr = ipaddr.encode("ascii")
        services = 1
        return (struct.pack('<Q12s', services, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff') +
        struct.pack('>4sH', ipaddr, port))

    def make_version_msg(self, magic, our_node, their_node):
        version = 70002 #7?
        services = 1
        timestamp = int(time.time())
        addr_me = self.netaddr(socket.inet_aton(our_node[0]), our_node[1])
        addr_you = self.netaddr(socket.inet_aton(their_node[0]), their_node[1])
        nonce = random.getrandbits(64)
        sub_version_num = struct.pack('<B', 0) + b''
        start_height = 0
        relay = 1

        payload = struct.pack('<LQQ26s26sQsL?', version, services, timestamp, addr_me,
        addr_you, nonce, b"\0", start_height, relay)
        return self.make_msg(magic, b"version", payload)

    def tx(self, currency, tx_hex, skip=0):
        assert(currency in self.config["network_id"])

        #Build tx propogate message.
        payload = binascii.unhexlify(tx_hex)
        network = "testnet" if self.config["testnet"] == 1 else "mainnet"
        magic = self.config["network_id"][currency][network]
        command = b"tx"
        msg = self.make_msg(magic, command, payload)

        #Push message to all fast nodes that work~
        success_no = 0
        for node in self.nodes[currency]:
            try:
                #Send our version message.
                our_node = (get_wan_ip(), self.nodes[currency][-1]["port"])
                their_node = (node["addr"], node["port"])
                version_msg = self.make_version_msg(magic, our_node, their_node)
                node["con"].send(version_msg)

                #Receive version.
                node["con"].recv(1000)
                
                #Receive verack.
                node["con"].recv(1000)

                #Send payload containing raw tx.
                node["con"].send(msg)
                success_no += 1

                #No need to spam.
                if success_no >= 5:
                    break
            except:
                continue

        #Try load more clients to connect with.
        if not success_no and not skip:
            self.load_nodes()
            self.tx(currency, tx_hex, skip=1)

if __name__ == '__main__':
    tx_push = TXPush(config, coins)
    tx_push.tx("litecoin", "0100000001a9fd1d375c92157eb1a1cf56d8dafe455dc09bbce9533f8480d0148efc9e2e0501000000fd690100483045022100e8e2bed00876f6dbcb20361ac8e1280c61601fac5cb1f6d939636b9e257b40da022016b54d46d3f232a92336b2eee65c3f80d7094ce3c491c403e9cd1443268426ca01483045022100c9d0ad496e4372b347bf638380f553d1dd8e21f8017af6f3ab080ab6673669ad02207b27af25c37f72f81a42e9deb872c293d2269be6702c8002d61fb95e24a3b62e01483045022100d4d81fb08781b8b3d5ad9e5ca7748c87cc44f1d9696cd0e994b163235e7c77490220481bb3f9865bf95c1a8c17f611fedfaa2728a9048a4b3a7283a431b10f9b9d8b014c8b5321038bf6fdc8eb08ee9f421bf2a6d2e281e8bb7e53aa3923ef5ed028385344204a53210214531a82d06f7a1aa115a767457ba9d90c55266a454d264e7a7a353dc6b5cd0a2103f70591eedaf8164fea363b6847c789b752f6f3e566fe3235e48abd5596bacea22103bcc5447aff3f9c0f709b663b4241a24a55b29128521e3beb6434b5257105a19154aeffffffff01297a0700000000001976a91496b5be75c2403554b0825d565f4efb630cf5b19688ac00000000")

