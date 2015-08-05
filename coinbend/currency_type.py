"""
The purpose of this module is to provide high precision calculations
when dealing with decimal numbers. It avoids the inaccuracy and
danger of using floating point or decimal numbers for financial
calculations by storing decimal numbers as integers. This is
accomplished by splitting the number into two Bigint 64 (8 byte unsigned)
numbers - one for the whole portion, the other for the decimal, which
correspond to the equivalent MySQL type (Bigint x 2) and makes packing
and unpacking data from the DB easy.

The advantage of two separate fields instead of one is the increased
precision for the decimal component: 16 digits instead of around 8.
This is useful when dealing with incredibly small numbers such as
what might occur when comparing new currencies against Bitcoin.
It also allows the system to avoid rounding and truncation of
value which means precise financial records can be maintained.
The only exception to this rule is with multiplication. When
multiplying two numbers whose number of decimal places combined
is greater than 16 - truncation occurs. Currently the only time
this happens is when working out fees but the loss isn't anything
to lose sleep over.

This module does not currently support negative numbers and an error
is raised if they occur. This precaution helps prevent overflows that
could lead to crediting accounts with absurd amounts of money.
Theoretically negative numbers could be supported by inverting
the order of the operands when a negative number error occurs.

I also want to add that division isn't supported, but the library
allows a number to be multiplied by a decimal.

Examples:
c = coinbend.C()
c.math("10.11", "11", "+")
[22, 11] #Result.

c.math(2, [10, 22], "*")
[20, 44]

c.math(Decimal("5.431"), 1.430, "-")
Waring: float passed. Value may be imprecise.
[4, 10000000000000]

c.math("1.0023", 4, "<")
1

c.math("1.0023", 4, ">")
0

#Divide by 2:
c.math("1.0302", "0.5", "*")
[0, 5151000000000000]

#Negative numbers:
def handle_negative(x, y, op):
    c = coinbend.C()
    p = "pos"
    try:
        r = c.math(x, y, op)
    except Exception, e:
        if "negative" in str(e):
            x, y = y, x
            r = c.math(x, y, op)
            p = "neg"
        else:
            raise Exception
    return [r, p]

handle_negative("5", "10", "-")
^ Something like that.

Valid operators include: +, -, *, >, <, >=, <=, ==, !=.
Success return values depend on function.
All functions throw exceptions on failure.

(In order to avoid decimal overflows the number of decimal
places in two numbers being multiplied must not exceed a total of 16.)
"""

import re
import random
import decimal
import copy
from .fiatcurrencies import *
from .cryptocurrencies import *

def add_currency_codes(rows):
    global cryptocurrencies
    global fiatcurrencies
    for row in rows:
        pair = [row["base_currency"], row["quote_currency"]]
        codes = ["", ""]
        for stuff in [[0, pair[0]], [1, pair[1]]]:
            index, currency = stuff
            if currency in cryptocurrencies:
                codes[index] = cryptocurrencies[currency]["code"]
                continue

            if currency in fiatcurrencies:
                codes[index] = fiatcurrencies[currency]["code"]
                continue

        row["pair"] = pair
        row["codes"] = codes

    return rows

def combine_number_parts(rows, f=str):
    pretty_rows = []
    for row in rows:
        pretty_row = {}
        sub_keys = []
        for key in list(row):
            #Convert whole, dec format to str.
            done = 0
            for partial in ["whole", "dec"]:
                if partial in key:
                    sub_key, temp = re.findall("^(.+?)_(whole|dec)$", key)[0]
                    if sub_key not in sub_keys:
                        whole = int(row[sub_key + "_whole"])
                        dec = int(row[sub_key + "_dec"])
                        n = C(whole, dec)
                        if f == str:
                            pretty_row[sub_key] = str(n)
                        else:
                            pretty_row[sub_key] = n

                        sub_keys.append(sub_key)

                    done = 1
                    break

            #Partial found -- nothing left to do.
            if done:
                continue
            else:
                pretty_row[key] = row[key]

        pretty_rows.append(pretty_row)

    return pretty_rows

def decimal_wrapper(decimal_obj):
    def closure(value):
        if type(value) == C:
            value = str(value)

        return decimal_obj(value)

    return closure

decimal_type = copy.deepcopy(decimal.Decimal)

class C:
    def __init__(self, whole_or_str=None, dec=None, limit_precision=8):
        self.valid_keys = ["whole", "dec", "int", 0, 1, 2]
        self.whole_no_limit = 18446744073709551610 #~max bigint size
        self.precision = 16 #16 decimal places (physical storage limit)
        self.dec_no_limit = int("9" * self.precision) #16 point precision
        self.limit_precision = limit_precision #Truncate dec to this
        self.whole = self.dec = 0
        self.as_str = "0.0"
        self.as_decimal = decimal.Decimal("0.0")
        self.currency = None
        
        if dec != None and whole_or_str != None:
            if type(dec) == int and type(whole_or_str) == int:
                dec = int(self.pad_dec_with_zeros(str(dec), "right"))
                temp = [whole_or_str, dec]
                self.whole, self.dec = self.number(temp)
                self.update()
        else:        
            if whole_or_str != None:
                self.whole, self.dec = self.number(whole_or_str)
                self.update()
            
    def update(self): 
        self.as_str = self.no_to_str(self.whole, self.dec)
        self.as_str = self.truncate_decimal(self.as_str, self.limit_precision)
        #formatting = "%." + str(self.limit_precision) + "f"
        self.as_decimal = decimal.Decimal(self.as_str)
    
    def is_cryptocurrency(self, code):
        return int(code in cryptocurrencies)
        
    def is_fiatcurrency(self, code):
        return int(code in fiatcurrencies)

    def pad_dec_with_zeros(self, dec, direction, precision=None):
        """
        This function is used mostly to ensure that conversion from
        decimals as strings is done right. For example, the input
        "0.0001" is a human-readable number, but it needs to be stored
        in the database as: [0, 1000000000000]. To get the correct
        number for [1], pad_dec_with_zeros(n, "right") needs to be used.
        Conversely, sometimes you want to do the opposite - convert
        a int to a human-readable number:
        x.pad_dec_with_zeros("1000000000000", "left") which produces
        "0001000000000000." However you will notice there are
        insignificant digits after the "1", hence
        self.truncate_insignificant is called on the result to produce
        the original human-readable number: "0.0001."

        Returns a decimal represented as a string on success.
        """
        if type(dec) != str:
            raise Exception("Invalid type for dec in pad dec with zeros.")

        if precision == None:
            precision = self.precision

        dec_len = len(dec)
        if dec_len < precision:
            for i in range(dec_len, precision):
                if direction == "left":
                    dec = "0" + dec
                else:
                    dec += "0"

        return dec

    def pieces(self, s):
        """
        This function is used to convert its input to a list of two
        int64s which is what the database uses. It indirectly allows
        the math function to take any type of argument for its
        operands. The same can also be said of the number function.

        Note that this function is called indirectly by other
        functions.

        Returns a list containing two longs on success - one for the
        whole portion, the other for the decimal.
        """

        #Decimal passed.
        f = ".%sf" % (str(self.precision))
        if type(s) == decimal.Decimal:
            s = str(format(s, f))
        if type(s) == decimal_type:
            s = str(format(s, f))

        #Float passed.
        if type(s) == float:
            s = str(s)
            print("Waring: float passed. Value may be imprecise.")

        #Number already passed.
        if type(s) == int:
            s = int(s)
            if s > self.dec_no_limit:
                return self.from_single_int(int(s))
            else:
                return [int(s), int(0)]

        #Result already passed.
        if type(s) == list or type(s) == tuple:
            if len(s) >= 2:
                if (type(s[0]) == int and type(s[1]) == int):
                    return [int(s[0]), int(s[1])]

        if type(s) != str:
            print("Invalid:")
            print(s)
            print(type(s))
            raise Exception("Invalid type for pieces")

        p = re.findall("^([0-9]+)(?:(?:[.])([0-9]+))?(?:(?:\s+)?([a-zA-Z]+))?$", s)
        if len(p) != 1:
            raise Exception("Invalid number format for pieces.")
        p = p[0]

        if p[1] == "":
            whole = int(p[0])
            dec = int(0)
        else:
            whole = int(p[0])
            dec = int(self.pad_dec_with_zeros(p[1], "right"))

        if p[2] != "":
            currency = p[2].lower()
            try:
                if self.is_cryptocurrency(currency):
                    self.currency = cryptocurrencies[currency]["name"]

                if self.is_fiatcurrency(currency):
                    self.currency = fiatcurrencies[currency]["name"]
            except:
                "Not a currency code or currency is not known."

        if type(whole) != int:
            raise Exception("Invalid whole number for pieces")

        if type(dec) != int:
            raise Exception("Invalid dec number for pieces")

        return [whole, dec]

    def no_to_str(self, whole, dec):
        """
        Converts a number which has been broken down into int whole,
         and int dec, back into a decimal. E.g. 1, 2 -> "1.2."
        Useful for conversion.

        Return value is a string representing the inputs as a dotted
        decimal.
        """

        if type(whole) != int:
            raise Exception("invalid whole number in no to str")
        if type(dec) != int:
            raise Exception("invalid dec number in no to str")
        result = str(whole) + "." + str(self.pad_dec_with_zeros(str(dec), "left"))

        #Check number.
        self.number(result)

        return result

    def number(self, s):
        """
        This function is used to parse function parameters to see
        if they qualify as a valid number. It checks for things like
        correct type, expected value, and whether or not there is an
        overflow.

        If there was no error it returns a list of two ints
        - the first for the whole portion, the second for the decimal.
        """

        if type(s) == C:
            return [s.whole, s.dec]

        p = self.pieces(s)
        whole = p[0]
        dec = p[1]
        if whole > self.whole_no_limit:
            print(whole)
            print("Overflow overflow overflow")
            raise Exception("Whole number overflow in number")
        if dec > self.dec_no_limit:
            raise Exception("Dec number overflow in number")
        return [whole, dec]

    def math(self, s1, s2, op, f="no"):
        """
        Carries out an operation (op) on any two operands (s1 and s2.)
        Evaluation order is s1 op s2.

        Returns a list of two ints on success: The first [0] is the
        whole portion, the second the decimal portion, e.g. [10, 1] =
        10.00000000000000001. Otherwise if you set the format parameter
        to "str", then the result will be a human-readable decimal.

        Note that if the operator is a Boolean operator then this
        function simply returns either int 1 or int 0.
        """

        valid_operators = ["+", "*", "-", "<", ">", "==", "<=", ">=", "!="]
        if op not in valid_operators:
            raise Exception("Invalid operator in bignum math.")

        valid_format = ["no", "str"]
        if f not in valid_format:
            raise Exception("Invalid format in bignum math.")

        p1 = self.number(s1)
        n1_whole = p1[0]
        n1_dec = p1[1]
        p2 = self.number(s2)
        n2_whole = p2[0]
        n2_dec = p2[1]
        result = ""

        if op == "<":
            if n1_whole < n2_whole:
                return 1
            else:
                if n1_whole == n2_whole:
                    if n1_dec < n2_dec:
                        return 1
                    else:
                        return 0
                else:
                    return 0

        if op == ">":
            if n1_whole > n2_whole:
                return 1
            else:
                if n1_whole == n2_whole:
                    if n1_dec > n2_dec:
                        return 1
                    else:
                        return 0
                else:
                    return 0

        if op == "==":
            if n1_whole == n2_whole:
                if n1_dec == n2_dec:
                    return 1
                else:
                    return 0
            else:
                return 0

        if op == "!=":
            if not self.math([n1_whole, n1_dec], [n2_whole, n2_dec], "=="):
                return 1
            else:
                return 0

        if op == ">=":
            if self.math([n1_whole, n1_dec], [n2_whole, n2_dec], ">") or self.math([n1_whole, n1_dec], [n2_whole, n2_dec], "=="):
                return 1
            else:
                return 0

        if op == "<=":
            if self.math([n1_whole, n1_dec], [n2_whole, n2_dec], "<") or self.math([n1_whole, n1_dec], [n2_whole, n2_dec], "=="):
                return 1
            else:
                return 0

        #Sets up format for numbers needed by the algorithm that
        #handles multiplication.
        if op == "*":
            if type(s1) != str:
                s1 = self.no_to_str(n1_whole, n1_dec)
            if type(s2) != str:
                s2 = self.no_to_str(n2_whole, n2_dec)

            s1 = self.truncate_insignificant(self.truncate_decimal(s1))
            s2 = self.truncate_insignificant(self.truncate_decimal(s2))
            total_dec_places = 0
            s1_parts = s1.split(".")
            s2_parts = s2.split(".")
            if len(s1_parts) == 2:
                total_dec_places += len(s1_parts[1])
            if len(s2_parts) == 2:
                total_dec_places += len(s2_parts[1])
            s1_str = "".join(s1_parts)
            s2_str = "".join(s2_parts)

        if op == "+":
            add_dec = n1_dec + n2_dec
            whole_carry = 0
            if add_dec > self.dec_no_limit:
                whole_carry = str(add_dec)
                add_dec = int(whole_carry[-self.precision : ])
                whole_carry = int(whole_carry[0 : len(whole_carry) - self.precision])

            add_whole = n1_whole + n2_whole + whole_carry
            result = [int(add_whole), add_dec]

        if op == "-":
            dec = n1_dec - n2_dec
            if dec < 0:
                m = "1"
                for i in range(0, self.precision):
                    m += "0"
                m = int(m)
                whole = (n1_whole - n2_whole) - 1
                w = whole
                if not whole:
                    w = 1
                dec = (1 * m) + dec
                if dec < 0:
                    dec = -dec
            else:
                whole = n1_whole - n2_whole

            result = [int(whole), dec]

        if op == "*":
            total = int(s1_str) * int(s2_str)
            total = str(total)
            if total_dec_places:
                #Padd with zeros.
                if len(total) <= total_dec_places:
                    p = total_dec_places - len(total)
                    for i in range(0, p):
                        total = "0" + total
                    total = "0." + total

                    whole = total[:-total_dec_places - 1]
                else:
                    whole = total[:-total_dec_places]
                dec = total[-total_dec_places:]

            else:
                whole = total
                dec = "0"

            if len(dec) > self.precision:
                dec = dec[0:self.precision]
            else:
                dec = self.pad_dec_with_zeros(dec, "right")
                
            result = [int(whole), int(dec)]
            
        
        if op == "/":
            """
            Division is pretty ugly.
            Try avoid using it for important calculations.
            """
            
        if result[0] > self.whole_no_limit:
            raise Exception("whole overflow in math bignum func")
        if result[0] < 0:
            raise Exception("whole cannot be negative in bignum func")
        if len(str(result[1])) > self.precision:
            #Truncate trailing decimal.
            result[1] = result[1][:self.precision]
        if result[1] < 0:
            raise Exception("dec cannot be negative in bignum func")

        if f == "str":
            result[1] = self.pad_dec_with_zeros(str(result[1]), "left")
        else:
            result[1] = int(result[1])
        return result

    def truncate_decimal(self, s, precision=None):
        """
        This function basically discards the portion of a decimal
        number which exceeds the precision defined in self.precision.
        It is currently used to "clean" a number in the math routine
        for use by the multiplication algorithm.

        Returns a truncated decimal string on success.
        """
        if type(s) != str:
            raise Exception("Truncate decimal expects str")

        parts = s.split(".")
        if len(parts) == 1:
            dec = self.pad_dec_with_zeros("0", "left")
        else:
            dec = parts[1]
        whole = parts[0]

        #Formatting.
        if precision != None:
            dec = dec[0:precision]
            return "%s.%s" % (str(whole), str(dec))

        #Truncate overflow.
        if len(dec) > self.precision:
            dec = dec[0:self.precision]
        dec = self.pad_dec_with_zeros(dec, "right")

        #Check number.
        s = self.no_to_str(int(whole), int(dec))

        return s

    def decimal_len(self):
        if not self.dec:
            return 0
        else:
            no = str(self)
            dec = no.split(".")[1]
            return len(dec)

    def truncate_insignificant(self, s):
        """
        Removes insignificant digits in the decimal portion of a
        number which allows for better presentation of numbers.

        Returns a decimal string with no significant digits on success.
        """
        if type(s) != str:
            raise Exception("truncate insignificant expects str")

        #Check number.
        self.number(s)

        parts = s.split(".")
        if len(parts) == 1:
            return parts[0]
        if not int(parts[1]):
            return parts[0]

        l = len(s)
        cut = "I'm sorry, Dave. I'm afraid I can't do that."
        for i in range(1, l + 1):
            if s[-i] == "0":
                cut = -i
            else:
                break
       
        if type(cut) == int:
            s = s[:cut]

        return s

    #Operator ==
    def __eq__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = "=="   
        return bool(self.math(a, b, op))
        
    #Operator !=
    def __ne__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = "!="   
        return bool(self.math(a, b, op))
        
    #Operator <
    def __lt__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = "<"   
        return bool(self.math(a, b, op))
        
    #Operator >
    def __gt__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = ">"   
        return bool(self.math(a, b, op))
        
    #Operator <=
    def __le__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = "<="   
        return bool(self.math(a, b, op))
        
    #Operator >=
    def __ge__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = ">="   
        return bool(self.math(a, b, op))
        
    #Operator +
    def __add__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = "+"   
        return C(self.math(a, b, op))
        
    #Operator -
    def __sub__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = "-"   
        return C(self.math(a, b, op))
        
    #Operator *
    def __mul__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = "*"   
        return C(self.math(a, b, op))

    """
    def __truediv__(self, other):
        if type(other) != C:
            other = C(other)
                         
        a = [self.whole, self.dec]
        b = [other.whole, other.dec]
        op = "/"   
        return C(self.math(a, b, op))
    """

    #Type conversation to str
    def __str__(self):
        old_str = str(self.as_str)
        new_str = str(self.truncate_insignificant(str(self.as_str)))

        """
        This ensures that when type casting to a str,
        the resulting type always 'looks' like a float.
        That way programmers who assume it will always
        be in a float format won't introduce bugs
        into their software by being wrong.
        """
        if len(new_str) != len(old_str):
            if "." not in new_str:
                new_str += ".00"
        return new_str

    #Boolean type conversion.
    def __bool__(self):
        return not bool(self.math(self, "0", "=="))
        
    #Type conversion to int.
    def __int__(self):
        return int(self.whole)
        
    #Type conversion to float.
    def __float__(self):
        return float(str(self.as_str))
    
    """    
    def __dict__(self):
        return {
            "whole": int(self.whole),
            "dec": int(self.dec)
        }
    """
        
    #These methods help implement list and tuple.
    def __len__(self):
        return 2

    """
    Instead of storing the values in two different data types: this one assumes the class is being initialised from a single integer and extracts the values accordingly. 
    """
    def from_single_int(self, single_int):
        single_int = str(single_int)
        dec = single_int[-self.precision:]
        whole = 0
        if len(single_int) > self.precision:
            whole = single_int[:-self.precision]

        return [whole, dec]
        
    def __getitem__(self, key):
        if key not in self.valid_keys:
            raise KeyError
            
        if key == "whole" or key == 0:
            return int(self.whole)
        
        if key == "dec" or key == 1:
            return int(self.dec)

        """
        This allows whole and dec to be stored as a single field in a database.
        """
        if key == "int" or key == 2:
            padded_whole = int(self.whole) * int("1" + ("0" * self.precision))
            single_int = padded_whole + int(self.dec)
            return single_int
            
    def __setitem__(self, key, value):
        if key not in self.valid_keys:
            raise KeyError
        if type(value) != int and type(value) != str:
            raise ValueError
        value = int(value)
            
        if key == "whole" or key == 0:
            self.whole = value
        if key == "dec" or key == 1:
            self.dec = int(self.pad_dec_with_zeros(str(value), "right"))
        if key == "int" or key == 2:
            self.whole, self.dec = self.from_single_int(value)
        self.update()
    
    """        
    def __delitem__(self, key):
        if key not in self.valid_keys:
            raise KeyError
            
        self.valid_keys.pop(key)
    """
    
    def __iter__(self):
        return iter([int(self.whole), int(self.dec)])
        
    def __reversed__(self):
        return iter([int(self.dec), int(self.whole)])
        
    def __missing__(self, key):
        if key not in self.valid_keys:
            raise KeyError
        
        """    
        return {
            "whole": int(self.whole),
            "dec": int(self.dec)
        }
        """
"""
Bad idea.

#Patch decimal to support type conversion from C.
decimal.Decimal = decimal_wrapper(decimal_type)
"""
            
if __name__ == "__main__":
    a = C("1.0")
    b = C("0.00000045")


    print(a["whole"])
    print(a["dec"])

    x = a["whole"] * int("1" + ("0" * a.precision))
    x = x + a["dec"]
    print(x)

    exit()
    #0.00000069
    print(a["dec"])
    #6900000000

    exit()
    print(C("0.000000000000123456"))


    exit()
    a = C("5.23123 usd")
    print(a.currency)
    print(a)


    exit()
    #x = C()
    #print(x.math("0.00000000000002", "0.01", "*", "no"))
    #print x.math("0.000000013", "0.00004", "*", "str")
    #x.math("4.5", "9.1", "/")
    #print x.math("450", "0", "-")
    #print x.math("0", "0", "-")
    fees = [
        "2",
        "2.0",
        "2%",
        "2.0%",
        "2 aud",
        "2.0 aud",
        "2% aud",
        "2.0% aud",
    ]

    x = C(0)
    #print(x == 1)
    #exit()
    print(bool(x))




