"""
Implements the p2p trading protocol.
"""


from .globals import *
from .database import *
from .sys_clock import *
from .proof_of_work import *
from .currency_type import *
from .nacl_crypt import *
from .ecdsa_crypt import *
from .lib import *
from .microtransfer_contract import *
from .private_key import *
from .address import *
from .trade_engine import *
from .trades import *
from .order_book import *
from .trade_type import *
from .order_type import *
from .match_type import *
from .match_state import *
from .green_address import *
from .contract_client import *
from .password_complexity import *
from .hybrid_reply import *
import re
from decimal import Decimal
import socket
import hashlib
import binascii
import copy
from bitcoin import SelectParams
from bitcoin.core import b2x, b2lx, lx, x, COIN, COutPoint, CTxOut, CTxIn, CTransaction, Hash160, Serializable, str_money_value
from bitcoin.core.script import CScript, OP_DUP, OP_NUMEQUAL, OP_DROP, OP_HASH160, OP_EQUALVERIFY, OP_CHECKSIG, SignatureHash, SIGHASH_ALL, SIGHASH_ANYONECANPAY, SIGHASH_SINGLE, OP_IF, OP_CHECKMULTISIGVERIFY, OP_NOTIF, OP_ELSE, OP_ENDIF, OP_VERIFY, OP_SHA256, OP_CHECKSIGVERIFY, OP_CHECKMULTISIG, OP_EQUAL, OP_FALSE, OP_3, OP_0, OP_1, OP_2, OP_5, OP_4, OP_TOALTSTACK, OP_TRUE, OP_DEPTH
from bitcoin.core.scripteval import VerifyScript, SCRIPT_VERIFY_P2SH
from bitcoin.wallet import CBitcoinAddress, CBitcoinSecret, CKey

class HybridProtocol():
    def __init__(self, config, sys_clock, nacl_crypt, net, coins, exchange_rate, trade_engine, contract_client=None):
        self.config = config
        self.sys_clock = sys_clock
        self.nacl_crypt = nacl_crypt
        self.ecdsa_crypt = ECDSACrypt()
        self.net = net
        self.coins = coins
        self.exchange_rate = exchange_rate
        self.trade_engine = trade_engine
        self.proof_of_work = ProofOfWork()
        self.version = 1
        self.contract_client = contract_client

        #What messages will we support?
        self.msg_handlers = {
            "open_order": self.parse_open_order,
            "match_order": self.parse_match_order,
            "shake_on_it": self.parse_shake_on_it,
            "get_refund_sig": self.parse_get_refund_sig,
            "return_refund_sig": self.parse_return_refund_sig,
            "get_setup_tx": self.parse_get_setup_tx,
            "return_setup_tx": self.parse_return_setup_tx,
            "return_adjusted_refund": self.parse_return_adjusted_refund
        }

    def calculate_msg_id(self, msg):
        msg_hash = hashlib.sha256(msg.encode("ascii")).digest()
        msg_hash = binascii.hexlify(msg_hash).decode("utf-8")
        return msg_hash

    def understand(self, msg, seen_messages, con=None):
        try:
            replies = parse_msg(msg, self.version, con, self.msg_handlers, self.sys_clock, self.config)
            if type(replies) == list:
                replies = list(filter(self.net.filter_old_messages, replies))

            return replies
        except Exception as e:
            error = parse_exception(e)
            log_exception(error_log_path, error)
            print(error)
            return []

    def parse_match_order(self, msg, version, ntp, con):
        #protocol_version ntp match_order order_hash match_hash action
        #pair amount ppc base_usd_rate:quote_usd_rate [routes ...]
        #deposit_txid inputs address public_key_1 public_key_2
        #encrypted_key sig_1 sig_2 nonce
        matches = re.findall("(match_order) ([a-zA-Z0-9]+) ([a-zA-Z0-9]+) (buy|sell) ([a-z@]{1,56})/([a-z@]{1,56}) ([0-9]{1,19}(?:[.][0-9]{1,16})?) ([0-9]{1,19}(?:[.][0-9]{1,16})?) ([0-9]{1,19}(?:[.][0-9]{1,16})?):([0-9]{1,19}(?:[.][0-9]{1,16})?) ((?:[,]?[\[](?:passive|simultaneous|relay) (?:[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}) (?:[0-9]{1,5})(?: (?:[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}) (?:[0-9]{1,5}))?[\]])+) ([a-zA-Z0-9]+) ((?:\s?[{](?:[0-9]+)[}])+) ([0-9a-zA-Z]{1,40}) ([^\s]{1,256}) ([^\s]{1,256}) ([^\s]{1,256}) ([^\s]{1,256}) ([^\s]{1,256}) ([0-9]{1,100})$", msg)

        if len(matches):
            #Deserialize.
            rpc, order_hash, match_hash, action, base, quote, amount, ppc, base_usd_worth, quote_usd_worth, routes, deposit_txid, inputs, address, pub_key_1, pub_key_2, server_pub_key, sig_1, sig_2, nonce = matches[0]
            base_usd_worth = C(base_usd_worth)
            quote_usd_worth = C(quote_usd_worth)
            amount = C(amount)
            ppc = C(ppc)
            nonce = int(nonce)
            match_trade = Trade(action, amount, [base, quote], ppc, status="open")
            match_trade.recv_addr = address
            ecdsa_1 = ECDSACrypt(pub_key_1)
            ecdsa_2 = ECDSACrypt(pub_key_2)
            ecdsa_encrypted = ECDSACrypt(server_pub_key)

            #Check we can match this with our clients.
            if match_trade.pair["base"] not in self.coins:
                print("Match a.")
                return []
            if match_trade.pair["quote"] not in self.coins:
                print("Match b.")
                return []

            #Check proof of work.
            initial_msg = msg.split(" ")
            remove_nonce = initial_msg.pop()
            initial_msg = " ".join(initial_msg)
            if not self.proof_of_work.is_valid(initial_msg, nonce):
                print("Match c")
                return []

            #Check signature.
            initial_msg = initial_msg.split(" ")
            sig_2 = initial_msg.pop()
            sig_1 = initial_msg.pop()
            initial_msg = " ".join(initial_msg)
            if not ecdsa_1.valid_signature(sig_1, initial_msg):
                print("Match d")
                return []
            if not ecdsa_2.valid_signature(sig_2, initial_msg):
                print("Match e")
                return []

            """
            Check green address.

            Note that a user could generate their own encrypted key pair and claim that the server generated it which would allow double-spends prior to contract setup. Those conditions aren't checked here but the microtransfer_server checks all green addresses and will reject any address with the incorrect leverage.
            """
            try:
                green_address = GreenAddress(match_trade, ecdsa_1, ecdsa_2, ecdsa_encrypted, self.coins, self.config, None, deposit_txid)
            except Exception as e:
                error = parse_exception(e)
                print(error)
                print("Match f")
                print(deposit_txid)
                print(match_trade)
                exit()
                #TODO: remove exit.
                return []

            #Check unspent.
            inputs_total = C("0")
            tx_out = green_address.get_input()
            if tx_out == None:
                print("Match g")
                return []

            #Increment inputs total.
            inputs_total = inputs_total + C(tx_out["amount"])

            #Check they can cover trade.
            if inputs_total < match_trade.to_send:
                print(inputs_total)
                print(match_trade.to_send)
                print("User cannot cover trade.")
                print("Match h")
                print(match_trade)
                print(match_trade.fees)
                return []

            #Parse routes.
            routes = self.parse_routes(routes)
            if not len(routes):
                print("Match i")
                return []

            #Pack match.
            match = MatchType(version, ntp, order_hash, self.calculate_msg_id(msg), match_trade, base_usd_worth, quote_usd_worth, routes, green_address, address, ecdsa_1, ecdsa_2, sig_1, sig_2, nonce)

            print("In match.")

            #This is a reply to our order.
            replies = []
            matched = None
            if match_hash == "0":
                #Search for our open trade.
                match_hash = match.match_hash
                for our_trade in self.trade_engine.trades:
                    #Trade not found.
                    print(our_trade.order_hash)
                    print(type(our_trade.order_hash))
                    print(match.order_hash)
                    print(type(match.order_hash))
                    if our_trade.order_hash != match.order_hash:
                        print("Order hash !=")
                        print(our_trade.order_hash)
                        print(match.order_hash)
                        continue

                    #Direct connections only.
                    if our_trade.dest_ip != "":
                        print("Match dest ip check.")
                        #We're not trading with this person.
                        if our_trade.dest_ip != con.s.getpeername()[0]:
                            print("Match dest ip skipping.")
                            continue

                    #Invalid trade status.
                    if our_trade.status != "open":
                        print("Match order status skipping.")
                        continue

                    #Trades can't match.
                    if our_trade != match_trade:
                        print("Trades != 2")
                        print("Our trade = ")
                        print(our_trade)
                        print("Match trade = ")
                        print(match_trade)
                        continue

                    #Load order from order book.
                    order = self.trade_engine.order_book.get_order(order_hash)
                    if order == None:
                        print("Unable to load order 1.")
                        print("Match j")
                        return []
                    ecdsa_1 = order.ecdsa_1

                    """
                    Calibrated reply not sent.
                    This is a new match request so set matched.reply.
                    """
                    our_trade.matches[match_hash] = MatchState(None, match, order)

                    """
                    Calculate calibrated trade - the trade which will define amounts for the contracts. The reason the
                    trade is recalibrated is some time may have passed
                    between opening an order and receiving a match and
                    the trade amount may be less in reality. This line
                    also matches the trade which simulating coins being swapped for the contract. The result is saved in a
                    new trade to easily generate the calibrated match.
                    """
                    cal_trade = our_trade / match_trade

                    #Generate new match.
                    cal_match_msg, cal_match = self.new_match_order(order_hash, match_hash, cal_trade, our_trade.recv_addr, order.ecdsa_1, order.ecdsa_2, order.green_address)
                    matched = our_trade.matches[match_hash]
                    matched.match_sent = cal_match

                    #Update state.
                    matched.update_state("pending_handshake")

                    #Return calibrated match.
                    replies.append(cal_match_msg)
            else:
                """
                It's a calibrated reply to something we sent.
                Find our corresponding match and check its not an
                impersonation. 
                """
                for our_trade in self.trade_engine.trades:
                    #Trade not found.
                    if match_hash not in our_trade.matches:
                        print("Order match !=")
                        print(our_trade.matches)
                        print(match_hash)
                        continue

                    #Check state is correct.
                    matched = our_trade.matches[match_hash]
                    new_state = "pending_handshake"
                    if not matched.state_machine(new_state):
                        print("Match k")
                        return []

                    """
                    Check match reply isn't an impersonation. If the
                    public keys don't match with the original order
                    then someone injected this.
                    """
                    if matched.match_sent.order_hash != order_hash:
                        print("Match l")
                        return []

                    order = self.trade_engine.order_book.get_order(order_hash)
                    if order == None:
                        print(order_hash)
                        print("Match m")
                        return []
                    if order.ecdsa_1.get_public_key() != ecdsa_1.get_public_key():
                        print("Match n")
                        return []

                    #Trades can't match.
                    temp_trade = our_trade.copy()
                    temp_trade.status = "open"
                    temp_trade.remaining = C("1")
                    if temp_trade != match_trade:
                        print("Trades != 1")
                        print("Our trade = ")
                        print(temp_trade)
                        print(match_trade)

                    """
                    Set ecdsa_1 for signing the handshake used to
                    accept the contract.
                    """
                    ecdsa_1 = matched.match_sent.ecdsa_1

                    """
                    Reverse old match. These are the coins we reserved
                    by applying the match earlier against an order in
                    the order book.
                    """
                    our_trade * matched.order.trade

                    #Apply new match.
                    our_trade / match_trade

                    #Update state.
                    matched.match_reply = match
                    matched.update_state(new_state)

            #Nothing to match.
            if matched == None:
                print("Nothing to match.")
                return []

            #Build contract.
            ret = self.format_contract(matched.match_reply, matched.match_sent)
            if ret != None:
                #Store contract.
                contract_msg, calibrated = ret
                matched.contract = self.parse_contract(contract_msg)
                matched.contract_hash = matched.contract["contract"]["hash"]

                #Sign contract.
                our_handshake_msg = self.new_shake_on_it(contract_msg, ecdsa_1)
                matched.our_handshake_msg = our_handshake_msg
                replies.append(our_handshake_msg)

                #Return replies.
                print("Returning matched replies.")
                return [HybridReply(replies, "any", "source")]
            else:
                print("Format contract failed.")
        else:
            print("Match format was wrong!")
            print("Match format was wrong!")
            print("Match format was wrong!")
            print("Match format was wrong!")

        return []


    def parse_open_order(self, msg, version, ntp, con=None):
        global tx_monitor

        print("In open order.")
        print(msg)
        #protocol_version ntp rpc action pair amount ppc
        # [routes ...] deposit_txid address public_key_1 public_key_2
        # server_pub_key sig_1 sig_2 nonce
        matches = re.findall("(open_order) (buy|sell) ([a-z@]{1,56})/([a-z@]{1,56}) ([0-9]{1,19}(?:[.][0-9]{1,16})?) ([0-9]{1,19}(?:[.][0-9]{1,16})?) ((?:[,]?[\[](?:passive|simultaneous|relay) (?:[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}) (?:[0-9]{1,5})(?: (?:[^\s]{1,255}) (?:[0-9]{1,5}))?[\]])+) ([0-9a-zA-Z]+) ([0-9a-zA-Z]{1,40}) ([^\s]{1,256}) ([^\s]{1,256}) ([^\s]{1,256}) ([^\s]{1,256}) ([^\s]{1,256}) ([0-9]{1,100})$", msg)
        if matches:
            print("Matches true>")

            #Deserialize.
            rpc, action, base, quote, amount, ppc, routes, deposit_txid, addr, pub_key_1, pub_key_2, server_pub_key, sig_1, sig_2, nonce = matches[0]
            amount = C(amount)
            ppc = C(ppc)
            nonce = int(nonce)
            ecdsa_1 = ECDSACrypt(pub_key_1)
            ecdsa_2 = ECDSACrypt(pub_key_2)
            ecdsa_encrypted = ECDSACrypt(server_pub_key)

            #Check proof of work.
            order_hash = self.calculate_msg_id(msg)
            initial_msg = msg.split(" ")
            remove_nonce = initial_msg.pop()
            initial_msg = " ".join(initial_msg)
            if not self.proof_of_work.is_valid(initial_msg, nonce):
                print("Invalid pow in open order.")
                return []

            #Check signature.
            initial_msg = initial_msg.split(" ")
            sig_2 = initial_msg.pop()
            sig_1 = initial_msg.pop()
            initial_msg = " ".join(initial_msg)
            if not ecdsa_1.valid_signature(sig_1, initial_msg):
                print("Invalid ecdsa sig 1 in open order.")
                return []
            if not ecdsa_2.valid_signature(sig_2, initial_msg):
                print("Invalid ecdsa sig 2 in open order.")
                return []

            #Parse routes.
            routes = self.parse_routes(routes)
            if not len(routes):
                print("Invalid routes in open order.")
                return []

            #Record new open position for the network.
            pair = [base, quote]
            trade = Trade(action, amount, pair, ppc, status="open")
            trade.recv_addr = addr
            green_address = GreenAddress(trade, ecdsa_1, ecdsa_2, ecdsa_encrypted, self.coins, self.config, None, deposit_txid, use_rpc=0)
            order = OrderType(order_hash, version, ntp, trade, routes, green_address, addr, ecdsa_1, ecdsa_2, sig_1, sig_2, nonce) 
            self.trade_engine.order_book.open_order(version, ntp, trade, routes, addr, ecdsa_1, ecdsa_2, sig_1, nonce, order_hash)
            print("Openning order.")

            """
            If there are existing green address deposits we don't record the last seen hash for this message since this open order might be a valid message to one of our pending trades.
            """
            replies = [HybridReply([msg], "p2p_net", "everyone")]
            if len(tx_monitor.find_watch_partial("green_address_deposit")):
                print("Record seen disabled.")
                replies[0].record_seen = 0
                return replies
            else:
                print("No pending green address deposits.")

            """
            Timeout old matches for our trade. This can be exploited to DoS the p2p order book but this is only a prototype. In the future the matching engine will probably be blockchain based and be replaced completely. 
            """
            their_trade = trade
            their_order = order
            for our_trade in self.trade_engine.trades:
                expired_matches = []
                for match_hash in list(our_trade.matches):
                    matched = our_trade.matches[match_hash]
                    elapsed = int(time.time() - matched.state_updated)
                    if elapsed >= 60 * 5 and matched.state == "pending_calibration" and matched.match_reply == None and matched.order != None:
                        #Undo reserve coins.
                        our_trade * matched.order.trade

                        #Expire old matched.
                        expired_matches.append(match_hash)

                #Expire old matches.
                for expired_match in expired_matches:
                    print("Deleting expired match~~~~~~~~")
                    print("\a\a\a")
                    del our_trade.matches[expired_match]

            """
            Attempt to match against this order.
            This is only done if they're the seller and we have buying ositions.
            The matching logic in the beta release wont be this crappy.
            """
            print(their_trade.actor)
            if their_trade.actor == "seller":
                #Have we already matched with this order?
                #Todo: remove this when partial matching is done.
                for our_trade in self.trade_engine.trades:
                    for match_hash in list(our_trade.matches):
                        matched = our_trade.matches[match_hash]
                        if matched != None:
                            if matched.match_sent.order_hash == their_order.order_hash:
                                return replies

                #Attempt to match order.
                for our_trade in self.trade_engine.trades:
                    if our_trade == their_trade:
                        print("Found our trade.")
                        """
                        When doing trade tests on the same machine and sharing the same database, you will see trades from ourself - skip them to avoid connection errors.
                        """
                        global direct_net
                        print(our_trade.dest_ip)
                        if not direct_net.validate_node(our_trade.dest_ip, None, same_nodes=0):
                            print("Validate node failed.")
                            continue                        

                        #Already processed this trade.
                        if our_trade.order_hash == "":
                            #Generate open order message.
                            open_msg, our_order = self.new_open_order(our_trade, our_trade.recv_addr, our_trade.green_address)
                            our_trade.open_msg = open_msg
                            our_trade.order = our_order
                            our_trade.order_hash = our_order.order_hash
                            self.trade_engine.order_book.orders.append(our_order)
                            our_trade.update()
                        else:
                            open_msg = our_trade.open_msg
                            our_order = our_trade.order

                        #Generate match to send.
                        match_msg, match = self.new_match_order(their_order.order_hash, "0", our_trade, our_trade.recv_addr, our_trade.green_address.ecdsa_1, our_trade.green_address.ecdsa_2, our_trade.green_address)
                        match_hash = self.calculate_msg_id(match_msg)

                        #Apply new match to reserve coins.
                        matched_order = their_order.copy()
                        our_trade / their_trade

                        #Update state.
                        our_trade.matches[match_hash] = MatchState(match, None, their_order)
                        our_trade.matches[match_hash].update_state("pending_calibration")

                        #Broadcast new match.
                        print(routes)
                        reply = HybridReply([open_msg, match_msg], "any", "route")
                        reply.add_routes(routes)
                        replies.append(reply)

                        print("End found trade.")

                        #Lets keep this simple.
                        break

            #Return message for propagation.
            return replies

        return []

    def parse_routes(self, routes):
        temp_routes = []
        routes = list(filter(None, routes.split(",")))
        for route in routes:
            temp_route = re.findall("[,]?[\[](passive|simultaneous|relay) ([0-9]+[.][0-9]+[.][0-9]+[.][0-9]+) ([0-9]+)(?: ([^\s]+) ([0-9]+))?[\]]", route)
            if self.config["debug"]:
                is_valid_ip = is_ip_valid
            else:
                is_valid_ip = is_ip_public
            if len(temp_route):
                temp_route = list(temp_route[0])
                if not is_valid_ip(temp_route[1]):
                    print("Route: invalid IP" + str(temp_route[1]))
                    continue

                if not is_valid_port(temp_route[2]) and temp_route[0] != "simultaneous":
                    print("Route: invalid port" + str(temp_route[2]))
                    continue

                if temp_route[0] == "simultaneous" or temp_route[0] == "relay":
                    try:
                        socket.gethostbyname(temp_route[3])
                    except Exception as e:
                        print(e)
                        print("Route: gethostbyname" + str(temp_route[3]))
                        continue
                    if not is_valid_port(temp_route[4]):
                        print("Route: valid port" + str(temp_route[4]))
                        continue

                temp_routes.append(temp_route)

        return temp_routes

    def format_routes(self):
        #Routes should probably be replaced with UNL which is cleaner.
        #What address should be used for the route?
        global local_only
        global direct_node_type
        global direct_port
        global direct_net
        if local_only:
            if direct_net.passive_bind == "0.0.0.0":
                bind_addr = get_lan_ip(direct_net.interface)
            else:
                bind_addr = direct_net.passive_bind

            if bind_addr == None:
                raise Exception("Unable to get LAN IP for interface.")
        else:
            bind_addr = get_wan_ip()

        msg = ""
        if direct_node_type == "unknown":
            raise Exception("Unknown node_type for format_routes.")
        elif direct_node_type == "passive":
            
            msg += " [passive %s %s]" % (bind_addr, direct_port)
        elif direct_node_type == "simultaneous":
            index = random_index_in_list(config["rendezvous_servers"])
            rendezvous = config["rendezvous_servers"][index]
            msg += " [simultaneous %s 0 %s" % (bind_addr, rendezvous["addr"])
            msg += " %s]" % (rendezvous["port"])
        else:
            #Relay isn't supported yet.
            passive_nodes = []
            for node in self.net.inbound + self.net.outbound:
                if node["type"] == "passive":
                    passive_nodes.append(node)
            passive_nodes = passive_nodes[:4] #Max 4.
            for node in passive_nodes:
                msg += " [relay %s 0 %s" % (bind_addr, node["ip"])
                msg += " %s]" % (node["port"])

            #Use main server to relay.
            if not len(passive_nodes):
                msg += " [relay %s 0" % (bind_addr)
                msg += " %s" % (config["rendezvous_servers"][0]["addr"])
                msg += " %s]" % (config["rendezvous_servers"][0]["port"])

        return msg

    def new_shake_on_it(self, contract_msg, ecdsa_1):
        msg = "%s " % (str(self.version))
        msg += "%s shake_on_it " % (str(int(self.sys_clock.time())))
        msg += "%s" % (str(hashlib.sha256(contract_msg.encode("ascii")).hexdigest()))

        #Sign message.
        sig = ecdsa_1.sign(msg)
        msg += " %s" % (str(sig))

        return msg

    def new_get_refund_sig(self, contract_hash, refund_tx_hex, ecdsa_1):
        msg = "%s " % (str(self.version))
        msg += "%s get_refund_sig " % (str(int(self.sys_clock.time())))
        msg += "%s " % (str(contract_hash))
        msg += "%s" % (refund_tx_hex)

        #Sign message.
        sig = ecdsa_1.sign(msg)
        msg += " %s" % (str(sig))

        return msg

    def parse_get_refund_sig(self, msg, version, ntp, con=None):
        matches = re.findall("(get_refund_sig) ([^\s]{1,256}) ([^\s]{1,4000}) ([^\s]{1,256})$", msg)
        if len(matches):
            #Parse matches.
            rpc, contract_hash, refund_tx_hex, sig = matches[0]

            #Find microtransfer contract + factory.
            contract = None
            contract_factory = None
            our_trade = None
            matched = None
            for trade in self.trade_engine.trades:
                if trade.contract_factory == None:
                    continue

                if contract_hash in trade.contract_factory.contracts:
                    our_trade = trade
                    contract_factory = trade.contract_factory
                    contract = contract_factory.contracts[contract_hash]
                    matched = contract.matched
                    break

            #Check contract.
            if contract == None:
                return []

            #Check they sent this message.
            initial_msg = msg.split(" ")
            sig = initial_msg.pop()
            initial_msg = " ".join(initial_msg)
            if not contract.ecdsa_them[0].valid_signature(sig, initial_msg):
                return []

            #Update state.
            status_checker = None
            if our_trade.actor == "buyer":
                def status_check(hybrid_reply):
                    #Setup TX is still not confirmed in blockchain.
                    if not matched.update_state("pending_buyer_get_refund_sig"):
                        return 0

                    #Setup TX is confirmed - safe to proceed with protocol.
                    return 1

                #Check to see if our setup tx is pending confirmation.
                if matched.state != "pending_buyer_return_refund_sig":
                    #simple mutex -- can only be done once.
                    if matched.state == "pending_buyer_setup_tx_confirm":
                        return []
                    else:
                        if not matched.update_state("pending_buyer_setup_tx_confirm"):
                            return []
                    status_checker = status_check
                else:
                    if not matched.update_state("pending_buyer_get_refund_sig"):
                        return []
            else:
                if not matched.update_state("pending_seller_get_setup_tx"):
                    return []

            #Check their setup txid has been set.
            their_setup_txid = None
            if not contract_hash in contract_factory.setup_txids:
                return []
            else:
                their_setup_txid = contract_factory.setup_txids[contract_hash]

            #Parse refund tx.
            tx = CTransaction.deserialize(binascii.unhexlify(refund_tx_hex))

            #Check txin is as expected.
            if len(tx.vin) != 1:
                return []
            if tx.vin[0].nSequence != 0:
                return []
            setup_txid = b2lx(tx.vin[0].prevout.hash)
            if setup_txid != their_setup_txid:
                return []
            
            #Check nlocktime.
            if tx.nLockTime != contract.nlock_time:
                return []

            #Sign refund transaction.
            refund_sig = contract.sign_refund_tx(refund_tx_hex, 1, "them")

            #Save refund hex.
            contract_factory.refunds[contract_hash] = {
                "tx_hex": refund_tx_hex,
                "our_sig": refund_sig
            }

            #Build reply.
            return_refund_sig_msg = self.new_return_refund_sig(contract_hash, refund_sig, contract.ecdsa_us[0])
            new_hybrid_reply = HybridReply([return_refund_sig_msg], "any", "source")
            if status_checker != None:
               new_hybrid_reply.set_status_checker(status_checker)

            #Return reply.
            return [new_hybrid_reply]

        return []

    def new_return_refund_sig(self, contract_hash, refund_sig, ecdsa_1):
        if type(refund_sig) == str:
            refund_sig = refund_sig.encode("ascii")

        msg = "%s " % (str(self.version))
        msg += "%s return_refund_sig " % (str(int(self.sys_clock.time())))
        msg += "%s " % (str(contract_hash))
        msg += "%s" % (base64.b64encode(refund_sig).decode("utf-8"))

        #Sign message.
        sig = ecdsa_1.sign(msg)
        msg += " %s" % (str(sig))

        return msg

    def new_get_setup_tx(self, contract_hash, setup_txid, ecdsa_1):
        msg = "%s " % (str(self.version))
        msg += "%s get_setup_tx " % (str(int(self.sys_clock.time())))
        msg += "%s " % (str(contract_hash))
        msg += "%s" % (str(setup_txid))

        #Sign message.
        sig = ecdsa_1.sign(msg)
        msg += " %s" % (str(sig))

        return msg

    def new_return_adjusted_refund(self, contract_hash, tx_hex, sig_1, sig_2, ecdsa_1):
        if type(sig_1) == str:
            sig_1 = sig_1.encode("ascii")
        if type(sig_2) == str:
            sig_2 = sig_2.encode("ascii")

        msg = "%s " % (str(self.version))
        msg += "%s return_adjusted_refund " % (str(int(self.sys_clock.time())))
        msg += "%s " % (str(contract_hash))
        msg += "%s " % (str(tx_hex))
        msg += "%s " % (base64.b64encode(sig_1).decode("utf-8"))
        msg += "%s" % (base64.b64encode(sig_2).decode("utf-8"))

        #Sign message.
        sig = ecdsa_1.sign(msg)
        msg += " %s" % (str(sig))

        return msg

    def new_return_setup_tx(self, contract_hash, tx_hex, collateral_info, ecdsa_1):
        msg = "%s " % (str(self.version))
        msg += "%s return_setup_tx " % (str(int(self.sys_clock.time())))
        msg += "%s " % (str(contract_hash))
        msg += "%s " % (str(tx_hex))

        #Should be a list of base64 encoded collateral messages.
        for info in collateral_info:
            msg += "%s@" % info

        #Sign message.
        sig = ecdsa_1.sign(msg)
        msg += " %s" % (str(sig))

        return msg

    def parse_collateral_info(self, collateral_info_msg):
        collateral_info = base64.b64decode(collateral_info_msg.encode("ascii")).decode("utf-8")
        chunk_size, arbiter_pub, sig_1, pub_1, sig_2, pub_2 = collateral_info.split(" ")
        chunk_size = C(chunk_size)
        collateral_info = {
            "msg": collateral_info_msg,
            "chunk_size": chunk_size, 
            "sig_1": sig_1,
            "sig_2": sig_2,
            "pub_1": pub_1,
            "pub_2": pub_2,
            "pub_arbiter": arbiter_pub
        }
        
        return collateral_info

    def parse_return_adjusted_refund(self, msg, version, ntp, con=None):
        matches = re.findall("(return_adjusted_refund) ([^\s]{1,256}) ([^\s]{1,10240}) ([^\s]{1,256}) ([^\s]{1,256}) ([^\s]{1,256})$", msg)
        if len(matches):
            #Parse matches.
            rpc, contract_hash, refund_tx, refund_sig_1, refund_sig_2, msg_sig = matches[0]
            refund_sig_1 = base64.b64decode(refund_sig_1.encode("ascii"))
            refund_sig_2 = base64.b64decode(refund_sig_2.encode("ascii"))

            #Find microtransfer contract + factory.
            contract = None
            contract_factory = None
            our_trade = None
            matched = None
            for trade in self.trade_engine.trades:
                if trade.contract_factory == None:
                    continue

                if contract_hash in trade.contract_factory.contracts:
                    our_trade = trade
                    contract_factory = trade.contract_factory
                    contract = contract_factory.contracts[contract_hash]
                    matched = contract.matched
                    break

            #Check contract.
            if contract == None:
                print("e222222")
                return []

            #Check state.
            if our_trade.actor == "buyer":
                if matched.state != "buyer_accept_microtransfer":
                    return []
            else:
                if matched.state != "seller_accept_microtransfer":
                    return []

            #Check they sent this message.
            initial_msg = msg.split(" ")
            sig = initial_msg.pop()
            initial_msg = " ".join(initial_msg)
            if not contract.ecdsa_them[0].valid_signature(sig, initial_msg):
                print("e3333333")
                return []

            #Adjust refund.
            our_setup_txid = contract_factory.setup["signed"]["txid"]
            their_setup_hex = contract_factory.setups[contract_hash]["tx_hex"]
            their_refund_hex = contract_factory.refunds[contract_hash]["tx_hex"]
            ret = contract.adjust_refund_tx(our_setup_txid, their_setup_hex, their_refund_hex, refund_tx, refund_sig_1, refund_sig_2)
            print("parse return adjusted refund.")
            print(ret)

            #Return result if its needed.
            msg = ""
            if type(ret) == dict:
                ecdsa_1 = contract_factory.green_address.ecdsa_1
                msg = self.new_return_adjusted_refund(contract_hash, ret["tx_hex"], ret["first_sig"], ret["second_sig"], ecdsa_1)
            
            if contract_factory.contracts[contract_hash].trade.sent == contract_factory.contracts[contract_hash].upload_amount and contract_factory.contracts[contract_hash].trade.recv == contract_factory.contracts[contract_hash].download_amount:
                matched.update_state("pending_microtransfer_complete")
                print("\a")
                print("\a")
                print("\a")


            print(contract_factory.contracts[contract_hash].trade.sent)
            print(contract_factory.contracts[contract_hash].upload_amount)
            print(contract_factory.contracts[contract_hash].trade.recv)
            print(contract_factory.contracts[contract_hash].download_amount)

            return [HybridReply(msg, "any", "source")]

        print("e11111")
        return []

    def parse_get_setup_tx(self, msg, version, ntp, con=None):
        matches = re.findall("(get_setup_tx) ([^\s]{1,256}) ([^\s]{1,256}) ([^\s]{1,256})$", msg)
        if len(matches):
            #Parse matches.
            rpc, contract_hash, setup_txid, sig = matches[0]

            #Find microtransfer contract + factory.
            contract = None
            contract_factory = None
            our_trade = None
            matched = None
            for trade in self.trade_engine.trades:
                if trade.contract_factory == None:
                    continue

                if contract_hash in trade.contract_factory.contracts:
                    our_trade = trade
                    contract_factory = trade.contract_factory
                    contract = contract_factory.contracts[contract_hash]
                    matched = contract.matched
                    break

            #Check contract.
            if contract == None:
                return []

            #Check state.
            if our_trade.actor == "buyer":
                if not matched.update_state("pending_buyer_get_setup_tx"):
                    return []
            else:
                if not matched.update_state("seller_initiate_microtransfer"):
                    return []

            #Check they sent this message.
            initial_msg = msg.split(" ")
            sig = initial_msg.pop()
            initial_msg = " ".join(initial_msg)
            if not contract.ecdsa_them[0].valid_signature(sig, initial_msg):
                return []

            #Get setup tx.
            setup_tx = contract_factory.setup["signed"]["tx_hex"]
            ecdsa_1 = contract_factory.green_address.ecdsa_1
            collateral_info = []
            for pub_key_1 in list(contract_factory.collateral_info):
                collateral_info.append(contract_factory.collateral_info[pub_key_1]["msg"])

            #Return reply.
            reply = self.new_return_setup_tx(contract_hash, setup_tx, collateral_info, ecdsa_1)
            return [HybridReply(reply, "any", "source")]

        return []

    def parse_return_setup_tx(self, msg, version, ntp, con=None):
        matches = re.findall("(return_setup_tx) ([^\s]{1,256}) ([^\s]+)((?:\s[^\s@]+[@])+) ([^\s]{1,256})$", msg)
        if len(matches):
            #Parse matches.
            rpc, contract_hash, setup_tx_hex, collateral_info, sig = matches[0]

            #Find microtransfer contract + factory.
            contract = None
            contract_factory = None
            our_trade = None
            matched = None
            for trade in self.trade_engine.trades:
                if trade.contract_factory == None:
                    continue

                if contract_hash in trade.contract_factory.contracts:
                    our_trade = trade
                    contract_factory = trade.contract_factory
                    contract = contract_factory.contracts[contract_hash]
                    matched = contract.matched
                    break

            #Check contract.
            if contract == None:
                return []

            #Check they sent this message.
            initial_msg = msg.split(" ")
            sig = initial_msg.pop()
            initial_msg = " ".join(initial_msg)
            if not contract.ecdsa_them[0].valid_signature(sig, initial_msg):
                return []

            #Parse collateral_info.
            temp = {}
            collateral_info = filter(None, collateral_info.split(" "))
            for info in collateral_info:
                info = self.parse_collateral_info(info)
                temp[info["pub_1"]] = info
            collateral_info = temp

            #Check signed setup TX is valid.
            ecdsa_1, ecdsa_2, temp = contract.ecdsa_them
            sig_1 = sig_2 = sig_3 = None
            trade_fee = C(self.config["trade_fee"])
            ret = validate_setup_tx(self.config, setup_tx_hex, ecdsa_1, ecdsa_2, sig_1, sig_2, sig_3, collateral_info, trade_fee)
            if type(ret) != dict:
                return []

            #Check their setup txid has been set.
            their_setup_txid = None
            if not contract_hash in contract_factory.setup_txids:
                return []
            else:
                their_setup_txid = contract_factory.setup_txids[contract_hash]

            #Check setup txid is valid.
            txid = calculate_txid(setup_tx_hex)
            if txid != their_setup_txid:
                return []

            #Check state.
            if our_trade.actor == "seller":
                if not matched.update_state("pending_seller_return_setup_tx"):
                    return []
            else:
                if not matched.update_state("buyer_accept_microtransfer"):
                    return []

            #Store their setup tx.
            contract_factory.setups[contract_hash] = {
                "tx_hex": setup_tx_hex,
                "txid": txid
            }

        return []

    def parse_return_refund_sig(self, msg, version, ntp, con=None):
        matches = re.findall("(return_refund_sig) ([^\s]{1,256}) ([^\s]{1,256}) ([^\s]{1,256})$", msg)
        if len(matches):
            #Parse matches.
            rpc, contract_hash, their_sig, sig = matches[0]
            their_sig = base64.b64decode(their_sig.encode("ascii"))

            #Find microtransfer contract + factory.
            contract = None
            contract_factory = None
            our_trade = None
            for trade in self.trade_engine.trades:
                if trade.contract_factory == None:
                    continue

                if contract_hash in trade.contract_factory.contracts:
                    contract_factory = trade.contract_factory
                    contract = contract_factory.contracts[contract_hash]
                    our_trade = trade
                    break

            #Check contract.
            if contract == None:
                return []

            #Check they sent this message.
            initial_msg = msg.split(" ")
            sig = initial_msg.pop()
            initial_msg = " ".join(initial_msg)
            if not contract.ecdsa_them[0].valid_signature(sig, initial_msg):
                return []

            #Check state.
            matched = contract.matched
            if our_trade.actor == "seller":
                if not matched.update_state("pending_seller_return_refund_sig"):
                    return []
            else:
                if not matched.update_state("pending_buyer_return_setup_tx"):
                    return []

            #Check refund works.
            tx_hex = contract_factory.refund["tx_hex"]
            our_sig_1 = contract.sign_refund_tx(tx_hex, 1)
            our_sig_2 = contract.sign_refund_tx(tx_hex, 2)
            refund_works = contract.check_refund_works(tx_hex, our_sig_1, our_sig_2, their_sig, "us")
            if refund_works == None:
                return []

            #Save signed refund details.
            contract_factory.refund["signed"] = refund_works

            return []

        return []

    def find_match_state(self, contract_hash):
        if contract_hash == None:
            raise Exception("Invalid contract hash in find_match_state.")

        for our_trade in self.trade_engine.trades:
            for match_hash in list(our_trade.matches):
                matched = our_trade.matches[match_hash]
                if matched.contract_hash == contract_hash:
                    return matched

        return None

    def parse_shake_on_it(self, msg, version, ntp, con=None):
        print("In parse shake on it")
        print(con)

        #version ntp shake_on_it contract_hash sig
        matches = re.findall("(shake_on_it) ([a-fA-F0-9]+) ([^\s]{1,256})$", msg)
        if not matches:
            print("Invalid shake on it msg")
            return []

        #Deserialize.
        rpc, contract_hash, sig = matches[0]

        #Find match state for contract hash.
        matched = self.find_match_state(contract_hash)
        if matched == None:
            print("Unable to find contract.")
            return []

        #Check match state.
        new_state = "pending_contract"
        if not matched.state_machine(new_state):
            print("Invalid state for parse shake on it.")
            return []

        #Record connection.
        matched.con = con

        #Check sig.
        initial_msg = msg.split(" ")
        initial_msg.pop() #Remove sig.
        initial_msg = " ".join(initial_msg)
        if not matched.match_reply.ecdsa_1.valid_signature(sig, initial_msg):
            print("Invalid signature.")
            return []

        #Unpack contract.
        contract = matched.contract
        contract_msg = contract["contract"]["msg"]

        #Calculate what we have to send.
        if not matched.calibrate_trades():
            print("Unable to calibrate trades with available amounts.")
            return []

        #Register contract with contract server.
        ecdsa_arbiter = ECDSACrypt(self.config["arbiter_key_pairs"][0]["pub"])
        ecdsa_1 = matched.match_sent.green_address.ecdsa_1
        ecdsa_2 = matched.match_sent.green_address.ecdsa_2
        matched.their_handshake_msg = msg

        """
        The proof is from their perspective. They sign how much they think you should be sending (micro-collateral) based on the terms of the contract which is why the chunks are reversed.
        """
        if matched.to_send.actor == "buyer":
            chunk_size = contract["seller"]["chunk_size"]
        else:
            chunk_size = contract["buyer"]["chunk_size"]
        collateral_info = "%s %s" % (chunk_size, ecdsa_arbiter.get_public_key())

        #Register match with contract server.
        sig_1 = ecdsa_1.sign(collateral_info)
        sig_2 = ecdsa_2.sign(collateral_info)
        collateral_info += " %s %s %s %s" % (sig_1, ecdsa_1.get_public_key(), sig_2, ecdsa_2.get_public_key())
        self.register_contract(matched.to_send, matched.match_sent.green_address, contract_msg, matched.our_handshake_msg, matched.their_handshake_msg, collateral_info)

        #Update state.
        matched.update_state(new_state)

        return ["valid"]

    def new_open_order(self, trade, address, green_address):
        #Requisites.
        version = self.version
        ntp = int(self.sys_clock.time())
        formatted_routes = self.format_routes()
        routes = self.parse_routes(formatted_routes)
        public_key_1 = green_address.ecdsa_1.get_public_key()
        public_key_2 = green_address.ecdsa_2.get_public_key()

        #Build message.
        msg = "%s" % (str(version))
        msg += " %s open_order" % (str(ntp))
        msg += " %s" % (str(trade.action))
        msg += " %s" % (str(trade.pair))
        msg += " %s" % (str(trade.amount))
        msg += " %s" % (str(trade.ppc))
        msg += formatted_routes
        msg += " %s" % (green_address.deposit_txid)
        msg += " %s" % (address)
        msg += " %s" % (public_key_1)
        msg += " %s" % (public_key_2)
        msg += " %s" % (green_address.ecdsa_encrypted.get_public_key())

        #Sign message.
        sig_1 = green_address.ecdsa_1.sign(msg)
        sig_2 = green_address.ecdsa_2.sign(msg)
        msg += " %s" % (sig_1)
        msg += " %s" % (sig_2)

        #Proof of work.
        nonce = self.proof_of_work.calculate(msg)
        msg += " %s" % (str(nonce))

        #Package.
        order_hash = self.calculate_msg_id(msg)
        trade.order_hash = order_hash
        order = OrderType(order_hash, version, ntp, trade, routes, green_address, address, green_address.ecdsa_1, green_address.ecdsa_2, sig_1, sig_2, nonce)

        return [msg, order]

    def new_match_order(self, order_hash, match_hash, trade, address, ecdsa_1, ecdsa_2, green_address):
        #Requisites.
        ntp = int(self.sys_clock.time())
        formatted_routes = self.format_routes()
        routes = self.parse_routes(formatted_routes)

        #Build message.
        msg = "%s %s" % (str(self.version), str(ntp))
        msg += " match_order %s %s %s" % (str(order_hash), str(match_hash), trade.action)
        msg += " %s/%s %s" % (str(trade.pair[0]), str(trade.pair[1]), str(trade.amount))
        msg += " %s" % (str(trade.ppc))

        #Get pair value in USD (used for chunk size.)
        counterparty_risk = C(self.config["counterparty_risk"])
        base_usd_worth = self.exchange_rate.currency_converter(counterparty_risk.as_decimal, counterparty_risk.currency, trade.pair.codes["base"])
        base_usd_worth = str(format(base_usd_worth, ".16f"))
        quote_usd_worth = self.exchange_rate.currency_converter(counterparty_risk.as_decimal, counterparty_risk.currency, trade.pair.codes["quote"])
        quote_usd_worth = str(format(quote_usd_worth, ".16f"))
        msg += " %s:%s" % (str(base_usd_worth), str(quote_usd_worth))

        #Set routes.
        msg += formatted_routes

        #Deposit tx.
        msg += " %s" % (green_address.deposit_txid)

        #Create inputs.
        tx_inputs = []
        input_total = Decimal("0")
        for tx_input in green_address.inputs:
            if input_total >= trade.to_send.as_decimal:
                break

            tx_inputs.append(tx_input)
            input_total += tx_input["amount"]
            msg += " {%s}" % (str(tx_input["vout"]))

        #Public keys that protect microtransfer contract + recv address.
        msg += " %s %s" % (str(address), str(ecdsa_1.get_public_key()))
        msg += " %s" % (ecdsa_2.get_public_key())
        msg += " %s" % (green_address.ecdsa_encrypted.get_public_key())

        #Sign msg.
        sig_1 = ecdsa_1.sign(msg)
        sig_2 = ecdsa_2.sign(msg)
        msg += " %s" % (sig_1)
        msg += " %s" % (sig_2)

        #Generate proof of work for entire message.
        nonce = self.proof_of_work.calculate(msg)
        msg += " %s" % (str(nonce))

        #Wrap.
        base_usd_worth = C(base_usd_worth)
        quote_usd_worth = C(quote_usd_worth)
        match = MatchType(self.version, ntp, order_hash, match_hash, trade, base_usd_worth, quote_usd_worth, routes, green_address, address, ecdsa_1, ecdsa_2, sig_1, sig_2, nonce)

        return [msg, match]

    def format_contract(self, match_1, match_2):
        #Which match is buy, which is sell?
        buy_match, sell_match = match_1.buy_sell(match_1, match_2)

        """
        Set alt-coin decimal precision. Some alt-coins have greater precision than this but we're keeping things simple for now.
        """
        decimal.getcontext().prec = 8

        #Calculate timestamp for matching.
        version = self.version
        timestamp = Decimal(buy_match.ntp) + Decimal(sell_match.ntp)
        timestamp = timestamp / Decimal(2)
        timestamp = int(timestamp)

        """
        One of these orders will be the calibrated match - the match
        with the most recent amount of coins for sale. It is this
        value which defines the contract.
        """
        if buy_match.timestamp > sell_match.timestamp:
            amount = buy_match.trade.amount
            ppc = buy_match.trade.ppc
            total = buy_match.trade.total
            match = buy_match
        else:
            amount = sell_match.trade.amount
            ppc = sell_match.trade.ppc
            total = sell_match.trade.total
            match = sell_match

        #Find smallest currency.
        ca = Decimal("0")
        cb = Decimal("0")
        if amount < total:
            a = amount
            b = total
        else:
            a = total
            b = amount

        #Create divisible chunks.
        if a <= Decimal("0.00000999"):
            ca = Decimal("0.00000001")
        else:
            ca = a.as_decimal * Decimal("0.005")

        #Extrapolate cb from ca : a = cb : b
        cb = b.as_decimal * (ca / a.as_decimal)

        #Remove exponents if needed.
        ca = C(ca)
        cb = C(cb)

        #Order chunk sizes.
        chunk_lookup = {}
        if amount < total:
            chunk_lookup["amount"] = ca
            chunk_lookup["total"] = cb
        else:
            chunk_lookup["total"] = ca
            chunk_lookup["amount"] = cb
        
        """
        Calculate unspent inputs for green address. This creates consensus as to the state of the green address for the server to validate and helps to prevent double spends.
        """
        buyer_vouts = ""
        for tx_input in buy_match.green_address.inputs:
            buyer_vouts +=  str(tx_input["vout"]) + "_"
        seller_vouts = ""
        for tx_input in sell_match.green_address.inputs:
            seller_vouts += str(tx_input["vout"]) + "_"

        """
        Build contract string.
        Version, timestamp, order_hash, pair, amount, ppc, buy pub key 1,
        buy pub key 2, server pub key 1, sell pub key 1, sell pub key 2, server pub key 2, buyer_deposit_txid, {buy vouts . . .} seller_deposit_txid, {sell vouts . . .} base_usd_worth, quote_usd_worth, amount_chunk, total_chunk, buy match sig 1, buy match sig 2,
        sell match sig 1, sell match sig 2.
        """

        contract = "%s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s" % (str(self.version),
        str(timestamp),
        buy_match.order_hash,
        str(buy_match.trade.pair),
        str(amount),
        str(ppc),
        buy_match.address,
        sell_match.address,
        buy_match.ecdsa_1.get_public_key(),
        buy_match.ecdsa_2.get_public_key(),
        buy_match.green_address.ecdsa_encrypted.get_public_key(),
        sell_match.ecdsa_1.get_public_key(),
        sell_match.ecdsa_2.get_public_key(),
        sell_match.green_address.ecdsa_encrypted.get_public_key(),
        buy_match.green_address.deposit_txid,
        buyer_vouts,
        sell_match.green_address.deposit_txid,
        seller_vouts,
        str(C(0)),
        str(C(0)),
        str(chunk_lookup["amount"]),
        str(chunk_lookup["total"]),
        buy_match.sig_1,
        buy_match.sig_2,
        sell_match.sig_1,
        sell_match.sig_2)

        return [contract, match]

    def parse_contract(self, contract_msg):
        version, ntp, order_hash, pair, amount, ppc, buyer_address, seller_address, buyer_pub_key_1, buyer_pub_key_2, server_pub_key_1, seller_pub_key_1, seller_pub_key_2, server_pub_key_2, buyer_deposit_txid, buyer_vouts, seller_deposit_txid, seller_vouts, base_usd_worth, quote_usd_worth, amount_chunk, total_chunk, buyer_sig_1, buyer_sig_2, seller_sig_1, seller_sig_1 = contract_msg.split(" ")
        base_usd_worth = C(base_usd_worth)
        quote_usd_worth = C(quote_usd_worth)
        amount_chunk = C(amount_chunk)
        total_chunk = C(total_chunk)
        version = int(version)
        ntp = int(ntp)
        if not deconstruct_address(buyer_address)["is_valid"]:
            raise Exception("Invalid buyer address for parse contract.")
        if not deconstruct_address(seller_address)["is_valid"]:
            raise Exception("Invalid seller address for parse contract.")

        trade = Trade("buy", amount, pair, ppc, order_hash)

        buyer_ecdsa = [
            ECDSACrypt(buyer_pub_key_1),
            ECDSACrypt(buyer_pub_key_2),
            ECDSACrypt(server_pub_key_1)
        ]

        seller_ecdsa = [
            ECDSACrypt(seller_pub_key_1),
            ECDSACrypt(seller_pub_key_2),
            ECDSACrypt(server_pub_key_1)
        ]

        buyer_vouts = list(filter(None, buyer_vouts.split("_")))
        seller_vouts = list(filter(None, seller_vouts.split("_")))
        buyer_vouts = [int(vout) for vout in buyer_vouts]
        seller_vouts = [int(vout) for vout in seller_vouts]

        contract_hash = hashlib.sha256(contract_msg.encode("ascii")).hexdigest()
        if type(contract_hash) == bytes:
            contract_hash = contract_hash.decode("utf-8")
        ret = {
            "contract": {
                "msg": contract_msg,
                "hash": contract_hash
            },
            "trade": trade,
            "version": version,
            "ntp": ntp,
            "order_hash": order_hash,
            "buyer": {
                "address": buyer_address,
                "ecdsa": buyer_ecdsa,
                "vouts": buyer_vouts,
                "deposit_txid": buyer_deposit_txid,
                "chunk_size": total_chunk
            },
            "seller": {
                "address": seller_address,
                "ecdsa": seller_ecdsa,
                "vouts": seller_vouts,
                "deposit_txid": seller_deposit_txid,
                "chunk_size": amount_chunk
            },
            "usd_worth": {
                "base": base_usd_worth,
                "quote": quote_usd_worth
            },
        }

        return ret

    def register_contract(self, trade, green_address, contract_msg, our_handshake_msg, their_handshake_msg, collateral_info):
        #Setup microtransfer contract details.
        details = self.parse_contract(contract_msg)
        if trade.actor == "buyer":
            ecdsa_them = details["seller"]["ecdsa"]
            their_address = details["seller"]["address"]
            our_address = details["buyer"]["address"]
        else:
            ecdsa_them = details["buyer"]["ecdsa"]
            their_address = details["buyer"]["address"]
            our_address = details["seller"]["address"]

        ecdsa_us = [green_address.ecdsa_1, green_address.ecdsa_2]
        chunk_sizes = {
            "buyer": details["buyer"]["chunk_size"],
            "seller": details["seller"]["chunk_size"]
        }
        contract_hash = details["contract"]["hash"]
        matched = self.find_match_state(contract_hash)
        our_trade = self.trade_engine.find_trade(contract_hash)
        contract_factory = our_trade.contract_factory
        contract_factory.our_tx_fee = contract_factory.tx_fee_amount = self.coins[trade.to_send.currency]["tx_fee"]
        contract_factory.their_tx_fee = self.coins[trade.to_recv.currency]["tx_fee"]

        #Add new microtransfer contract for match.
        contract = contract_factory.add_contract(contract_hash, trade, ecdsa_us, ecdsa_them, our_address, their_address, chunk_sizes, details["ntp"], matched)

        #Generate most up-to-date setup transaction.
        ret = contract_factory.build_setup()

        #Build messages.
        instance_id = PasswordComplexity(["uppercase", "lowercase", "numeric"], 30).generate_password()
        contract_factory.instance_id = instance_id
        register_msg = self.contract_client.new_register(ret["tx_hex"], green_address.ecdsa_1, green_address.ecdsa_2, ret["first_sig"], ret["second_sig"], instance_id)
        match_msg = self.contract_client.new_match(contract_msg, our_handshake_msg, their_handshake_msg, collateral_info, instance_id)

        #Update contract server with latest happennings.
        self.contract_client.con.send_line(register_msg)
        self.contract_client.con.send_line(match_msg)

        print(register_msg)
        print(match_msg)


if __name__ == "__main__":
    pass


    



