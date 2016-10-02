import os

# the place to store the uploaded audio files
# here the upload directory should be at the same level of config file
# UPLOAD_FOLDER = "../tmp"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__) + '/tmp')


# the file formats allowed
ALLOWED_EXTENSIONS = set(['wav'])

# CouchDB server connection
COUCHDB_SERVER='http://bitmad:mylife4aiur@localhost:5984'

DB_BIRD ='db_bird'

# # the database for user information
# DB_USER ='db_user'
#
# # the database for audio file record information
# DB_RECORD = 'db_record'
#
# # the database for machine learning feature engineering
# DB_MODEL = 'db_model'

CSRF_ENABLED = True
SECRET_KEY = 'you-will-never-guess'