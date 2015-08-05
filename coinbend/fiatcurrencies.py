"""
A list of traditional currencies or fiat-currencies.
"""

if __name__ != "__main__":
    # -*- coding: utf-8 -*-
    #Source: http://en.wikipedia.org/wiki/ISO_4217
    #td>([^<>]+?)</td>[\s\S]+?<td>[^<>]+?</td>[\s\S]+?<td>[^<>]+?
    #</td>[\s\S]+?<td[^=]+?title=\"([^\"]+?)\"
    fiatcurrencies = {
        "aed": {
            "name": "united arab emirates dirham"
        },
        "afn": {
            "name": "afghan afghani"
        },
        "all": {
            "name": "albanian lek"
        },
        "amd": {
            "name": "armenian dram"
        },
        "ang": {
            "name": "netherlands antillean guilder"
        },
        "aoa": {
            "name": "angolan kwanza"
        },
        "ars": {
            "name": "argentine peso"
        },
        "aud": {
            "name": "australian dollar"
        },
        "awg": {
            "name": "aruban florin"
        },
        "azn": {
            "name": "azerbaijani manat"
        },
        "bam": {
            "name": "bosnia and herzegovina convertible mark"
        },
        "bbd": {
            "name": "bangladeshi taka"
        },
        "bgn": {
            "name": "bulgarian lev"
        },
        "bhd": {
            "name": "bahraini dinar"
        },
        "bif": {
            "name": "burundian franc"
        },
        "bmd": {
            "name": "bermudian dollar"
        },
        "bnd": {
            "name": "brunei dollar"
        },
        "bob": {
            "name": "brazilian real"
        },
        "bsd": {
            "name": "bahamian dollar"
        },
        "btn": {
            "name": "bhutanese ngultrum"
        },
        "bwp": {
            "name": "botswana pula"
        },
        "byr": {
            "name": "belarusian ruble"
        },
        "bzd": {
            "name": "belize dollar"
        },
        "cad": {
            "name": "canadian dollar"
        },
        "cdf": {
            "name": "congolese franc"
        },
        "che": {
            "name": "wir bank"
        },
        "chf": {
            "name": "swiss franc"
        },
        "chw": {
            "name": "wir bank"
        },
        "clf": {
            "name": "unidad de fomento"
        },
        "clp": {
            "name": "chilean peso"
        },
        "cny": {
            "name": "renminbi"
        },
        "cop": {
            "name": "colombian peso"
        },
        "cou": {
            "name": "cuban convertible peso"
        },
        "cup": {
            "name": "cuban peso"
        },
        "cve": {
            "name": "czech koruna"
        },
        "djf": {
            "name": "djiboutian franc"
        },
        "dkk": {
            "name": "danish krone"
        },
        "dop": {
            "name": "dominican peso"
        },
        "dzd": {
            "name": "algerian dinar"
        },
        "egp": {
            "name": "egyptian pound"
        },
        "ern": {
            "name": "eritrean nakfa"
        },
        "etb": {
            "name": "ethiopian birr"
        },
        "eur": {
            "name": "euro"
        },
        "fjd": {
            "name": "falkland islands pound"
        },
        "gbp": {
            "name": "pound sterling"
        },
        "gel": {
            "name": "georgian lari"
        },
        "ghs": {
            "name": "gibraltar pound"
        },
        "gmd": {
            "name": "gambian dalasi"
        },
        "gnf": {
            "name": "guinean franc"
        },
        "gtq": {
            "name": "guatemalan quetzal"
        },
        "gyd": {
            "name": "guyanese dollar"
        },
        "hkd": {
            "name": "hong kong dollar"
        },
        "hnl": {
            "name": "honduran lempira"
        },
        "hrk": {
            "name": "croatian kuna"
        },
        "htg": {
            "name": "haitian gourde"
        },
        "huf": {
            "name": "hungarian forint"
        },
        "idr": {
            "name": "indonesian rupiah"
        },
        "ils": {
            "name": "israeli new shekel"
        },
        "inr": {
            "name": "indian rupee"
        },
        "iqd": {
            "name": "iraqi dinar"
        },
        "irr": {
            "name": "iranian rial"
        },
        "isk": {
            "name": "icelandic króna"
        },
        "jmd": {
            "name": "jamaican dollar"
        },
        "jod": {
            "name": "jordanian dinar"
        },
        "jpy": {
            "name": "japanese yen"
        },
        "kes": {
            "name": "kenyan shilling"
        },
        "kgs": {
            "name": "kyrgyzstani som"
        },
        "khr": {
            "name": "cambodian riel"
        },
        "kmf": {
            "name": "north korean won"
        },
        "krw": {
            "name": "south korean won"
        },
        "kwd": {
            "name": "kuwaiti dinar"
        },
        "kyd": {
            "name": "cayman islands dollar"
        },
        "kzt": {
            "name": "kazakhstani tenge"
        },
        "lak": {
            "name": "lao kip"
        },
        "lbp": {
            "name": "lebanese pound"
        },
        "lkr": {
            "name": "sri lankan rupee"
        },
        "lrd": {
            "name": "liberian dollar"
        },
        "lsl": {
            "name": "lesotho loti"
        },
        "ltl": {
            "name": "lithuanian litas"
        },
        "lyd": {
            "name": "libyan dinar"
        },
        "mad": {
            "name": "moroccan dirham"
        },
        "mdl": {
            "name": "moldovan leu"
        },
        "mga": {
            "name": "macedonian denar"
        },
        "mmk": {
            "name": "mongolian tögrög"
        },
        "mop": {
            "name": "macanese pataca"
        },
        "mro": {
            "name": "mauritian rupee"
        },
        "mvr": {
            "name": "maldivian rufiyaa"
        },
        "mwk": {
            "name": "malawian kwacha"
        },
        "mxn": {
            "name": "mexican peso"
        },
        "mxv": {
            "name": "mexican unidad de inversion"
        },
        "myr": {
            "name": "malaysian ringgit"
        },
        "mzn": {
            "name": "mozambican metical"
        },
        "nad": {
            "name": "namibian dollar"
        },
        "ngn": {
            "name": "nigerian naira"
        },
        "nio": {
            "name": "nicaraguan córdoba"
        },
        "nok": {
            "name": "norwegian krone"
        },
        "npr": {
            "name": "nepalese rupee"
        },
        "nzd": {
            "name": "new zealand dollar"
        },
        "omr": {
            "name": "omani rial"
        },
        "pab": {
            "name": "panamanian balboa"
        },
        "pen": {
            "name": "peruvian nuevo sol"
        },
        "pgk": {
            "name": "papua new guinean kina"
        },
        "php": {
            "name": "philippine peso"
        },
        "pkr": {
            "name": "pakistani rupee"
        },
        "pln": {
            "name": "polish złoty"
        },
        "pyg": {
            "name": "paraguayan guaraní"
        },
        "qar": {
            "name": "qatari riyal"
        },
        "ron": {
            "name": "serbian dinar"
        },
        "rub": {
            "name": "russian ruble"
        },
        "rwf": {
            "name": "rwandan franc"
        },
        "sar": {
            "name": "saudi riyal"
        },
        "sbd": {
            "name": "solomon islands dollar"
        },
        "scr": {
            "name": "sudanese pound"
        },
        "sek": {
            "name": "swedish krona"
        },
        "sgd": {
            "name": "singapore dollar"
        },
        "shp": {
            "name": "saint helena pound"
        },
        "sll": {
            "name": "sierra leonean leone"
        },
        "sos": {
            "name": "somali shilling"
        },
        "srd": {
            "name": "surinamese dollar"
        },
        "ssp": {
            "name": "south sudanese pound"
        },
        "std": {
            "name": "são tomé and príncipe dobra"
        },
        "syp": {
            "name": "syrian pound"
        },
        "szl": {
            "name": "swazi lilangeni"
        },
        "thb": {
            "name": "thai baht"
        },
        "tjs": {
            "name": "tajikistani somoni"
        },
        "tmt": {
            "name": "tunisian dinar"
        },
        "top": {
            "name": "tongan paʻanga"
        },
        "try": {
            "name": "turkish lira"
        },
        "ttd": {
            "name": "trinidad and tobago dollar"
        },
        "twd": {
            "name": "new taiwan dollar"
        },
        "tzs": {
            "name": "tanzanian shilling"
        },
        "uha": {
            "name": "ukrainian hryvnia"
        },
        "ugx": {
            "name": "ugandan shilling"
        },
        "usd": {
            "name": "united states dollar"
        },
        "usn": {
            "name": "uruguayan peso"
        },
        "uzs": {
            "name": "venezuelan bolívar"
        },
        "vnd": {
            "name": "vietnamese dong"
        },
        "vuv": {
            "name": "vanuatu vatu"
        },
        "wst": {
            "name": "central african cfa franc"
        },
        "xag": {
            "name": "silver"
        },
        "xau": {
            "name": "gold"
        },
        "xba": {
            "name": "east caribbean dollar"
        },
        "xdr": {
            "name": "special drawing rights"
        },
        "xfu": {
            "name": "uic franc"
        },
        "xof": {
            "name": "west african cfa franc"
        },
        "xpd": {
            "name": "palladium"
        },
        "xpf": {
            "name": "cfp franc"
        },
        "xpt": {
            "name": "platinum"
        },
        "xts": {
            "name": "yemeni rial"
        },
        "zar": {
            "name": "south african rand"
        },
        "zmw": {
            "name": "zambian kwacha"
        }
    }

    #Create lookup for name as a key too.
    reverse = {}
    for code in fiatcurrencies:
        reverse[fiatcurrencies[code]["name"]] = {"code": code}
    temp = reverse.copy()
    temp.update(fiatcurrencies)
    fiatcurrencies = temp

    #Capitalise.
    cap = {}
    for code in fiatcurrencies:
        cap[code.upper()] = fiatcurrencies[code]
    temp = cap.copy()
    temp.update(fiatcurrencies)
    fiatcurrencies = temp

    def get_fiatcurrencies():
        global fiatcurrencies
        return fiatcurrencies
