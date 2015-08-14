from .database import *
from .trade_type import *
import datetime

#Our trades.
class Trades():
    def __init__(self, trades=None):
        #Manually overwrite trades.
        if trades != None:
            self.trades = trades
        else:
            self.trades = self.get_trades()

    def new_trade(self, trade):
        self.trades.insert(0, trade)
        return trade.id

    def get_trades(self, specifier=None):
        ret = 0
        trades = []
        with Transaction() as tx:
            if type(specifier) == str:
                if specifier.isdigit():
                    sql = "SELECT * FROM `trade_orders` WHERE `id`=? ORDER BY created_at DESC;"
                    tx.execute(sql, (specifier,))
                    return [trade_from_row(tx.fetchall()[0])]
                else:
                    specifier = specifier.lower()
                    pair = CurrencyPair(specifier.split("_"))
                    ordered_pair = order_pair(pair)
                    if pair != ordered_pair:
                        trades = self.get_trades(ordered_pair)
                    sql = "SELECT * FROM `trade_orders` WHERE `base_currency`=? AND `quote_currency`=? ORDER BY created_at DESC;"
                    tx.execute(sql, (pair[0], pair[1]))
            else:
                sql = "SELECT * FROM `trade_orders`;"
                tx.execute(sql)
            rows = tx.fetchall()
            for row in rows:
                trades.append(trade_from_row(row))
            ret = 1

        return trades
        
    def get_trade(self, trade_id):
        """
        Load a trade from the database by its ID.
        """
        ret = 0
        with Transaction() as tx:
            sql = "SELECT * FROM `trade_orders` WHERE `id`=?;"
            tx.execute(sql, (trade_id,))
            row = tx.fetchall()[0]
            ret = trade_from_row(row)
            
        return ret

    def __len__(self):
        return len(self.trades)

    def __iter__(self):
        return iter(list(self.trades))

    def __reversed__(self):
        return self.__iter__()

