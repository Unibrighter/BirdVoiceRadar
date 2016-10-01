import couchdb

couch_server=couchdb.Server('http://bitmad:mylife4aiur@localhost:5984/')

user_db=couch_server.create('fuck')
user_1={"username":"admin","password":"admin","role":"admin"}

user_db.save(user_1)

print "done"
user_1