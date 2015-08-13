"""
The main event loop.
This software is designed to be single-threaded to avoid complexity and deadlocks.
Figure out why the open message isn't being seen

python3.3 -m "coinbend.main" -externalexchange 0 -erateinit BTC_USD_358.03,USD_AUD_1.2116072,LTC_BT0.00996000,DOGE_BTC_0.00000056 -clockskew -29.9615900039672851562500 -trade "sell 0.5 dogecoin/litecoin @ 0.02 mug1tyr3J7JojVmdZHEn45hUvxW1GNRwsS" -interface eth0:2 -uiport 7778 -uibind 127.0.0.1 -passiveport 50500 -passivebind 192.168.1.45 -directport 50501 -directbind 192.168.1.45 -skipbootstrap 1 -localonly 1 -wanip 192.168.1.45 -uselocaltime 1


python3.3 -m "coinbend.main" -externalexchange 0 -erateinit BTC_USD_358.03,USD_AUD_1.2116072,LTC_BT0.00996000,DOGE_BTC_0.00000056 -clockskew -29.9615900039672851562500 -trade "buy 0.5 dogecoin/litecoin @ 0.02 n2k4uEfUoWQGTd7mV6ZJ8bqz67EQfAmZB6" 1 -interface eth0:3 -uiport 7779 -uibind 127.0.0.1 -passiveport 50502 -passivebind 192.168.1.46 -directport 50503 -directbind 192.168.1.46 -localonly 1 -addnode passive://192.168.1.45:50500/p2p -wanip 192.168.1.46 -uselocaltime 1
"""

from .globals import *
from .user_web_server import *
from .lib import *
from .trades import *
from .order_book import *
from .trade_type import *
from .nacl_crypt import *
from .contract_client import *
from .hybrid_protocol import *
from .hybrid_reply import *
from .coinlib import *
from .sock import *
import time
import os
import platform
import hashlib
import copy
from threading import Thread, Lock


def main():
    #Check we're not running as root.
    whoami = os.path.split(map_path("~"))[-1].lower()
    invalid_whoami = ["root", "admin", "administrator"]
    if whoami in invalid_whoami:
        print("Don't run this program as an administrator.")
        exit()

    #Protocol handlers.
    global trade_engine
    global coins
    global demo
    nacl_crypt = NaclCrypt()
    p2p_protocol = HybridProtocol(config, sys_clock, nacl_crypt, p2p_net, coins, e_exchange_rate, trade_engine)
    contract_client = ContractClient(p2p_protocol, config)
    direct_protocol = HybridProtocol(config, sys_clock, nacl_crypt, direct_net, coins, e_exchange_rate, trade_engine, contract_client)

    #Initialize software with one test trade.
    if args.trade != None:
        #Extract trade parts.
        trade_parts = re.findall("^(buy|sell)\s+([0-9]+(?:[.][0-9]+)?)\s+([a-zA-Z0-9]+)[/]([a-zA-Z0-9]+)\s+[@]\s+([0-9]+(?:[.][0-9]+)?)\s*([a-zA-Z0-9]+)?(?:\s+([a-zA-Z0-9]+)\s+([a-zA-Z0-9+//=]+)((?:\s+(?:[a-zA-Z0-9+//=]+)\s+(?:[a-zA-Z0-9+//=]+))+))?$", args.trade)
        if len(trade_parts):
            trade_parts = trade_parts[0]
            action, amount, base_currency, quote_currency, ppc = trade_parts[0:5]
            pair = [base_currency, quote_currency]

            if trade_parts[5] != "":
                recv_addr = trade_parts[5]
            else:
                recv_addr = None

            if trade_parts[6] != "":
                deposit_txid, ecdsa_encrypted_pub, owner_key_pairs = trade_parts[6:9]
            else:
                deposit_txid = None
                ecdsa_encrypted = None
                ecdsa_owner = None

            if deposit_txid != None:
                ecdsa_encrypted = ecdsa_encrypted_pub
                owner_key_pairs = list(filter(None, owner_key_pairs.split(" ")))
                ecdsa_owner = [
                    {
                        "pub": owner_key_pairs[0],
                        "priv": owner_key_pairs[1]
                    },
                    {
                        "pub": owner_key_pairs[2],
                        "priv": owner_key_pairs[3]
                    }
                ]

            #Open the trade.
            trade_engine.open_trade(action, amount, pair, ppc, recv_addr, deposit_txid, ecdsa_encrypted, ecdsa_owner)
        else:
            raise Exception("Invalid trade argument: " + args.trade)

    #Start UI web server.
    print("Attempting to start web server.")
    def start_ui_server(app, host, port, debug):
        run(app, host=host, port=port, debug=debug)
    ui_server_thread = Thread(target=start_ui_server, args=(app, ui_bind, ui_port, True))
    ui_server_thread.start()
    print("Web server started.")

    #Make data dirs if they don't exist yet.
    init_data_dirs(data_dir, backup_data_dir)

    #Main event loop.
    networks = {
        "p2p_net": p2p_net,
        "direct_net": direct_net
    }
    p2p_net.seen_messages = direct_net.seen_messages = seen_messages
    hybrid_replies = []
    while 1:
        #Send get_refund_sig when contract server indicates setup ready.
        for our_trade in trade_engine.trades:
            #Send open order to network.
            if our_trade.status == "green_address_deposit_confirm":
                if our_trade.actor == "seller":
                    #Generate open order message.
                    open_msg, order = p2p_protocol.new_open_order(our_trade, our_trade.recv_addr, our_trade.green_address)
                    our_trade.order_hash = order.order_hash
                    print("Order hash = " + str(our_trade.order_hash))

                    trade_engine.order_book.orders.append(order)
                    our_trade.update()

                    #Send open order message.
                    print(p2p_net.inbound + p2p_net.outbound)
                    print(type(open_msg))
                    record_msg_hash(open_msg)
                    print(open_msg)

                    #Rebroadcast every minute (up to 10 times.)
                    def status_builder():
                        def status_check(hybrid_reply):
                            #No p2p net connections.
                            if our_trade.dest_ip == "":
                                if not (len(p2p_net.inbound) + len(p2p_net.outbound)):
                                    return 0

                            elapsed = int(time.time() - hybrid_reply.last_run_time)
                            interval = min_retransmit_interval + (propagation_delay * 2)
                            if elapsed >= interval:
                                hybrid_reply.last_run_time = time.time()
                                return 1
                            else:
                                if our_trade.status == "microtransfer_complete":
                                    return -1
                                else:
                                    return 0

                        return status_check

                    #Route trade to single node.
                    if our_trade.dest_ip != "":
                        print("In direct seller open.")
                        print(our_trade.dest_ip)
                        dest_con = direct_net.con_by_ip(our_trade.dest_ip)
                        print(dest_con)
                        routes = [
                            dest_con,
                        ]
                        new_hybrid_reply = HybridReply([open_msg], "direct_net", "route", max_retransmissions)
                        new_hybrid_reply.add_routes(routes)
                    else:
                        new_hybrid_reply = HybridReply([open_msg], "p2p_net", "everyone", max_retransmissions)
                    new_hybrid_reply.set_status_checker(status_builder())
                    hybrid_replies.append(new_hybrid_reply)

                #Update status.
                our_trade.status = "open"
                
                #Skip checking match states.
                continue

            contract_factory = our_trade.contract_factory
            valid_get_refund_sig_states = [
                "pending_seller_get_refund_sig",
                "pending_buyer_get_refund_sig"
            ]
            valid_get_setup_tx_states = [
                "pending_seller_get_setup_tx",
                "pending_buyer_get_setup_tx"
            ]

            #Sanity checking.
            if contract_factory == None:
                continue

            #Check contract states.
            #Todo: some of these need to only initiate once.
            for contract_hash in list(contract_factory.contracts):
                contract = contract_factory.contracts[contract_hash]
                matched = contract.matched

                #Don't keep checking this if it hasn't changed.
                if matched.state == matched.checked_state:
                    """
                    You still have to wait for the buyer's setup TX to confirm so there is no point in spamming them endlessly with get refund requests because they reject it until their setup TX is confirmed.
                    """
                    if matched.state == "seller_sent_get_refund_sig":
                        elapsed = time.time() - matched.state_updated
                        if elapsed < 5:
                            continue
                        else:
                            matched.state_updated = time.time()
                    else:
                        continue
                else:
                    matched.checked_state = matched.state
                print(matched.state)

                #Get refund sig.
                if matched.state in valid_get_refund_sig_states:
                    print("Getting refund sig.")
                    setup_txid = contract_factory.setup["signed"]["txid"]
                    refund = contract_factory.contracts[contract_hash].build_refund_tx(setup_txid)
                    contract_factory.refund["tx_hex"] = refund["tx_hex"]
                    contract_factory.refund["txid"] = calculate_txid(refund["tx_hex"])
                    get_refund_sig_msg = direct_protocol.new_get_refund_sig(contract_hash, refund["tx_hex"], our_trade.green_address.ecdsa_1)
                    matched.con.send_line(get_refund_sig_msg)

                    if matched.state == "pending_seller_get_refund_sig":
                        matched.update_state("seller_sent_get_refund_sig")

                    if matched.state == "pending_buyer_get_refund_sig":
                        matched.update_state("buyer_sent_get_refund_sig")

                #Get setup TX.
                if matched.state in valid_get_setup_tx_states:
                    print("Getting setup tx.")
                    ecdsa_1 = contract_factory.green_address.ecdsa_1
                    setup_txid = contract_factory.setup_txids[contract_hash]
                    get_setup_tx_msg = direct_protocol.new_get_setup_tx(contract_hash, setup_txid, ecdsa_1)
                    matched.con.send_line(get_setup_tx_msg)

                    if matched.state == "pending_seller_get_setup_tx":
                        matched.update_state("seller_sent_get_setup_tx")

                    if matched.state == "pending_buyer_get_setup_tx":
                        matched.update_state("buyer_sent_get_setup_tx")

                #Initiate microtransfer.
                if matched.state == "seller_initiate_microtransfer":
                    print("Initiating microtransfer.")
                    our_setup_txid = contract_factory.setup["signed"]["txid"]
                    their_setup_hex = contract_factory.setups[contract_hash]["tx_hex"]
                    their_refund_hex = contract_factory.refunds[contract_hash]["tx_hex"]
                    ret = contract.adjust_refund_tx(our_setup_txid, their_setup_hex, their_refund_hex)
                    ecdsa_1 = contract_factory.green_address.ecdsa_1
                    if type(ret) == dict:
                        new_return_adjusted_refund_msg = direct_protocol.new_return_adjusted_refund(contract_hash, ret["tx_hex"], ret["first_sig"], ret["second_sig"], ecdsa_1)
                        if matched.update_state("seller_accept_microtransfer"):
                            matched.con.send_line(new_return_adjusted_refund_msg)

                #Broadcast final version.
                if matched.state == "pending_microtransfer_complete":
                    print("pending_microtransfer_confirm")
                    rpc = coins[our_trade.to_recv.currency]["rpc"]["sock"]
                    coinbend_contract = contract.details["our_download"]["tx_hex"]
                    txid = rpc.sendrawtransaction(coinbend_contract)
                    print(calculate_txid(coinbend_contract))
                    print(txid)
                    matched.update_state("pending_microtransfer_confirm")

                    def builder(contract_hash):
                        def callback(event, tx_hex, needle):
                            global trade_engine

                            #Update % matched in trade.
                            print("Contract hash = ")
                            print(contract_hash)
                            trade = trade_engine.find_trade(contract_hash)
                            trade.status = "microtransfer_complete"
                            trade.update(100)

                            #Update matched state.
                            print(matched.update_state("microtransfer_complete"))
                            find_microtransfer(contract_hash, trade_engine.trades).update("microtransfer_complete")
                            print("Microtransfer complete")
                            print("\a\a\a\a")

                        return callback

                    callbacks = {
                        "confirm": builder(contract_hash),
                        "mutate": builder(contract_hash)
                    }

                    needle = {
                        "type": "tx_hex",
                        "value": coinbend_contract
                    }

                    tx_monitor.add_watch(our_trade.to_recv.currency, needle, callbacks, "Microtransfer redeem TX.")

        #Process direct messages from other nodes.
        for con in direct_net:
            for msg in con:
                print("direct msg = ")
                print(msg)
                replies = direct_protocol.understand(msg, seen_messages, con)
                for reply in replies:
                    if type(reply) == str:
                        con.send_line(reply)

                    if type(reply) == HybridReply:
                        reply.source_con = con
                        hybrid_replies.append(reply)

        #Propogate messages from P2P network.
        for con in p2p_net:
            for msg in con:
                #Don't parse p2p_net replies when in demo mode.
                if demo:
                    continue

                print("p2p msg = ")
                print(msg)
                replies = p2p_protocol.understand(msg, seen_messages, con)
                for reply in replies:
                    if type(reply) == str:
                        p2p_net.broadcast(reply, con)

                    if type(reply) == HybridReply:
                        reply.source_con = con
                        hybrid_replies.append(reply)

        #Route hybrid replies.
        new_hybrid_replies = []
        for hybrid_reply in hybrid_replies:
            #Evaluable hybrid reply -- should this be sent, deleted, what?
            hybrid_reply_status = hybrid_reply.status_checker(hybrid_reply)

            #Success.
            if hybrid_reply_status == 1:
                pass

            #Not ready.
            if hybrid_reply_status == 0:
                new_hybrid_replies.append(hybrid_reply)
                continue

            #Remove!
            if hybrid_reply_status == -1:
                continue

            def route_hybrid_reply(hybrid_reply):
                #Check network.
                if hybrid_reply.network not in networks:
                    print("Invalid network.")
                    return

                #Generate dynamic message if needed.
                if callable(hybrid_reply.msg):
                    msg = hybrid_reply.msg()
                else:
                    msg = hybrid_reply.msg
                
                #Parse route.
                con = None
                if hybrid_reply.routes != []:
                    for route in hybrid_reply.routes:
                        if type(route) == Sock:
                            con = route
                        else:
                            node_type = route[0]
                            node_addr = route[1]
                            node_port = route[2]
                            if node_type != "passive" and node_type != "simultaneous":
                                print("Invalid node typeeee")
                                continue

                            #Connect route.
                            #Todo: only open new conncetion if it doesn't already exist.
                            con = networks[hybrid_reply.network].add_node(node_addr, node_port, node_type)
                            if con == None:
                                continue
                            else:
                                break

                #Route reply.
                if hybrid_reply.recipient == "route":
                    if con != None:
                        con.send_line(msg)
                        return

                #Broadcast.
                if hybrid_reply.recipient == "everyone":
                    networks[hybrid_reply.network].broadcast(msg)
                    return

                #Source.
                if hybrid_reply.recipient == "source":
                    if hybrid_reply.source_con != None:
                        hybrid_reply.source_con.send_line(msg)
                        return

                return

            #Multiple messages.
            if type(hybrid_reply.msg) == list:
                for hybrid_reply_msg in hybrid_reply.msg:
                    sub_hybrid_reply = hybrid_reply.copy()
                    sub_hybrid_reply.msg = hybrid_reply_msg
                    route_hybrid_reply(sub_hybrid_reply)
            else:
                #Single message.
                route_hybrid_reply(hybrid_reply)

            #Retransmit?
            if hybrid_reply.retransmit_interval != 0:
                new_hybrid_replies.append(hybrid_reply)
                if hybrid_reply.retransmit_interval:
                    hybrid_reply.retransmit_interval -= 1

        #Update hybrid replies.
        hybrid_replies = new_hybrid_replies

        #Process contract server replies.
        contract_client.process_replies()                

        #Check for new transactions.
        tx_monitor.check()

        #Avoid CPU DoS.
        time.sleep(0.01)





