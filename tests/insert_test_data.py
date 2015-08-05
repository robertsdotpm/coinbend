#from unittest import TestCase

import coinbend.currency_type
import coinbend.database
import coinbend.trade_engine
import oursql
import random
from decimal import *
import datetime
import time
from colorama import Fore, Back, Style

class insert_test_data():
    def __init__(self):
        self.c = coinbend.CurrencyType()
        self.db = coinbend.Database()
        self.trade_engine = coinbend.TradeEngine(["btc", "aud"])
        self.trade_engine.start()
        self.users = \
        [
            {
                "username": "Laurence",
                "aud_balance": "2000000.4567",
                "btc_balance": "2000000.94300002300",
                "trades": [
                    {
                        "action": "buy",
                        "pair": ["btc", "aud"],
                        "amount": "10.00001234",
                        "ppc": "1001.23000004"
                    },
                    
                    {
                        "action": "sell",
                        "pair": ["btc", "aud"],
                        "amount": "200",
                        "ppc": "300.000012"
                    },
                    {
                        "action": "buy",
                        "pair": ["aud", "btc"],
                        "amount": "2000.00003",
                        "ppc": "0.0008"
                    }
                ]
            },
            {
                "username": "Holo",
                "aud_balance": "2000001.24234234000234",
                "btc_balance": "2000004.0000012340000",
                "trades": [
                    {
                        "action": "sell",
                        "pair": ["btc", "aud"],
                        "amount": "2000000.1",
                        "ppc": "921.1"
                    },
                    {
                        "action": "sell",
                        "pair": ["aud", "btc"],
                        "amount": "4000",
                        "ppc": "1010.10"
                    },
                    {
                        "action": "sell",
                        "pair": ["btc", "aud"],
                        "amount": "3",
                        "ppc": "1400"
                    }
                ]
            },
            {
                "username": "Chloe",
                "aud_balance": "20000.0",
                "btc_balance": "90000000.000001",
                "trades": [
                    {
                        "action": "buy",
                        "pair": ["btc", "aud"],
                        "amount": "100",
                        "ppc": "900"
                    },
                    {
                        "action": "sell",
                        "pair": ["btc", "aud"],
                        "amount": "50000",
                        "ppc": "950"
                    },
                    {
                        "action": "sell",
                        "pair": ["btc", "aud"],
                        "amount": "8000000",
                        "ppc": "50"
                    }
                ]
            },
            {
                "username": "Norah",
                "aud_balance": "20000.000004",
                "btc_balance": "100",
                "trades": [
                    {
                        "action": "buy",
                        "pair": ["btc", "aud"],
                        "amount": "5",
                        "ppc": "2000"
                    },
                    {
                        "action": "sell",
                        "pair": ["btc", "aud"],
                        "amount": "100",
                        "ppc": "500"
                    }
                ]
            }
        ]
        
    def insert_data(self):
        #Clear old test data.
        choice = input(Fore.RED + "Are you sure you want to delete all old database tables?\n" + Fore.RESET)
        if choice[0].lower() == "y":
            for table in self.db.schema["tables"]:
                sql = "TRUNCATE TABLE `%s`;" % (table)
                self.db.execute(sql)
            self.db.commit()

        if coinbend.config["debug"]:
            choice = "y"
        else:
            choice = input("Do you want to insert test data now?\n")
        if choice[0].lower() == "y":
            i = 0
            #Simulate prefered market.
            sql = "INSERT INTO `coinbend`.`ticker` (`id`, `base_currency`, `quote_currency`, `volume_whole`, `volume_dec`, `last_whole`, `last_dec`, `low_whole`, `low_dec`, `high_whole`, `high_dec`) VALUES (NULL, 'btc', 'aud', '123123', '23423', '0', '0', '0', '0', '0', '0');"
            self.db.execute(sql)
            self.db.commit()
            for user in self.users:
                #Insert users.
                try:
                    self.db.start_transaction()
                except:
                    pass
                sql = "INSERT INTO `users` (`username`) VALUES (?)"
                self.db.execute(sql, (user["username"],))
                user["id"] = self.db.cur.lastrowid

                #Insert auth details for test admin.
                if 0:
                    if user["username"] == "Laurence":
                        sql = "UPDATE `users` SET `email`='root@localhost.com', `salt`='x', `password`='5dbd172dfaa0e42158b036caf55430654b802da69f12741b496e1b70b3077bc5bfbf0231923b292c773fdfd697a09fa232ec3a6f5e847330db98723eee114ae5' WHERE `id`=" + str(user["id"])
                        self.db.execute(sql)

                #Create balances.
                aud_whole, aud_dec = self.c.number(user["aud_balance"])
                btc_whole, btc_dec = self.c.number(user["btc_balance"])
                sql = "INSERT INTO `balances` (`aud_whole`, `aud_dec`, `btc_whole`, `btc_dec`, `user_id`) VALUES (?, ?, ?, ?, ?)"
                self.db.execute(sql, (aud_whole, aud_dec, btc_whole, btc_dec, user["id"]))
                i += 1

                #Insert trade orders.
                for trade in user["trades"]:
                    print(Fore.BLUE + "Inserting new trade for " + user["username"])
                    #Error could be here - multiple threads sharing the same connection and executing the same queries.
                    #http://stackoverflow.com/questions/9173276/error-when-use-multithreading-and-mysqldb
                    print("Result: " + Fore.GREEN + self.trade_engine.new_trade(user["id"], trade["action"], trade["pair"], trade["amount"], trade["ppc"]) + Fore.RESET)
                    print("\n")
                    
                self.db.finish_transaction()
        
if __name__ == "__main__":
    x = insert_test_data()
    x.insert_data()
    #x.db.con.close()
    x.trade_engine.process_trades()
    while 1:
        time.sleep(3) #Allow time to match.
        x.trade_engine.process_trades()
    x.trade_engine.stop()
