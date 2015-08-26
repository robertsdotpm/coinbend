import threading
from .globals import *
from .database import *
from .currency_type import *
from .trades import *
from .order_book import *
from .trade_type import *
from .lib import *
import time
import datetime
import logging
import random
from colorama import Fore, Back, Style
import copy

class TradeEngine():
    def __init__(self, config, coins, tx_monitor, demo=0, trades=None, order_book=None, db=None):
        self.config = config
        self.coins = coins
        self.tx_monitor = tx_monitor
        self.demo = demo

        #Connect engine to database.
        if db != None:
            self.db = db
        else:
            self.db = Database()

        #Load our open orders.
        if trades == None:
            #Todo: renable this when DB is different for both sides
            #self.trades = Trades()
            self.trades = Trades([])
        else:
            self.trades = trades

        #Load network order book.
        if order_book == None:
            self.order_book = OrderBook()
        else:
            self.order_book = order_book

    def find_trade(self, contract_hash):
        if contract_hash == None:
            raise Exception("Invalid contract hash in find trade.")

        for our_trade in self.trades:
            for match_hash in list(our_trade.matches):
                matched = our_trade.matches[match_hash]
                if matched.contract_hash == contract_hash:
                    return our_trade

        return None

    def open_trade(self, action, amount, pair, ppc, recv_addr=None, deposit_txid=None, ecdsa_encrypted=None, ecdsa_owner=None, dest_ip="", src_ip=""):
        #Check same IP hasn't already submitted a trade.
        if self.demo:
            previous_day = int(time.time() - (24 * 60 * 60))
            found = 0
            with Transaction() as tx:
                sql = "SELECT * FROM `trade_orders` WHERE `src_ip`=? AND `created_at`>?"
                tx.execute(sql, (src_ip, previous_day))
                ret = tx.fetchall()
                if len(ret) >= 4:
                    found = 1

            if found:
                raise Exception("Demo mode is active so you can only submit four trades per 24 hours.")

        #Build trade object.
        trade = Trade(action, amount, pair, ppc, dest_ip=dest_ip, src_ip=src_ip)
        trade_fee = C(self.config["trade_fee"])
        our_trade_fee = trade.apply_trade_fee(trade_fee, optional=1)
        their_trade_fee = trade.apply_trade_fee(trade_fee, optional=1, toggle=1)
        trade.apply_trade_fee(trade_fee)

        """
        All outputs in the resulting setup TX need to be greater than the dust threshold otherwise the TX will never confirm. The trade fee in this sense is actually extremely important for allowing the micro-collateral through. 

        The code bellow ensures the trade size vs trade fee will result in all outputs larger than the dust threshold.
        """
        if our_trade_fee < self.coins[trade.to_send.currency]["dust_threshold"]:
            print(str(our_trade_fee))
            print(str(self.coins[trade.to_send.currency]["dust_threshold"]))
            raise Exception("The resulting trade fee for our trade is less than the dust threshold and can't be broadcast.")

        if our_trade_fee != self.coins[trade.to_send.currency]["dust_threshold"] and self.demo:
            raise Exception("Demo mode is active so the required send amount is limited to prevent abuse.")

        if their_trade_fee < self.coins[trade.to_recv.currency]["dust_threshold"]:
            print(str(their_trade_fee))
            print(str(self.coins[trade.to_recv.currency]["dust_threshold"]))
            raise Exception("The resulting trade fee for their side of the trade is less than the dust threshold and can't be broadcast.")

        if their_trade_fee != self.coins[trade.to_recv.currency]["dust_threshold"] and self.demo:
            raise Exception("Demo mode is active so the required receive amount is limited to prevent abuse.")

        if trade.to_send < self.coins[trade.to_send.currency]["dust_threshold"]:
            print(str(trade.to_send))
            print(str(self.coins[trade.to_send.currency]["dust_threshold"]))
            raise Exception("Sending amount for this trade is less than the dust threshold amount and can't be broadcast.")

        if trade.to_recv < self.coins[trade.to_recv.currency]["dust_threshold"]:
            print(str(trade.to_recv))
            print(str(self.coins[trade.to_recv.currency]["dust_threshold"]))
            raise Exception("Receiving amount for this trade is less than the dust threshold amount and can't be broadcast.")

        #Check balance is enough to cover trade.
        rpc = self.coins[trade.to_recv.currency]["rpc"]["sock"]
        balance = C(rpc.getbalance())
        if trade.to_send > balance:
            raise Exception("Insufficent balance to cover trade.")

        #Generate a receive address.
        if recv_addr == None:
            recv_addr = rpc.getnewaddress()
    
        #Set receive address.
        trade.recv_addr = recv_addr

        #Generate deposit tx_hex.
        deposit_tx_hex = trade.setup_green_address(self.config, self.coins, deposit_txid, ecdsa_encrypted, ecdsa_owner)
        if deposit_txid == None:
            trade.green_address.save()
        trade.save()

        """
        Make the trade available only when the deposit into the green address has been confirmed. If it isn't confirmed you're doing logic that will end up failing (plus its insecure.)
        """
        def callback(event, tx_hex, needle):
            print("\a")
            print("\a")
            print("Deposit tx confirmed.")

            #Update deposit_txid (in case of TX malleability.)
            txid = calculate_txid(tx_hex)
            trade.green_address.deposit_tx_hex = tx_hex
            trade.green_address.deposit_txid = txid
            trade.green_address.update()

            #Update status.
            trade.status = "green_address_deposit_confirm"
            trade.deposit_status = "confirm"
            trade.update()

            #Insert new trade.
            print("Insert trade status:")
            print(str(self.trades.new_trade(trade)))
            print(self.trades.trades)

        callbacks = {
            "confirm": callback,
            "mutate": callback,
            "fraud": callback
        }

        needle = {
            "type": "tx_hex",
            "value": deposit_tx_hex
        }

        unique_id = get_unique_id()
        watch_id = "green_address_deposit_" + unique_id
        self.tx_monitor.add_watch(trade.to_send.currency, needle, callbacks, "Green address deposit TX.", watch_id)

        return trade
        
    def close_trade(self, trade):
        if trade["status"] == "closed":
            return trade
    
        with Transaction(self.db) as tx:        
            #Get trade.
            if type(trade) == int:
                trade = self.get_trade(trade_id, tx.in_transaction, tx.db)
                if not trade:
                    raise Exception("Failed to get trade in close_trade.")
            
            #Close trade.
            sql = """UPDATE `trade_orders` SET `status`="closed" WHERE `id`=?;"""
            tx.execute(sql, (trade["id"],))
            
            #Apply trade fees.
            if trade["received"] > "0.1":
                trade["trade_fee"] = trade["received"] * str(self.config["trade_fee"])
                trade["received"] = trade["received"] - trade["trade_fee"]
            
            #Apply refund if needed.
            balance = Balance(trade["user_id"], tx.in_transaction, tx.db)
            if not balance.is_loaded:
                raise Exception("Unable to load balance in close_trade.")
            
            refund = trade["value"] - trade["sent"]
            if refund > "0.0":
                old_balance = balance.get(trade["send_currency"], tx.in_transaction, tx.db)
                if not old_balance:
                    raise Exception("Unable to get balance in close_trade")
                
                new_balance = old_balance + refund
                if not balance.set(
                trade["send_currency"],
                str(new_balance),
                tx.in_transaction,
                tx.db):
                    raise Exception("Unable to apply refund.")
            
            #Increase balance.
            new_balance = balance.get(trade["recv_currency"], tx.in_transaction, tx.db) + trade["received"]
            if not new_balance:
                raise Exception("Unable to get balance in close_trade.")
            
            if not balance.set(
            trade["recv_currency"],
            str(new_balance),
            tx.in_transaction,
            tx.db):
                raise Exception("Unable to increase balance in close trade.")
                
            trade["status"] = "closed"
            
        return trade


if __name__ == "__main__":
    #xx = TradeEngine()
    #print(x.new_trade("buy", ["btc", "ltc"], C(10, 3), C(2, 4)))
    #print(x.get_trade(1))
    #print(x.get_trades("litecoin_bitcoin"))

    """
    buy = Trade("buy", "10", ["bitcoin", "litecoin"], "0.5")
    sell = Trade("sell", "5", ["bitcoin", "litecoin"], "0.45")

    order_book = OrderBook()
    order_book.open_order("1", 4343244, sell, [], "x", "x", 10, "x")
    matches = order_book.find_matches(buy)
    print(matches)
    """

    """
    print(buy == sell)

    buy.matches["test"] = 4
    buy.matches["test2"] = 2
    for match in buy:
        print(match)


    print("------------")
    print(buy.pair)
    """

    """
    cp = CurrencyPair(["bitcoin", "litecoin"])
    print(cp[0])
    print(cp["base"])
    print(cp["base_currency"])
    print(cp[1])
    print(cp["quote"])
    print(cp["quote_currency"])
    print(str(cp))
    """


    trade_orders = TradeOrders()
    #trade_orders.open_trade(Trade("sell", "10", ["dogecoin", "bitcoin"], "0.44"))
    print(trade_orders.get_trades())
    


