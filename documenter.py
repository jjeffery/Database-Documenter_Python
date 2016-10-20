from pgdb import connect
from mako.template import Template
import os

show_all_tables = """
select table_name from information_schema.tables
where table_schema = 'public';
"""

show_comment = """
select description, objsubid
from pg_description
where objoid = '{0}' and objsubid = '{1}';
"""

show_columns = """
select column_name, data_type, character_maximum_length
from information_schema.columns 
where table_name = '{0}';
"""

particular_column_things = """
select *
from information_schema.columns 
where table_name = '{0}' and ordinal_position = {1};
"""

table_things = """
select oid, relname
from pg_class
where relname = '{0}';
"""

table_from_relid = """
select relname
from pg_class
where oid = {0}
"""

no_desc = "~No Description~"

key_things = """
select conname, case c.contype
    when 'u' then 'Unique'
    when 'p' then 'Primary Key'
    when 'f' then 'Foreign Key'
END as "contype", condeferrable, confrelid, confkey
from pg_constraint c
where conrelid = '{0}' and conkey @> array[{1}::smallint];
"""

tables = {}

class Table(object):
    def __init__(self, name):
        self._name = name
        self._description = ""
        self._columns = []

        table_cursor = con.cursor()
        table_cursor.execute(table_things.format(self._name));
        self._relid = table_cursor.fetchone().oid

        print("rel id", self._relid)
        

        table_cursor = con.cursor()
        for i, each_col in enumerate(table_cursor.execute(show_columns.format(self._name))):
            self._columns.append(Column(self._name, self._relid, each_col.column_name, i+1, each_col.data_type, each_col.character_maximum_length))
        table_cursor.close()
        
        
        
    def set_desc(self, desc):
        self._description = desc

    def get_desc(self):
        return self._description

    def get_relid(self):
        return self._relid

    def get_name(self):
        return self._name

    def get_cols(self):
        return self._columns

    def __str__(self):
        return "Table: {0}  Desc: {1}".format(self._name, self.get_desc())

    def __repr__(self):
        return "Table: {0}  Desc: {1}".format(self._name, self.get_desc())

class Column(object):
    """
    holds column information
    """

    def __init__(self, table, relid, name, ordinal, type, length):
        self._name = name
        self._type = type
        self._length = length
        self._parent_table = table
        self._par_table_id = relid
        self._description = no_desc
        self._ord = ordinal

        print(self._parent_table, self._ord)

        col_cursor = con.cursor()
        col_cursor.execute(show_comment.format(self._par_table_id, self._ord))
        if col_cursor.rowcount == 1:
            self._description = col_cursor.fetchone().description
        print(self._description)

        col_cursor.close()
        self._key_type = "Non-Key"
        
        col_cursor = con.cursor()
        col_cursor.execute(key_things.format(self._par_table_id, self._ord))
        if col_cursor.rowcount == 1:
            results = col_cursor.fetchone()
            print(results)
            self._conname = results.conname
            self._contype = results.contype
            print(self._contype)
            self._condeferrable = results.condeferrable
            self._confrelid = results.confrelid
            #if results.contype == 'Foreign Key':
            try:
                self._confkey = list(results.confkey)[0]
                print("f rel id type", self._confkey)
            except TypeError:
                self._confkey = ""
            #else:
             #  self._confkey = ""
        col_cursor.close()
        
        
    def get_key_type(self):
        #print("key type", self._contype)
        try: 
            if self._contype == 'Foreign Key':
                key_cursor = con.cursor()
                key_cursor.execute(table_from_relid.format(self._confrelid))
                relname = key_cursor.fetchone().relname
                print("relname: ", relname)
                key_cursor.close()

                frkey_cursor = con.cursor()
                print("self confkey", type(self._confkey), "self name", self._name)
                frkey_cursor.execute(particular_column_things.format(relname, self._confkey))
                
                colname = frkey_cursor.fetchone().column_name
                print("colname", colname)
                print("relname: ", relname)
                frkey_cursor.close()
                return "{0} - {1} REFFERENCES {2}.{3}".format(self._contype, self.get_name(), relname, colname) #key_cursor2.fetchone().column_name key_cursor.fetchone().relname
                
            else:
                return self._contype
        except AttributeError:
           return self._key_type

    def get_name(self):
        return self._name

    def get_type(self):
        return self._type

    def get_length(self):
        return self._length

    def get_description(self):
        return self._description


database = input("Database: ")

host = input("Host: (host:port) Default: localhost:5432 ")
if host == "" or host.isspace():
    host = "localhost:5432"

user = input("Username: ")
password = input("Password: ")

con = connect(database=database, host=host, user=user, password=password)

cursor = con.cursor()
cursor2 = con.cursor()
i = 0
for eachtable in cursor.execute(show_all_tables): # loop over each table
    i += 1
    print(i)
    tbl = eachtable.table_name
    print(eachtable.table_name)
    tables[tbl] = Table(tbl)
    print("here and there")
    cursor2.execute(show_comment.format(tables[tbl].get_relid(), 0)) # grab table desc
    if cursor2.rowcount != 0:
        desc = cursor2.fetchone().description
        print(desc)
    else:
        desc = no_desc
    tables[tbl].set_desc(desc) # set table desc


    
    print(tables[tbl]) # print that object as a string

#print('here', tables['application'].get_desc())

doc_template = Template(filename='template.html')
print('there')
output = doc_template.render(tables=tables)
#print(output)

with open ('document.html', 'w') as f:
    f.write(output)
    f.close()