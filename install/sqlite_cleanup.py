"""
Converts the output of mysql2sqlite.sh so that the
id field is considered auto-increment and primary
to sqlite. This could be done by modifying the
mysql2sqlite.sh, but awk looks like brainfuck.
"""

import re
content_file = open("sqlite.sql", 'r+')
content = content_file.read()
content = re.sub(r"""["]id" int[(][0-9]+[^,]+?[,]""", "\"id\" INTEGER PRIMARY KEY AUTOINCREMENT,", content)
content = re.sub(r""",[\s]+?PRIMARY KEY [(]"id"[)][\s]+?[)]""", "\n)", content)
content = re.sub(r"""BEGIN TRANSACTION;""", "", content)
content = re.sub(r"""END TRANSACTION;""", "", content)
content = re.sub(r"""PRAGMA synchronous = OFF;""", "", content)
content = re.sub(r"""PRAGMA journal_mode = MEMORY;""", "", content)
content_file.seek(0)
content_file.write(content)
content_file.truncate()
content_file.close()
