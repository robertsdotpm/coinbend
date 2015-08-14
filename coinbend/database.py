"""
Provides a wrapper for oursql and sqlite3 that enforces
serializable isolation and manual transaction management
for database operations designed to maintain consistent
accounting records. Also includes a context manager.

See User module for an example of a function which uses
this.
"""

import sys
from .parse_config import *
from .lib import *
import time
import oursql
import sqlite3
import re
import os

class Database():
    def __init__(self, isolation="serializable"):
        self.timeout = 5
        self.cur = None
        self.serializable = \
        [
            "SET autocommit=0;",
            "SET SESSION TRANSACTION ISOLATION LEVEL SERIALIZABLE;",
            "START TRANSACTION;"
        ]

        #Load config.
        self.config = ParseConfig(os.path.join(data_dir, "config.json"))
        
        #Connect.
        self.connected = 0
        self.in_transaction = 0
        self.disable_transactions = 0
        if not self.connect(blocking=0):
            raise Exception("Unable to connect to database server.")
        
    def connect(self, blocking=1):
        #Already connected.
        if self.connected:
            return
            
        #Block until connected.
        while not self.connected:
            #Flat file.
            if self.config["flat_file"]:
                try:
                    flat_file_path = os.path.join(data_dir, self.config["flat_file"])
                    self.con = sqlite3.connect(
                    database=flat_file_path,
                    timeout=self.timeout,
                    detect_types=0,
                    isolation_level="EXCLUSIVE",
                    check_same_thread=False)
                    self.connected = 1
                    #Mimics oursql dict cursor for fetch.
                    self.con.row_factory = sqlite3.Row
                except Exception as e:
                    print(e)
                    print("Sqlite3 unable to connect.")
                    self.kill_connection()
            else: #MySQL
                for db_server in self.config["db_servers"]:
                    try:
                        #raise_on_warnings for debug
                        self.con = oursql.connect(
                        host=db_server["host"],
                        port=int(db_server["port"]),
                        user=db_server["user"],
                        passwd=db_server["pass"],
                        db=db_server["name"],
                        init_command=self.serializable[0],
                        raise_on_warnings=1)
                        self.connected = 1
                        break
                    except Exception as e:
                        print(e)
                        print("Mysql server down.")
                        self.kill_connection()
                    
            #Avoid raping a CPU core if connection can't succeed.
            if not self.connected:
                if not blocking:
                    return 0
                else:
                    print("All database servers and files down.")
                    time.sleep(0.5)
        
        #Success.
        return 1

    def disconnect(self):
        self.kill_connection()
        
    def commit(self):
        self.con.commit()
        
    def execute(self, sql, parameterization=None, blocking=1):
        try:
            if parameterization != None:
                #Check parameters for obscure attacks.
                vectors = ["outfile", "load_file", "xp_cmdshell", "attach database", "load_extension", "readfile", "writefile"]
                allowed_charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890`~!@#$%^&*()-_=+{[}]:;\"<,>.?/ \r\n\t"
                for param in parameterization:
                    param = str(param).lower()
                    for ch in param:
                        if ch not in allowed_charset:
                            print(ch)
                            raise Exception("Invalid character in query parameter.")

                    for vector in vectors:
                        if vector in param:
                            raise Exception("Attack vector detected in query parameter.")

                #Execute parameterized query.
                self.cur.execute(sql, parameterization)
            else:
                self.cur.execute(sql)
            return 1
        except Exception as e:
            #Can also occur if SQL syntax is wrong.
            #Or incorrect parameterization.

            if int(self.config["debug"]):
                print(e)
            self.kill_connection()
            if self.connect(blocking):
                #SQL wasn't executed but successfully reconnected.
                raise Exception("Temporarily lost connection to database.")

            #SQL wasn't executed and a connection couldn't be restablished.
            raise Exception("Database connection died. Unable to execute SQL.")
            
            """
            You don't reexecute the SQL. It might of been part
            of a transaction relying on the state of previous calls.
            If that's the case, financial records will end up in an
            incorrect state.
            """
    
    def start_transaction(self):
        """
        Starts a transaction and
        checks that the transaction level is actually set.
        """
        if self.disable_transactions:
            return 1

        #Already in a transaction.
        if self.in_transaction:
            raise Exception("Already in a transaction.")
        try:
            if self.config["flat_file"]:
                self.cur = self.con.cursor()
                self.cur.execute("BEGIN TRANSACTION;")
                self.in_transaction = 1
                return 1
            else:
                self.cur = self.con.cursor(oursql.DictCursor)
                for sql in self.serializable:
                    self.cur.execute(sql)

                self.cur.execute("SELECT @@session.tx_isolation")
                tx_isolation = self.cur.fetchall()[0]["@@session.tx_isolation"]
                if tx_isolation != u"SERIALIZABLE":
                    raise Exception
                self.in_transaction = 1
                return 1
        except Exception as e:
            print(e)
            print("Unable to set transaction level to serializable in main.")
            return 0
            
    def finish_transaction(self):
        #Graceful close for transactions.
        #Propogates a transaction state. Do this if no errors occur.
        if self.disable_transactions:
            return 1
        try:
            self.con.commit()
            self.cur.close()
            self.in_transaction = 0
            return 1
        except:
            return 0
            
    def destroy_transaction(self):
        #Ungracefully destroy a transaction.
        #Transaction state is not propogated.
        if self.disable_transactions:
            return 1
        try:
            self.con.rollback()
            self.cur.close()
            self.in_transaction = 0
            return 1
        except:
            return 0
        

    def kill_connection(self):
        #Close cursor.
        try:
            self.cur.close()
        except:
            pass        
        
        #Close connection.
        try:
            self.con.close()
        except:
            pass
            
        self.connected = 0
        self.in_transaction = 0
        return 1

    def fetchall(self):
        #Convert sqlite3.Row to standard dict.
        if self.config["flat_file"]:
            return [dict(row) for row in self.cur]
        return self.cur.fetchall()
        
class Transaction():
    """
    This function is used to handle executing SQL code in
    a database transaction and keeps track of the context for
    transactions. For example, suppose you need to execute
    SQL in a transaction as part of a function call.
    How do you know whether you need to start a new transaction?
    If the function was called as a helper function from
    another function, then you might already be in a
    transaction and wish to continue it.
    
    This function answers questions like:
    How do you know if you're already in a transaction?
    How do you propogate transaction state down the function
    call stack?
    How do you swap in a new database connection and
    transaction context whenever you want?
    
    Using optional function parameters for functions that
    work with database transactions turns out to be an
    easy solution, but another part of this code is also
    essential: self.disable_transactions.
    
    There needs to be a way to restore the previous state
    for whether or not transactions will be disabled
    for the current context when this call ends
    That is why the state of self.disable_transactions is
    stored before any potential new modifications. If you
    were to arbitarily assume that you need to renable
    transactions at the end of this execution AND you were
    already in a transaction when you entered, then you
    may accidentally cause errors not to propogate up to
    the parent function and cause an invalid state to be
    saved to the database.
    
    Only the parent function which starts the transaction
    has the right to decide to commit the transaction. The
    above problem could accidentally enable a problem func
    to mess up everything.
    
    I know that's a lot of documentation for 50~ lines of
    code, but those lines aren't so intuitive. 
    """
    def __init__(self, db=None):
        #Set DB connection.
        if db == None:
            self.db = Database()
        else:
            self.db = db
            
    def execute(self, sql, parameterization=None, blocking=1):
        #Test the required parameters exist.
        if parameterization != None:
            detected_p = re.findall("[?]", sql)
            if len(detected_p) != len(parameterization):
                raise Exception("Required parameterization not met.")

        #Split multiple queries.
        queries = sql.split(";")
        ret = None
        for query in queries:
            #Blank query.
            if re.match("^(\s+)?$", query) != None:
                continue

            #Extract parameters to match individual query.
            if parameterization != None:
                required_parameters_no = len(re.findall("[?]", query))
                if required_parameters_no:
                    required_parameters = parameterization[:required_parameters_no]
                    parameterization = parameterization[required_parameters_no:]
                else:
                    required_parameters = None
            else:
                required_parameters = None

            #Append result.
            if ret == None:
                ret = self.db.execute(query, required_parameters, blocking)
            else:
                ret += self.db.execute(query, required_parameters, blocking)

        return ret
        
    def fetchall(self):
        #Convert sqlite3.Row to standard dict.
        if self.db.config["flat_file"]:
            return [dict(row) for row in self.db.cur]
        return self.db.cur.fetchall()

    def __enter__(self):
        self.disable_transactions = self.db.disable_transactions
        if self.db.in_transaction:
            self.db.disable_transactions = 1
        self.db.start_transaction()
        return self
        
    def __exit__(self, type, value, traceback):
        if isinstance(value, Exception):
            print(value)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error = "%s %s %s" % (str(exc_type), str(fname), str(exc_tb.tb_lineno))
            print(error)
            self.db.destroy_transaction()
        else:
            if not self.db.finish_transaction():
                self.db.destroy_transaction()
        self.db.disable_transactions = self.disable_transactions
        return True

if __name__ == "__main__":
    """
    with Transaction() as tx:
        tx.execute("SELECT * FROM `users`;")
        print(tx.fetchall())
    """
   
    """
    with Transaction() as tx:
        sql_path = data_dir + os.sep + "coinbend.sql"
        with open(sql_path, "r") as content_file:
            sql = content_file.read()
            print(sql)
            tx.execute(sql)

        sql = "INSERT INTO `balances` (`user_id`) VALUES (?);"
        tx.execute(sql, (1,))
        tx.execute(sql, (1,))
        sql = "SELECT * FROM `balances`;"
        tx.execute(sql)
        print("yo")
        r = tx.fetchall()
        print(r[0]["user_id"])
        print(r[1]["user_id"])
        r[0]["user_id"] = "test"
    """
