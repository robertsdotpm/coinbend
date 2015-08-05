from unittest import TestCase
from coinbend.sock import *

class test_sock(TestCase):
    def test_0000001_sock(self):
        s = Sock("www.example.com", 80, blocking=0)
        data =  "GET / HTTP/1.1\r\n"
        data += "Host: www.example.com\r\n\r\n"
        s.send(data)
        time.sleep(1)
        replies = ""
        for reply in s:
            replies += reply
            print(reply)
        assert(replies != "")

        s = Sock()
        s.buf = "\r\nx\r\n"
        x = s.parse_buf()
        assert(x[0] == "x")

        s.buf = "\r\n"
        x = s.parse_buf()
        assert(x == [])

        s.buf = "\r\n\r\n"
        x = s.parse_buf()
        assert(x == [])

        s.buf = "\r\r\n\r\n"
        x = s.parse_buf()
        assert(x[0] == "\r")

        s.buf = "\r\n\r\n\r\nx"
        x = s.parse_buf()
        assert(x == [])

        s.buf = "\r\n\r\nx\r\nsdfsdfsdf\r\n"
        x = s.parse_buf()
        assert(x[0] == "x" and x[1] == "sdfsdfsdf")


        s.buf = "sdfsdfsdf\r\n"
        s.parse_buf()
        s.buf += "abc\r\n"
        x = s.parse_buf()
        assert(x[0] == "abc")


        s.buf += "\r\ns\r\n"
        x = s.parse_buf()
        assert(x[0] == "s")

