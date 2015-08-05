"""
A list of cryptocurrencies accessible by either name or
currency code.
"""

if __name__ != "__main__":
    # -*- coding: utf-8 -*-
    #Source: http://coinmarketcap.com/all.html
    #currency-name[\s\S]+?>([^<>]+?)</a>[\s\S]+?class="
    #price"[\s\S]+?[^<>]+?</a></td>[\s\S]+?([^<>]+?)</a></td>
    cryptocurrencies = {
        "btc": {
            "name": "bitcoin"
        },
        "xrp": {
            "name": "ripple"
        },
        "ltc": {
            "name": "litecoin"
        },
        "aur": {
            "name": "auroracoin"
        },
        "ppc": {
            "name": "peercoin"
        },
        "doge": {
            "name": "dogecoin"
        },
        "nxt": {
            "name": "nxt"
        },
        "msc": {
            "name": "mastercoin"
        },
        "nmc": {
            "name": "namecoin"
        },
        "pts": {
            "name": "bitshares-pts"
        },
        "xcp": {
            "name": "counterparty"
        },
        "qrk": {
            "name": "quark"
        },
        "ftc": {
            "name": "feathercoin"
        },
        "vtc": {
            "name": "vertcoin"
        },
        "xpm": {
            "name": "primecoin"
        },
        "nvc": {
            "name": "novacoin"
        },
        "spa": {
            "name": "spaincoin"
        },
        "ifc": {
            "name": "infinitecoin"
        },
        "mec": {
            "name": "megacoin"
        },
        "max": {
            "name": "maxcoin"
        },
        "drk": {
            "name": "darkcoin"
        },
        "ybc": {
            "name": "ybcoin"
        },
        "wdc": {
            "name": "worldcoin"
        },
        "bc": {
            "name": "blackcoin"
        },
        "air": {
            "name": "aircoin"
        },
        "dvc": {
            "name": "devcoin"
        },
        "mint": {
            "name": "mintcoin"
        },
        "tix": {
            "name": "tickets"
        },
        "utc": {
            "name": "ultracoin"
        },
        "anc": {
            "name": "anoncoin"
        },
        "clr": {
            "name": "copperlark"
        },
        "btcs": {
            "name": "bitcoin scrypt"
        },
        "zet": {
            "name": "zetacoin"
        },
        "frc": {
            "name": "freicoin"
        },
        "ixc": {
            "name": "ixcoin"
        },
        "trc": {
            "name": "terracoin"
        },
        "dgc": {
            "name": "digitalcoin"
        },
        "prt": {
            "name": "particle"
        },
        "apc": {
            "name": "applecoin"
        },
        "rdd": {
            "name": "reddcoin"
        },
        "uno": {
            "name": "unobtanium"
        },
        "tips": {
            "name": "fedoracoin"
        },
        "cach": {
            "name": "cachecoin"
        },
        "pot": {
            "name": "potcoin"
        },
        "mona": {
            "name": "monacoin"
        },
        "bil": {
            "name": "billioncoin"
        },
        "mnc": {
            "name": "mincoin"
        },
        "unc": {
            "name": "unioncoin"
        },
        "mzc": {
            "name": "mazacoin"
        },
        "net": {
            "name": "netcoin"
        },
        "gld": {
            "name": "goldcoin"
        },
        "cgb": {
            "name": "cryptogenic bullion"
        },
        "huc": {
            "name": "huntercoin"
        },
        "tag": {
            "name": "tagcoin"
        },
        "zeit": {
            "name": "zeitcoin"
        },
        "src": {
            "name": "securecoin"
        },
        "ptc": {
            "name": "pesetacoin"
        },
        "ecc": {
            "name": "eccoin"
        },
        "col": {
            "name": "colossuscoin"
        },
        "mmc": {
            "name": "memorycoin"
        },
        "meow": {
            "name": "kittehcoin"
        },
        "sxc": {
            "name": "sexcoin"
        },
        "hbn": {
            "name": "hobonickels"
        },
        "hvc": {
            "name": "heavycoin"
        },
        "karm": {
            "name": "karmacoin"
        },
        "dgb": {
            "name": "digibyte"
        },
        "red": {
            "name": "redcoin"
        },
        "flt": {
            "name": "fluttercoin"
        },
        "cat": {
            "name": "catcoin"
        },
        "c2": {
            "name": "coin2"
        },
        "kdc": {
            "name": "klondikecoin"
        },
        "bqc": {
            "name": "bbqcoin"
        },
        "yac": {
            "name": "yacoin"
        },
        "lot": {
            "name": "lottocoin"
        },
        "gpuc": {
            "name": "gpucoin"
        },
        "myrc": {
            "name": "myriadcoin"
        },
        "moon": {
            "name": "mooncoin"
        },
        "ric": {
            "name": "riecoin"
        },
        "mrc": {
            "name": "microcoin"
        },
        "eac": {
            "name": "earthcoin"
        },
        "flo": {
            "name": "florincoin"
        },
        "topc": {
            "name": "topcoin"
        },
        "flap": {
            "name": "flappycoin"
        },
        "usde": {
            "name": "usde"
        },
        "lky": {
            "name": "luckycoin"
        },
        "42": {
            "name": "42 coin"
        },
        "q2c": {
            "name": "qubitcoin"
        },
        "sat": {
            "name": "saturncoin"
        },
        "leaf": {
            "name": "leafcoin"
        },
        "emc2": {
            "name": "einsteinium"
        },
        "exe": {
            "name": "execoin"
        },
        "mts": {
            "name": "metiscoin"
        },
        "fst": {
            "name": "fastcoin"
        },
        "phs": {
            "name": "philosopher stones"
        },
        "mrs": {
            "name": "marscoin"
        },
        "glb": {
            "name": "globe"
        },
        "dtc": {
            "name": "datacoin"
        },
        "btg": {
            "name": "bitgem"
        },
        "bte": {
            "name": "bytecoin"
        },
        "frk": {
            "name": "franko"
        },
        "elc": {
            "name": "elacoin"
        },
        "qqc": {
            "name": "qqcoin"
        },
        "krn": {
            "name": "ekrona"
        },
        "tak": {
            "name": "takcoin"
        },
        "glc": {
            "name": "globalcoin"
        },
        "dope": {
            "name": "dopecoin"
        },
        "dem": {
            "name": "deutsche emark"
        },
        "888": {
            "name": "octocoin"
        },
        "nyan": {
            "name": "nyancoin"
        },
        "bat": {
            "name": "batcoin"
        },
        "ebt": {
            "name": "ebtcoin"
        },
        "emo": {
            "name": "emoticoin"
        },
        "bet": {
            "name": "betacoin"
        },
        "csc": {
            "name": "casinocoin"
        },
        "smc": {
            "name": "smartcoin"
        },
        "pnd": {
            "name": "pandacoin"
        },
        "10-5": {
            "name": "tenfivecoin"
        },
        "bcx": {
            "name": "battlecoin"
        },
        "note": {
            "name": "dnotes"
        },
        "arg": {
            "name": "argentum"
        },
        "sbc": {
            "name": "stablecoin"
        },
        "ztc": {
            "name": "zenithcoin"
        },
        "rpc": {
            "name": "ronpaulcoin"
        },
        "zed": {
            "name": "zedcoin"
        },
        "ani": {
            "name": "animecoin"
        },
        "asr": {
            "name": "astrocoin"
        },
        "ruby": {
            "name": "rubycoin"
        },
        "asc": {
            "name": "asiccoin"
        }
    }

    #Create lookup for name as a key too.
    reverse = {}
    for code in cryptocurrencies:
        reverse[cryptocurrencies[code]["name"]] = {"code": code}
    temp = reverse.copy()
    temp.update(cryptocurrencies)
    cryptocurrencies = temp

    #Capitalise.
    cap = {}
    for code in cryptocurrencies:
        cap[code.upper()] = cryptocurrencies[code]
    temp = cap.copy()
    temp.update(cryptocurrencies)
    cryptocurrencies = temp

    def get_cryptocurrencies():
        global cryptocurrencies
        return cryptocurrencies
