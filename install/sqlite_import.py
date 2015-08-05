import coinbend

with coinbend.Transaction() as tx:
    sql_path = "sqlite.sql"
    with open(sql_path, "r") as content_file:
        sql = content_file.read()
        tx.execute(sql)
