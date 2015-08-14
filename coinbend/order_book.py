from .database import *
from .ecdsa_crypt import *
from .trade_type import *
from .order_type import *
from .currency_type import *
from .green_address import *

#Orders for the network.
class OrderBook():
    def __init__(self, orders=[]):
        self.orders = orders

    def get_order(self, order_hash):
        #Use manually loaded orders for the search.
        if len(self.orders):
            for order in self.orders:
                if order.order_hash == order_hash:
                    return order

        #Use database for search.
        with Transaction() as tx:
            #Load routes.
            sql = "SELECT * FROM `order_routes` WHERE `order_hash`=?;"
            tx.execute(sql, (order_hash,))
            rows = tx.fetchall()
            if not len(rows):
                return None

            #Parse routes.
            routes = []
            for row in rows:
                route = [row["type"], row["ip"], row["port"], row["relay_addr"], row["relay_port"]]
                routes.append(route)

            #Load order.
            sql = "SELECT * FROM `order_book` WHERE `order_hash`=?;"
            tx.execute(sql, (order_hash,))
            rows = tx.fetchall()
            if not len(rows):
                return None

            #Parse trade.
            row = rows[0]
            trade = Trade(row["action"], C(row["amount_whole"], row["amount_dec"]), [row["base_currency"], row["quote_currency"]], C(row["ppc_whole"], row["ppc_dec"]), row["order_hash"])

            #Parse key pairs.
            ecdsa_1 = ECDSACrypt(row["public_key_1"])
            ecdsa_1.load_db_private_key()
            ecdsa_2 = ECDSACrypt(row["public_key_2"])
            ecdsa_2.load_db_private_key()

            #Return order type.
            #Todo: store sig 2 here instead of copying the same one
            green_address = None
            return OrderType(row["order_hash"], int(row["version"]), int(row["ntp"]), trade, routes, green_address, row["address"], ecdsa_1, ecdsa_2, row["signature"], row["signature"], row["nonce"])

    def open_order(self, version, ntp, trade, routes, address, ecdsa_1, ecdsa_2, sig, nonce, order_hash):
        #Only store orders that don't already exist.
        with Transaction() as tx:
            sql = "SELECT * FROM `order_book` WHERE `order_hash`=?;"
            tx.execute(sql, (order_hash,))
            row = tx.fetchall()
            if len(row):
                return row[0]["id"]

        #Store order in order book.
        with Transaction() as tx:
            sql = "INSERT INTO `order_book` (`version`, `ntp`, `action`, `base_currency`, `quote_currency`, `amount_whole`, `amount_dec`, `ppc_whole`, `ppc_dec`, `address`, `public_key_1`, `public_key_2`, `signature`, `nonce`, `order_hash`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
            tx.execute(sql, (version, int(ntp), trade.action, trade.pair["base"], trade.pair["quote"], trade.amount["whole"], trade.amount["dec"], trade.ppc["whole"], trade.ppc["dec"], address, ecdsa_1.get_public_key(), ecdsa_2.get_public_key(), sig, nonce, order_hash))
            order_id = tx.fetchall()

            for route in routes:
                sql = "INSERT INTO `order_routes` (`type`, `ip`, `port`, `relay_addr`, `relay_port`, `order_hash`) VALUES (?, ?, ?, ?, ?, ?);"
                tx.execute(sql, (route[0], route[1], route[2], route[3], route[4], order_hash))

            #Store key pairs if we know it.
            if ecdsa_1.private_key != None:
                sql = "INSERT INTO `ecdsa_pairs` (`public_key`, `private_key`) VALUES (?, ?)"
                tx.execute(sql, (ecdsa_1.get_public_key(), ecdsa_1.get_private_key()))
            if ecdsa_2.private_key != None:
                sql = "INSERT INTO `ecdsa_pairs` (`public_key`, `private_key`) VALUES (?, ?)"
                tx.execute(sql, (ecdsa_2.get_public_key(), ecdsa_2.get_private_key()))

            return order_id

        return 0

    def find_matches(self, trade):
        if trade.action == "buy":
            ppc_op = "<="
            action = "sell"
        else:
            ppc_op = ">="
            action = "buy"

        rows = []
        with Transaction() as tx:
            sql = "SELECT * FROM `order_book` WHERE `base_currency`=? AND `quote_currency`=? AND `ppc_whole` %s ? AND `action`=? ORDER BY `ntp` DESC LIMIT 10000;" % (ppc_op)
            tx.execute(sql, (trade.pair["base"], trade.pair["quote"], trade.ppc["whole"], action))
            rows = tx.fetchall()

        matches = []
        for row in rows:
            match = trade_from_row(row)

            """
            The SELECT only checks the whole number portion
            so trades are compared again for final compatiability.
            """
            if trade == match:
                matches.append(match)

        return matches

if __name__ == "__main__":
    x = OrderBook()
    order = x.get_order("0e2a5ab8cae6a7dbdd59388a000e6229ed1ee521729c7087a291b6b53cb01a10")
    print(order.routes)

    
