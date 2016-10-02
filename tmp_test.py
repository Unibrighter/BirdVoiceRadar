import couchdb

couch_server=couchdb.Server('http://bitmad:mylife4aiur@localhost:5984/')


if 'db_bird' not in couch_server:
    couch_server.create('db_bird')

db_bird=couch_server['db_bird']

tmp_new_user={
            "type":"account", # the user information, separated from other docs
            "username":"suck",
            "email":"suck.suck@suck.cc",
            "password":"aaaaaa",
            "expert":"true"
        }
# put the new added account information into the DB
# db_bird.save(tmp_new_user)

result=db_bird.view("account/account_by_email")

for row in result:
    print row.key
    print row.value

print result['suck.suck@suck.cc']