from unittest import TestCase
from coinbend.database import *
import re
from multiprocessing.dummy import Pool
import time

"""
Things to test.

MySQL [ ] and Sqlite [x]
Check isolation works [x]
Test for dead locks [x]
with Transaction  [x]
    * Include propogation [x]
Multiple statements [x]
Parameterization [x]
    * In where clause [x]
Select [x]
Update [x]
Insert [x]
Delete [x]
Non-blocking [ ], blocking [x]
    * Timeouts [ ]
Reconnects [ ]
"""

class test_database(TestCase):
    def sim_execute(self, sql, parameterization=None):
        ret = None
        db = Database()
        db.connect(blocking=1)
        db.start_transaction()
        db.execute(sql, parameterization)
        if re.match("^SELECT", sql) != None:
            ret = db.fetchall()
        db.finish_transaction()
        db.disconnect()
        return ret

    def test_000000_insert(self):
        self.sim_execute("INSERT INTO `users` (`username`) VALUES ('test');")

    def test_000001_insert_p(self):
        self.sim_execute("INSERT INTO `users` (`username`) VALUES (?);", ("testp",))

    def test_000002_insert_p2(self):
        self.sim_execute("INSERT INTO `users` (`username`, `email`) VALUES (?, ?)", ("test3", "Test3"))

    def test_000003_select(self):
        row = self.sim_execute("SELECT * FROM `users` WHERE `username`=?", ("test",))[0]
        assert(row["username"] == "test")

    def test_000004_select2(self):
        row = self.sim_execute("SELECT * FROM `users` WHERE `username`=? AND `email`=?", ("test3", "Test3"))[0]
        assert(row["username"] == "test3")
        assert(row["email"] == "Test3")

    def test_000005_update(self):
        sql = "UPDATE `users` SET `username`=? WHERE 1=1"
        self.sim_execute(sql, ("updated",))

    def test_000006_delete(self):
        sql = "DELETE FROM `users` WHERE `username`=?;"
        self.sim_execute(sql, ("updated",))

    def test_000007_transaction_insert(self):
        ret = 0
        with Transaction() as tx:
            tx.execute("INSERT INTO `users` (`username`) VALUES ('tran_test');")
            ret = 1
        assert(ret == 1)

    def test_000008_tran_insert_p(self):
        ret = 0
        with Transaction() as tx:
            tx.execute("INSERT INTO `users` (`username`) VALUES (?);", ("000008",))
            ret = 1
        assert(ret == 1)

    def test_000009_tran_insert_p(self):
        ret = 0
        with Transaction() as tx:
            tx.execute("INSERT INTO `users` (`username`, `email`) VALUES (?, ?);", ("000009", "000009"))
            ret = 1
        assert(ret == 1)

    def test_000010_tran_multiline(self):
        ret = 0
        with Transaction() as tx:
            sql = """INSERT INTO `users` (`username`) VALUES ("a");"""
            sql = sql * 2
            tx.execute(sql)
            ret = 1
        assert(ret == 1)

    def test_000011_tran_multiline_p1(self):
        ret = 0
        with Transaction() as tx:
            sql = """INSERT INTO `users` (`username`) VALUES ("a"); INSERT INTO `users` (`username`) VALUES (?);"""
            tx.execute(sql, ("x",))
            ret = 1
        assert(ret == 1)

    def test_000012_tran_multiline_p2(self):
        ret = 0
        with Transaction() as tx:
            sql = """INSERT INTO `users` (`username`) VALUES ("a"); INSERT INTO `users` (`username`) VALUES (?); INSERT INTO `users` (`username`) VALUES ("a"); INSERT INTO `users` (`username`) VALUES (?);"""
            tx.execute(sql, ("x", "y"))
            ret = 1
        assert(ret == 1)

    def test_000013_tran_select(self):
        ret = 0
        with Transaction() as tx:
            tx.execute("SELECT * FROM `users` WHERE `username`=?", ("a",))
            row = tx.fetchall()[0]
            assert(row["username"] == "a")
            ret = 1
        assert(ret == 1)


    def test_000014_tran_select2(self):
        ret = 0
        with Transaction() as tx:
            tx.execute("SELECT * FROM `users` WHERE `username`=? AND `email`=?", ("000009", "000009"))
            row = tx.fetchall()[0]
            assert(row["username"] == "000009")
            assert(row["email"] == "000009")
            ret = 1
        assert(ret == 1)


    def test_000015_tran_update(self):
        ret = 0
        with Transaction() as tx:
            tx.execute("UPDATE `users` SET `username`=? WHERE 1=1", ("updated",))
            ret = 1
        assert(ret == 1)


    def test_000016_tran_delete(self):
        ret = 0
        with Transaction() as tx:
            tx.execute("DELETE FROM `users` WHERE `username`=?;", ("updated",))
            ret = 1
        assert(ret == 1)

    def test_000017_tran_nestled(self):
        ret = 0
        db = Database()
        with Transaction(db) as tx:
            tx.execute("INSERT INTO `users` (`username`) VALUES (?);", ("not_commited",))
            ret = 1
            with Transaction(db) as tx2:
                ret = 0
                tx2.execute("SELECT * FROM `users` WHERE `username`=?", ("not_commited",))
                row = tx2.fetchall()[0]
                assert(row["username"] != "not_commited")
                ret = 1

            assert(ret == 0)

        ret = 0
        with Transaction(db) as tx:
            tx.execute("SELECT * FROM `users` WHERE `username`=?", ("not_commited",))
            row = tx.fetchall()[0]
            assert(row["username"] == "not_commited")
            ret = 1
        assert(ret == 1)

        ret = 0
        with Transaction(db) as tx:
            tx.execute("DELETE FROM `users` WHERE `username`='not_commited';")
            ret = 1
        assert(ret == 1)


        ret = 0
        with Transaction(db) as tx:
            ret = 1
            tx.execute("SELECT * FROM `users` WHERE `username`=?", ("not_commited",))
            row = tx.fetchall()[0]
            assert(row["username"] != "not_commited")
            ret = 0
        assert(ret == 1)

    def test_000018_tran(self):
        ret = 0
        db = Database()
        with Transaction(db) as tx:
            tx.execute("INSERT INTO `users` (`username`) VALUES (?);", ("not_commited2",))
            raise Exception("tx err")
            ret = 1
        assert(ret != 1)

        ret = 0
        with Transaction(db) as tx:
            tx.execute("SELECT * FROM `users` WHERE `username`=?", ("not_commited2",))
            row = tx.fetchall()
            assert(row == [])
            ret = 1
        assert(ret == 1)

    def thread_a(self, p):
        ret = 0
        db = Database()
        with Transaction(db) as tx:
            tx.execute("UPDATE `balances` SET `btc_whole`=? WHERE `id`=?", ("2000", p[0]))
            time.sleep(5)
            ret = 1
        assert(ret == 1)

    def thread_b(self, p):
        ret = 0
        with Transaction() as tx:
            tx.execute("SELECT * FROM `balances` WHERE `id`=?", (p[0],))
            row = tx.fetchall()[0]
            assert(row["btc_whole"] == 2000)
            ret = 1
        assert(ret == 1)        

    def test_000018_serialization(self):
        ret = 0
        db = Database()
        with Transaction(db) as tx:
            tx.execute("INSERT INTO `balances` (`btc_whole`) VALUES (1000);")
            ret = tx.db.cur.lastrowid
        assert(ret != 0)

        pool = Pool()
        pool.map(self.thread_a, [[ret]])
        pool.close()
        pool.join()

        pool = Pool()
        pool.map(self.thread_b, [[ret]])
        pool.close()
        pool.join()

        time.sleep(6)

    def test_000019_tran_delete(self):
        ret = 0
        with Transaction() as tx:
            tx.execute("DELETE FROM `balances` WHERE 1=1")
            ret = 1
        assert(ret == 1)

