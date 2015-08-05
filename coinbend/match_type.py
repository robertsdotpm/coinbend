import time

class MatchType():
    def __init__(self, version, ntp, order_hash, match_hash, trade, base_usd_worth, quote_usd_worth, routes, green_address, address, ecdsa_1, ecdsa_2, sig_1, sig_2, nonce):
        self.match_hash = match_hash
        self.version = version
        self.ntp = ntp
        self.order_hash = order_hash
        self.trade = trade
        self.base_usd_worth = base_usd_worth
        self.quote_usd_worth = quote_usd_worth
        self.routes = routes
        self.green_address = green_address
        self.address = address
        self.ecdsa_1 = ecdsa_1
        self.ecdsa_2 = ecdsa_2
        self.sig_1 = sig_1
        self.sig_2 = sig_2
        self.nonce = nonce
        self.timestamp = time.time()

    def buy_sell(self, match_1, match_2):
        if match_1.trade.action == "buy":
            return [match_1, match_2]
        else:
            return [match_2, match_1]

if __name__ == "__main__":
    pass
