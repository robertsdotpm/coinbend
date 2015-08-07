"""
The contract server is used to unlock coins from a green addresses and allocate them between contracts. It is the mechanism that allows for partial matching by indicating in real time when the other side of a contract has submitted a setup transaction allocating money towards a contract. Outputs from the setup transaction can thus be timed out and updated as needed which also prevents time wasting from other nodes as contracts are only funded if both sides do.

(You can think of this server as working similar to a switch board operator for routing coins between green addresses and contracts.)

Todo: there's an error in this where one of the instances doesn't exist when it comes time to build the ready message. What situations could produce this?
"""


from .globals import *
from .trades import *
from .trade_type import *
from .nacl_crypt import *
from .order_book import *
from .trade_engine import *
from .green_address import *
from .hybrid_protocol import *
from .microtransfer_contract import *
from .ecdsa_crypt import *
from .lib import *
from twisted.internet import ssl, reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.protocols.basic import LineReceiver
import os
import re
import base64
import binascii
from decimal import Decimal
import hashlib

from bitcoin import SelectParams
from bitcoin.core import b2x, b2lx, lx, x, COIN, COutPoint, CTxOut, CTxIn, CTransaction, Hash160, Serializable, str_money_value , b2lx
from bitcoin.core.script import CScript, OP_DUP, OP_NUMEQUAL, OP_DROP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, SIGHASH_ANYONECANPAY, SIGHASH_SINGLE, OP_IF, OP_CHECKMULTISIGVERIFY, OP_NOTIF, OP_ELSE, OP_ENDIF, OP_VERIFY, OP_SHA256, OP_CHECKSIGVERIFY, OP_CHECKMULTISIG, OP_EQUAL, OP_FALSE, OP_3, OP_0, OP_1, OP_2, OP_5, OP_4, OP_TOALTSTACK, OP_TRUE, OP_DEPTH
from bitcoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from bitcoin.wallet import CBitcoinAddress, CBitcoinSecret, CKey
from decimal import Decimal

class ContractProtocol(LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.connected = False

    def send_line(self, msg):
        #Not connected.
        if not self.connected:
            print("Send line not connected.")
            return

        #Network byte order.
        try:
            if type(msg) != bytes:
                msg = msg.encode("ascii")
        except Exception as e:
            print("send line ex: ")
            print(e)
            return

        self.sendLine(msg)

    def lineReceived(self, line):
        #Unicode samich.
        print(line)
        try:
            if type(line) == bytes:
                line = line.decode("utf-8")
        except Exception as e:
            print(e)
            return

        #Indicate IP.
        line += " " + self.transport.getPeer().host + " " + str(self.transport.getPeer().port)

        #Parse replies.
        try:
            for reply in parse_msg(line, self.factory.version, None, self.factory.msg_handlers, self.factory.hybrid_protocol.sys_clock, self.factory.hybrid_protocol.config):
                self.send_line(reply)
        except Exception as e:
            error = parse_exception(e)
            log_exception(error_log_path, error)
            print(error)

    def connectionMade(self):
        self.connected = True
        ip_addr = self.transport.getPeer().host
        port = self.transport.getPeer().port
        ident = ip_addr + ":" + str(port)
        print("Con made: " + str(ident))
        self.factory.clients[ident] = self

    def connectionLost(self, reason):
        self.connected = False
        ip_addr = self.transport.getPeer().host
        port = self.transport.getPeer().port
        ident = ip_addr + ":" + str(port)
        print("Con lost:" + str(ident))
        if ident in self.factory.clients:
            del self.factory.clients[ident]


class ContractFactory(Factory):
    def __init__(self, config):
        nacl_crypt = NaclCrypt()
        trades = Trades()
        order_book = OrderBook()
        trade_engine = TradeEngine(trades, order_book)
        self.hybrid_protocol = HybridProtocol(config, sys_clock, nacl_crypt, None, coins, e_exchange_rate, trade_engine, contract_client=None)
        self.msg_handlers = {
            "REGISTER": self.parse_register_msg,
            "MATCH": self.parse_match_msg,
            "UPDATE": self.parse_update_msg
        }
        self.version = 1
        self.instances = {} #Setup transactions.
        self.green_addresses = {} #Funding sources / inputs.
        self.contracts = {} #Details for match agreements.
        self.clients = {} #Connected clients.
        self.config = config
        self.ecdsa_encrypted = ECDSACrypt(self.config["green_address_server"]["encrypted_key_pair"]["pub"], self.config["green_address_server"]["encrypted_key_pair"]["priv"])
        self.ecdsa_offline = ECDSACrypt(self.config["green_address_server"]["offline_key_pair"]["pub"])
        self.ecdsa_fee = ECDSACrypt(self.config["fee_key_pair"]["pub"])

    def parse_register_msg(self, msg, version, ntp, con=None):
        #Unpack.
        version, ntp, rpc, tx_hex, pub_1, pub_2, sig_1, sig_2, instance_id, ip_addr, port = msg.split(" ")
        version = int(version)
        ntp = int(ntp)
        ecdsa_1 = ECDSACrypt(pub_1)
        ecdsa_2 = ECDSACrypt(pub_2)
        sig_1 = base64.b64decode(sig_1.encode("ascii"))
        sig_2 = base64.b64decode(sig_2.encode("ascii"))

        #Check instance id.
        if instance_id in self.instances:
            print("Instance already exists in setup.")
            return []

        #Check setup transaction.
        redeem_script = green_redeem_script(ecdsa_1, ecdsa_2, self.ecdsa_encrypted, self.ecdsa_offline)
        sig_3 = sign_setup_tx(tx_hex, redeem_script, self.ecdsa_encrypted)
        ret = validate_setup_tx(self.config, tx_hex, ecdsa_1, ecdsa_2, sig_1, sig_2, sig_3)
        print("Herrrr 666--------")
        print(ret)
        if type(ret) != dict:
            print("Check setup failed.")
            return []

        if ret["deposit"]["txid"] in self.green_addresses:
            print("Setup TX / green address already exists.")
            return []

        #Create new instance:
        instance = {
            "id": None,
            "chunks": {}, #Index = vout no.
            "collateral_info": {},
            "locked": [],
            "is_locked": False,
            "con": {
                "ip_addr": None,
                "port": None
            }
        }
        instance = dict(list(ret.items()) + list(instance.items()))

        #Record details.
        instance["contract"]["links"] = {}
        instance["con"]["ip_addr"] = ip_addr
        instance["con"]["port"] = port
        instance["id"] = instance_id
        self.instances[instance_id] = instance
        self.green_addresses[instance["deposit"]["txid"]] = self.instances[instance_id]
        
        return []

    def parse_handshake_msg(self, msg):
        version, ntp, rpc, contract_hash, sig = msg.split(" ")
        ret = {
            "version": version,
            "ntp": ntp,
            "rpc": rpc,
            "contract_hash": contract_hash,
            "sig": sig
        }

        return ret

    def parse_match_msg(self, msg, version, ntp, con=None):
        #Unpack values.
        version, ntp, rpc, contract_msg, our_handshake_msg, their_handshake_msg, collateral_info, instance_id, ip_addr, port = msg.split(" ")
        collateral_info = base64.b64decode(collateral_info.encode("ascii")).decode("utf-8")
        contract_msg = base64.b64decode(contract_msg.encode("ascii")).decode("utf-8")
        contract_hash = hashlib.sha256(contract_msg.encode("ascii")).hexdigest()
        our_handshake_msg = base64.b64decode(our_handshake_msg.encode("ascii")).decode("utf-8")
        our_handshake = self.parse_handshake_msg(our_handshake_msg)
        their_handshake_msg = base64.b64decode(their_handshake_msg.encode("ascii")).decode("utf-8")
        their_handshake = self.parse_handshake_msg(their_handshake_msg)
        contract = self.hybrid_protocol.parse_contract(contract_msg)

        #Does the instance exist?
        if instance_id not in self.instances:
            print(self.instances)
            print(instance_id)
            print("Instance doesn't exist mate.")
            return []
        else:
            #Record IP address.
            self.instances[instance_id]["con"]["ip_addr"] = ip_addr
            self.instances[instance_id]["con"]["port"] = port

        #Are the handshake hashes valid?
        if our_handshake["contract_hash"] != their_handshake["contract_hash"]:
            print("errro 234324234")
            return [] #What are you doing?
        if our_handshake["contract_hash"] != contract_hash:
            print("erorr 34545435")
            return [] #Nice try.

        #Check "our handshake" is valid.
        actor = None
        ecdsa_pairs = [
            contract["buyer"]["ecdsa"][0],
            contract["seller"]["ecdsa"][0]
        ]
        our_handshake_msg = our_handshake_msg.split(" ")
        our_handshake_sig = our_handshake_msg.pop()
        for ecdsa_pair in ecdsa_pairs:
            if ecdsa_pair.valid_signature(our_handshake_sig, " ".join(our_handshake_msg)):
                if ecdsa_pair.get_public_key() == contract["buyer"]["ecdsa"][0].get_public_key():
                    actor = "buyer"
                else:
                    actor = "seller"
                ecdsa_pairs.remove(ecdsa_pair)
                break
        if len(ecdsa_pairs) == 2:
            print("Invalid handshake 1.")
            return []

        #Check "their handshake" is valid.
        their_handshake_msg = their_handshake_msg.split(" ")
        their_handshake_sig = their_handshake_msg.pop()
        if not ecdsa_pairs[0].valid_signature(their_handshake_sig, " ".join(their_handshake_msg)):
            print("Invalid handshake 2.")
            return []

        #Check signed collateral info msg.
        chunk_size, arbiter_pub, sig_1, pub_1, sig_2, pub_2 = collateral_info.split(" ")
        if C(chunk_size) != contract["seller"]["chunk_size"] and C(chunk_size) != contract["buyer"]["chunk_size"]:
            print("errror 55556")
            return []
        if pub_1 != contract[actor]["ecdsa"][0].get_public_key():
            print("errorr 55557")
            return []
        collateral_unsigned = "%s %s" % (chunk_size, arbiter_pub)
        if not contract[actor]["ecdsa"][0].valid_signature(sig_1, collateral_unsigned):
            print("errorr 55558")
            return []
        if not contract[actor]["ecdsa"][1].valid_signature(sig_2, collateral_unsigned):
            print("errror 55559")
            return []

        #Record proof they agree on the transfer size.
        self.instances[instance_id]["collateral_info"][contract_hash] = collateral_info

        #Check whether contract has any existing satisfied setup TXs.
        #As in, someone who has setup the right outputs in an existing setup tx.
        sides = {
            "buyer": "seller",
            "seller": "buyer"
        }
        found = {}
        for side in list(sides):
            #Have we seen this before?
            deposit_txid = contract[side]["deposit_txid"]
            if not deposit_txid in self.green_addresses:
                continue

            #Find a valid contract output.
            instance = self.green_addresses[deposit_txid]
            index = 1
            for vout in instance["contract"]["vouts"]:
                #Is this our contract?
                ecdsa_us = contract[side]["ecdsa"]
                ecdsa_them = contract[sides[side]]["ecdsa"]
                ecdsa_arbiter = ECDSACrypt(self.config["arbiter_key_pairs"][0]["pub"])
                redeem_script = bond_redeem_script(ecdsa_us, ecdsa_them, ecdsa_arbiter)
                redeem_script_hash160 = hash160_script(redeem_script)
                p2sh_script_pub_key = CScript([OP_HASH160, redeem_script_hash160["bin"], OP_EQUAL])
                if vout.scriptPubKey != p2sh_script_pub_key:
                    index += 1
                    continue

                #Do the amounts add up?
                vout_amount = Decimal(str_money_value(vout.nValue))
                if side == "buyer":
                    calibrated_amount = contract["trade"].total.as_decimal
                    calibrated_amount -= contract["buyer"]["chunk_size"].as_decimal
                else:
                    calibrated_amount = contract["trade"].amount.as_decimal
                    calibrated_amount -= contract["seller"]["chunk_size"].as_decimal

                if vout_amount < calibrated_amount:
                    print("Insufficent vout_amount.")
                    index += 1
                    continue

                #Record details.
                found[side] = {
                    "instance": instance,
                    "vout": vout
                }

                #Save chunk size details.
                instance["chunks"][index] = {}
                instance["chunks"][index]["buyer"] = contract["buyer"]["chunk_size"]
                instance["chunks"][index]["seller"] = contract["seller"]["chunk_size"]
                break

        #Both vouts found -- check they both work.
        if len(list(found)) == 2:
            print("Both vouts found.")
            works = found

            #Lock the outputs in both setups.
            broadcast = []
            for side in list(works):
                instance = works[side]["instance"]
                vout = works[side]["vout"]

                #Lock vouts.
                index = instance["contract"]["vouts"].index(vout) + 1
                if vout not in instance["locked"]:
                    """
                    The magic + 1 is because vout 0 is already for the fee output. Everything after that is the contract followed by a possible change -- this keeps the vout index in the correct order relative to the TX.
                    """
                    instance["locked"].append(index)

                #Their index.
                their_instance = works[sides[side]]["instance"]
                their_vout = works[sides[side]]["vout"]
                their_index = their_instance["contract"]["vouts"].index(their_vout) + 1

                #Save instance references for matched contract.
                their_instance_id = their_instance["id"]
                instance["contract"]["links"][index] = {
                    "instance_id": their_instance_id,
                    "index": their_index,
                    "contract_hash": contract_hash,
                }

                #This means its ready to broadcast.
                if len(instance["contract"]["vouts"]) == len(instance["locked"]):
                    """
                    The old TXID for the unsigned transaction is intentionally used to make the client-side logic easier for parsing status messages. Basically, it will tell the client which signed transaction corresponds to their original unsigned transaction and hence which coin client to broadcast it to. 
                    """
                    tx_info = {
                        "tx": instance["setup"]["signed"]["tx"],
                        "txid": instance["setup"]["txid"]
                    }
                    broadcast.append(tx_info)

            #All inputs locked - broadcast setup TX.
            if len(broadcast) == 2:
                print(broadcast[0])
                print(broadcast[1])
                print("Broadcasting bruh.")

                #Check fee output is correct.
                trade_fee = C(self.config["trade_fee"])
                valid_fees = 1
                for side in list(works):
                    instance = works[side]["instance"]
                    collateral = C(0)
                    index = 1

                    #Add up micro-collateral amounts.
                    for vout in instance["contract"]["vouts"]:
                        #Have the chunk amounts been recorded?
                        if index not in instance["chunks"]:
                            break

                        chunks = instance["chunks"][index]
                        if "buyer" not in chunks:
                            break
                        if "seller" not in chunks:
                            break

                        #Calculate relative chunk size.
                        vout_amount = Decimal(str_money_value(vout.nValue))
                        collateral += chunks[side]

                        #Next contract vout.
                        index += 1

                    #Check trade fee.
                    total_coins = C(instance["fee"]["total"]) + instance["contract"]["total"]
                    change = C(instance["change"]["total"])
                    expected_fee = collateral + ((total_coins - change) * trade_fee)

                    #Check fee output amount.
                    if expected_fee != C(instance["fee"]["total"]):
                        print("Invalid fees")
                        print(expected_fee)
                        print(C(instance["fee"]["total"]))
                        valid_fees = 0

                #Broadcast.
                if valid_fees:
                    #There's no circuit checks or anything at this point.
                    #This is a prototype.
                    for side in list(works):
                        #Build ready message.
                        instance = works[side]["instance"]
                        ready_msg = self.new_ready_msg(instance["id"], instance["setup"]["sig_3"], instance["contract"]["links"])
                        print(ready_msg)

                        #Send message to client.
                        ident = instance["con"]["ip_addr"] + ":" + str(instance["con"]["port"])
                        if ident in self.clients:
                            print("Successfully broadcast")
                            self.clients[ident].send_line(ready_msg)
                else:
                    print("Did not broadcast - invalid fees")

        return []

    def new_ready_msg(self, instance_id, sig_3, links):
        msg = "%s " % (str(self.version))
        msg += "%s " % (str(int(self.hybrid_protocol.sys_clock.time())))
        msg += "READY %s " % (instance_id)
        msg += "%s" % (base64.b64encode(sig_3).decode("utf-8"))

        setup_details = ""
        collateral_info = ""
        for vout_index in list(links):
            link = links[vout_index]
            instance = self.instances[link["instance_id"]]
            setup_txid = instance["setup"]["signed"]["txid"]
            contract_hash = link["contract_hash"]
            setup_details += " %s@%s" % (setup_txid, contract_hash)

            info = instance["collateral_info"][contract_hash]
            if type(info) == str:
                info = info.encode("ascii")
            collateral_info += " %s" % (base64.b64encode(info).decode("utf-8"))

        msg += setup_details + collateral_info

        return msg

    def parse_update_msg(self, msg, version, ntp, con=None):
        pass

    def buildProtocol(self, addr):
        return ContractProtocol(self)

if __name__ == '__main__':
    server_key = os.path.join(data_dir, 'server.key')
    server_crt = os.path.join(data_dir, 'server.crt') 
    reactor.listenSSL(int(config["contract_server"]["port"]), ContractFactory(config),
                      ssl.DefaultOpenSSLContextFactory(server_key, server_crt))
    print("Starting contract server.")
    reactor.run()



