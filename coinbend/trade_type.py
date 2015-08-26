
from .currency_type import *
from .database import *
from .ecdsa_crypt import *
from .green_address import *
from .microtransfer_contract import *
from .lib import *
from .address import *
import datetime
import json

def trade_from_row(row):
    action = row["action"]
    if "amount_whole" in row:
        amount = C(row["amount_whole"], row["amount_dec"])
    else:
        amount = C(row["amount"])
    pair = [row["base_currency"], row["quote_currency"]]
    if "ppc_whole" in row:
        ppc = C(row["ppc_whole"], row["ppc_dec"])
    else:
        ppc = C(row["ppc"])
    sent = C(0)
    recv = C(0)
    if "sent_whole" in row and "sent_dec" in row:
        sent = C(row["sent_whole"], row["sent_dec"])
    if "sent" in row:
        sent = C(row["sent"])
    if "recv_whole" in row and "recv_dec" in row:
        recv = C(row["recv_whole"], row["recv_dec"])
    if "recv" in row:
        recv = C(row["recv"])
    
    order_hash = ""
    if "order_hash" in row:
        order_hash = row["order_hash"]
    trade = Trade(action, amount, pair, ppc, order_hash, sent, recv)
    trade.id = row["id"]
    if "created_at" in row:
        trade.create_at = row["created_at"]
    if "updated_at" in row:
        trade.updated_at = row["updated_at"]
    
    return trade

def order_pair(pair):
    """
    Defines a standardised order for currency pairs so that
    a given pair has only one representation: e.g. btc/usd
    and not also usd/btc. Funtion works by sorting the
    currency codes by alphabetical order. This is necessary
    for more efficient matching of orders. 
    """
    if len(pair) != 2:
        raise Exception("Invalid currency pair.")

    #Swap currencies.
    return CurrencyPair(sorted(pair))
    

class CurrencyPair():
    def __init__(self, pair, set_codes=1):
        if type(pair) == str:
            pair = pair.split("/")
        self.base_currency = pair[0].lower()
        self.quote_currency = pair[1].lower()

        self.codes = {}
        if set_codes:
            #Currency code for base.
            code_list = []
            code = get_currency_code(self.base_currency, crypto=cryptocurrencies, fiat=fiatcurrencies)
            if code == None:
                code = ""
            code_list.append(code)

            #Currency code for quote.
            code = get_currency_code(self.quote_currency, crypto=cryptocurrencies, fiat=fiatcurrencies)
            if code == None:
                code = ""
            code_list.append(code)
            self.codes = CurrencyPair(code_list, 0)

    #Type conversation to str
    def __str__(self):
        return self.base_currency + "/" + self.quote_currency

    #Dict type.
    def __getitem__(self, key):
        valid_keys = [0, 1, "base", "quote", "base_currency", "quote_currency"]
        if key not in valid_keys:
            raise KeyError

        if key == 0:
            return self.base_currency

        if key == 1:
            return self.quote_currency

        if "base" in key:
            return self.base_currency

        if "quote" in key:
            return self.quote_currency

    #List type.
    def __len__(self):
        return 2

    def __iter__(self):
        return iter([self.base_currency, self.quote_currency])

    def __reversed__(self):
        return iter([self.quote_currency, self.base_currency])

    #Operator == 
    def __eq__(self, other):
        #Base currency.
        if self.base_currency != other.base_currency:
            return False

        #Quote currency.
        if self.quote_currency != other.quote_currency:
            return False

        return True

    #Operator !=
    def __ne__(self, other):
        if self.__eq__(other):
            return False
        else:
            return True

class Trade():
    def __init__(self, action, amount, pair, ppc, order_hash="", sent=0, recv=0, fees=0, dest_ip="", recv_addr="", status="pending_green_address_deposit", id=0, src_ip=""):
        self.action = action.lower()
        if self.action not in ["buy", "sell"]:
            raise Exception("Invalid action for trade.")

        self.pair = CurrencyPair(pair)
        self.amount = C(amount)
        self.ppc = C(ppc)
        self.order = None
        self.order_hash = order_hash
        self.sent = C(sent)
        self.recv = C(recv)
        self.updated_at = self.created_at = datetime.datetime.today()
        self.id = id
        self.type = "limit"
        self.status = status
        self.deposit_status = "pending"
        self.matches = {}
        self.green_address = None
        self.contract_factory = None
        self.fees = C(fees)
        self.dest_ip = dest_ip
        self.src_ip = src_ip
        self.open_msg = None
        if self.dest_ip != "":
            print(self.dest_ip)
            if not is_ip_valid(self.dest_ip):
                raise Exception("Invalid direct IP entered for trade.")

        self.recv_addr = recv_addr
        if self.recv_addr != "":
            if not deconstruct_address(self.recv_addr)["is_valid"]:
                raise Exception("Invalid recv address for trade.")

        #Make trade easier to process.
        self.analyze_trade()

    def update(self, complete=0):
        with Transaction() as tx:
            sql = "UPDATE `trade_orders` SET `order_hash`=?,`complete`=?,`deposit_status`=? WHERE `id`=?"
            tx.execute(sql, (self.order_hash, complete, self.deposit_status, self.id))

    def save(self):
        with Transaction() as tx:
            sql = "INSERT INTO `trade_orders` (`total_whole`, `total_dec`, `recv_whole`, `recv_dec`, `amount_whole`, `amount_dec`, `ppc_whole`, `ppc_dec`, `type`, `base_currency`, `quote_currency`, `created_at`, `updated_at`, `flipped`, `status`, `action`, `sent_whole`, `sent_dec`, `recv_addr`, `dest_ip`, `fees_whole`, `fees_dec`, `green_address_id`, `deposit_status`, `complete`, `src_ip`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

            created_at = updated_at = int(time.time())
            params = (\
                self.total["whole"],
                self.total["dec"],
                self.recv["whole"],
                self.recv["dec"],
                self.amount["whole"],
                self.amount["dec"],
                self.ppc["whole"],
                self.ppc["dec"],
                "limit",
                self.pair["base"],
                self.pair["quote"],
                created_at,
                updated_at,
                self.flipped,
                self.status,
                self.action,
                self.sent["whole"],
                self.sent["dec"],
                self.recv_addr,
                self.dest_ip,
                self.fees["whole"],
                self.fees["dec"],
                self.green_address.id,
                "pending",
                0,
                self.src_ip
            )

            tx.execute(sql, params)
            self.id = tx.db.cur.lastrowid

        return self.id

    #Setup green address + contract factory for trade.
    def setup_green_address(self, config, coins, deposit_txid=None, ecdsa_encrypted=None, ecdsa_owner=None):
        if ecdsa_encrypted == None:
            ecdsa_encrypted = ECDSACrypt(config["green_address_server"]["encrypted_key_pair"]["pub"])
        else:
            ecdsa_encrypted = ECDSACrypt(ecdsa_encrypted)

        if ecdsa_owner == None:
            ecdsa_owner = [ECDSACrypt(), ECDSACrypt()]
        else:
            ecdsa_owner = [
                ECDSACrypt(ecdsa_owner[0]["pub"], ecdsa_owner[0]["priv"]),
                ECDSACrypt(ecdsa_owner[1]["pub"], ecdsa_owner[1]["priv"])
            ]

        self.green_address = GreenAddress(self, ecdsa_owner[0], ecdsa_owner[1],ecdsa_encrypted, coins, config, deposit_txid=deposit_txid)
        self.contract_factory = MicrotransferFactory(self.green_address, coins, config)
        return self.green_address.deposit_tx_hex

    def analyze_trade(self):
        #Check action.
        valid_actions = ["buy", "sell"]
        if self.action not in valid_actions:
            raise Exception("Invalid action.")

        #Fixed precision.
        try:
            self.total = self.amount * self.ppc
        except:
            return 0

        self.flipped = 0
        trading_pair_flipped = CurrencyPair([self.pair[1], self.pair[0]])

        """
        Trading against a valid pair but reversed.
        Reconceptualize trade against valid pair.
        I.E - Flip everything except ppc.
        """
        if trading_pair_flipped == order_pair(trading_pair_flipped):
            self.flipped = 1
            if self.action == "buy":
                self.action = "sell"
            else:
                self.action = "buy"
            self.pair = trading_pair_flipped
            self.amount = self.total
            self.total = self.amount * self.ppc

        #Set currency for trade amounts.
        self.amount.currency = self.pair["base"]
        self.total.currency = self.pair["quote"]
        self.ppc.currency = self.pair["quote"]

        #Who are we in this trade?
        self.actor = self.action + "er"
        if self.actor == "buyer":
            self.audience = "seller"
        else:
            self.audience = "buyer"

        #Ok, but what are we doing?
        if self.action == "buy":
            self.to_send = self.total
            self.to_recv = self.amount
            self.remaining = self.amount - self.recv
            self.remaining.currency = self.to_recv.currency
        else:
            self.to_send = self.amount
            self.to_recv = self.total
            self.remaining = self.amount - self.sent
            self.remaining.currency = self.to_send.currency

        self.sent.currency = self.to_send.currency
        self.recv.currency = self.to_recv.currency

    def toggle_action(self):
        if self.action == "buy":
            self.action = "sell"
        else:
            self.action = "buy"

    def apply_trade_fee(self, trade_fee, optional=0, toggle=0):
        if toggle:
            self.toggle_action()

        if self.action == "buy":
            fee = self.total * trade_fee
        else:
            fee = self.amount * trade_fee

        if toggle:
            self.toggle_action()

        if not optional:
            self.apply_fee(fee)

        return fee

    def apply_fee(self, fee):
        if fee == C(0):
            return

        #Apply fees based on to_send.
        if self.action == "buy":
            if fee > self.total:
                raise Exception("Fee are too high.")
            self.total -= fee
            self.amount = C(self.total.as_decimal / self.ppc.as_decimal)
        else:
            if fee > self.amount:
                raise Exception("Fee are too high.")
            self.amount -= fee

        #Reset sent + recv amounts.
        self.sent = C(0)
        self.recv = C(0)

        #Update fees counter.
        self.fees += fee

        #Recompute current trade.
        self.analyze_trade()

    def remove_fees(self, fees=None):
        #Remove all.
        if fees == None:
            fees = self.fees
        if fees == C(0):
            return

        #Remove fees based on to_send.
        if self.action == "buy":
            self.total += fees
            self.amount = C(self.total.as_decimal / self.ppc.as_decimal)
        else:
            self.amount += fees

        #Reset sent + recv amounts.
        self.sent = C(0)
        self.recv = C(0)

        #Update fees counter.
        self.fees -= fees

        #Recompute current trade.
        self.analyze_trade()

    def copy(self):
        return Trade(copy.deepcopy(self.action), copy.deepcopy(self.amount), copy.deepcopy(self.pair), copy.deepcopy(self.ppc), copy.deepcopy(self.order_hash), copy.deepcopy(self.sent), copy.deepcopy(self.recv), copy.deepcopy(self.fees), copy.deepcopy(self.dest_ip), copy.deepcopy(self.recv_addr), copy.deepcopy(self.status), copy.deepcopy(self.id))

    def to_dict(self):
        json_out = {
            "id": self.id,
            "type": self.type,
            "action": self.action,
            "pair": [self.pair["base"], self.pair["quote"]],
            "codes": [self.pair.codes["base"], self.pair.codes["quote"]],
            "amount": str(self.amount),
            "ppc": str(self.ppc),
            "total": str(self.total),
            "sent": str(self.sent),
            "recv": str(self.recv),
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "flipped": self.flipped
        }

    #Return trades in order with buy then sell.
    def buy_sell(self, trade_a, trade_b):
        if trade_a.actor == "buyer":
            return [trade_a, trade_b]
        else:
            return [trade_b, trade_a]

    #Type conversation to str
    def __str__(self):
        if self.action == "buy":
            op = "<="
        else:
            op = ">="
        ret = "\r\nTrade: %s %s %s %s %s per coin" % (str(self.action), str(self.amount), str(self.pair), str(op), str(self.ppc))
        ret += "\r\nSent: %s / %s (a possible)" % (str(self.sent), str(self.to_send))
        ret += "\r\nRecv: %s / %s" % (str(self.recv), str(self.to_recv))
        ret += "\r\nRemaining: %s" % (str(self.remaining))
        ret += "\r\nStatus: %s" % (str(self.status))
        return ret

    #Operator == if trades are == then they can be matched.
    def __eq__(self, other):
        #Types.
        if type(other) != Trade:
            return False

        #Check trades are open.
        if self.status != "open" or other.status != "open":
            return

        #Pairs.
        if self.pair != other.pair:
            return False

        #Actions.
        if self.action == other.action:
            return False

        #PPC.
        buy, sell = self.buy_sell(self, other)
        if buy.ppc < sell.ppc:
            return False

        #Disable partial matching.
        if buy.amount != sell.amount:
            return False

        #Remaining.
        if not self.remaining or not other.remaining:
            return False
                         
        return True

    #Matches two trades.
    def __truediv__(self, other):
        #Which is buy, which is sell?
        buy, sell = self.buy_sell(self, other)

        #Order status vars.
        close_buy = 0
        close_sell = 0
        old_self = self.copy()
        old_other = other.copy()
        
        #Sell trade partially fills buy trade.
        if buy.remaining > sell.remaining:
            change = sell.remaining
            close_sell = 1
            
        #Buy trade partially fills sell trade.
        if buy.remaining < sell.remaining:
            change = buy.remaining
            close_buy = 1
            
        #Both trades fully fill each other.
        if buy.remaining == sell.remaining:
            change = buy.remaining
            close_buy = 1
            close_sell = 1

        """
        Notes:
        * Every trade has two important values: sent and recv.
        * Sent is how much value has been transferred so far as part
        of trying to fulfil the trade.
        * Recv is how much value has been received so far as
        part of trying to fulfil the trade.
        * It may take multiple matches to execute just to complete
        a single buy or sell trade.
        * An order is considered matched when self.to_recv == self.recv.
        * The price that is sent as part of a buy may not reflect
        the total value of the trade based on amount * ppc. This
        is because the trade may have been matched with sellers
        selling for less than the buy amount.
            * This is important to remember since a refund may
            be required when closing a buy trade.
            * Sell trades may also require a refund if the trade is
            closed before it has been fully matched. Likewise for
            buy trades.
        * Received should theoretically never be more than
        what is specified for the trade (but it may be less if it can't
        be matched.)
        """

        #Update buy_trade.
        trade_value = change * sell.ppc
        buy.recv = buy.recv + change
        buy.sent = buy.sent + trade_value
        buy.remaining = buy.amount - buy.recv

        #Update sell_trade.
        sell.sent = sell.sent + change
        sell.recv = sell.recv + trade_value
        sell.remaining = sell.amount - sell.sent

        #Close buy trade.
        if close_buy:
            buy.status = "closed"

        #Close sell trade.
        if close_sell:
            sell.status = "closed"

        #Return difference.
        ret = self - old_self
        ret.ppc = sell.ppc
        return ret

    #Unmatch two trades.
    def __mul__(self, other):
        #Which is buy, which is sell?
        buy, sell = self.buy_sell(self, other)

        #Order status vars.
        open_buy = 0
        open_sell = 0
        old_self = self.copy()
        old_other = other.copy()

        #Sell trade partially filled buy trade.
        if buy.sent > sell.recv:
            buy.sent = buy.sent - sell.recv
            buy.recv = buy.recv - sell.sent
            sell.sent = C("0")
            sell.recv = C("0")
            open_sell = 1

        #Buy trade partially filled sell trade.
        if buy.sent < sell.recv:
            sell.sent = sell.sent - buy.recv
            sell.recv = sell.recv - buy.sent
            buy.sent = C("0")
            buy.recv = C("0")
            open_buy = 1

        #Both trades fully filled each other.
        if buy.sent == sell.recv:
            buy.sent = C("0")
            buy.recv = C("0")
            sell.sent = C("0")
            sell.recv = C("0")
            open_buy = 1
            open_sell = 1

        #Calculate remaining.
        buy.remaining = buy.amount - buy.recv
        sell.remaining = sell.amount - sell.sent

        #Open buy trade.
        if open_buy:
            buy.status = "open"

        #Open sell trade.
        if open_sell:
            sell.status = "open"

        #Return difference.
        ret = old_self - self
        return ret

    #Operator !=
    def __ne__(self, other):
        if self.__eq__(other):
            return False
        else:
            return True

    #Operator > cmp ppc
    def __gt__(self, other):
        return bool(self.ppc > other.ppc)

    #Operator >= cmp ppc
    def __ge__(self, other):
        return bool(self.ppc >= other.ppc)

    #Operator < cmp ppc
    def __lt__(self, other):
        return bool(self.ppc < other.ppc)

    #Operator <= cmp ppc
    def __le__(self, other):
        return bool(self.ppc <= other.ppc)

    """
    Returns the difference between two version of the SAME trade as
    a new trade which is useful for seeing the match amount.

    Self needs to be greater than other for this to work. I.e. the
    version before matching occurs.
    """
    def __sub__(self, other):
        if self.action == "buy":
            amount = self.recv - other.recv
        else:
            amount = self.sent - other.sent

        return Trade(self.action, amount, self.pair, self.ppc, self.order_hash)

    def __len__(self):
        return len(self.matches)

    def __iter__(self):
        return iter(list(self.matches))

    def __reversed__(self):
        return self.__iter__()

if __name__ == "__main__":
    trade_a = Trade("sell", "2.5", ["bitcoin", "litecoin"], "0.004")
    trade_b = Trade("buy", "0.5", ["bitcoin", "litecoin"], "0.005")
    trade_c = Trade("buy", "1", ["bitcoin", "litecoin"], "0.006")

    trade_fee = C(config["trade_fee"])
    fee = trade_a.amount * trade_fee
    print(fee)
    print(trade_a)
    trade_a.apply_fee(fee)
    print(trade_a)
    trade_a.remove_fees(fee)
    print(trade_a)
    exit()

    #Match.
    trade_a / trade_b
    trade_a / trade_c
    
    #print(trade_a)
    #print(trade_b)
    #print(trade_c)
    #print("----------------------------------------")

    #Unmatch
    trade_a * trade_c
    trade_a * trade_b

    #print(trade_a)
    #print(trade_b)
    #print(trade_c)

    
    trade_1 = Trade("sell", "10", ["bitcoin", "litecoin"], "0.0000000000000005")
    trade_2 = Trade("buy", "1", ["bitcoin", "litecoin"], "0.0000000000000006")
    trade_3 = trade_2 / trade_1
    print(str(trade_3))



