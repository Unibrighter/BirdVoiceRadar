import couchdb
import os
couch_server=couchdb.Server('http://bitmad:mylife4aiur@localhost:5984/')


# use this piece of code to update the storing location of the audio files
# enable them to be served by Nginx
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

result_dictionary=db_bird.view("record/record_by_md5")

#update the storing location of all the audio files
for row in result_dictionary:
    record_doc=row.value
    if record_doc['training_data']=='true':
        record_doc['confidence']==1.0

        head, tail = os.path.split(record_doc['file_path'])
        target_file_path=os.path.join('F:\\MSc_Proj\\nginx-1.10.1\\html\\audio\\training',tail)

        record_doc['file_path']=target_file_path

        db_bird.save(record_doc)

        print record_doc
    # delete of the testing uploading data.
    else:
        db_bird.delete(record_doc)



