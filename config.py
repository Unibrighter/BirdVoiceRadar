import os

# the place to store the uploaded audio files
# here the upload directory should be at the same level of config file
# UPLOAD_FOLDER = "../tmp"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__) + '/tmp')

# the place to store the training data downloaded from xeno_canto
TRAINING_FILE_FOLDER=os.path.join(os.path.dirname(__file__) + '/training_file/')

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

BIRD_NAME_LIST=[
    'Brush Cuckoo','Australian Golden Whistler','Eastern Whipbird','Grey Shrikethrush','Pied Currawong',
           'Southern Boobook','Spangled Drongo','Willie Wagtail']

BIRD_DOWNLOAD_LIST=[
    'Brush%20Cuckoo','Australian%20Golden%20Whistler','Eastern%20Whipbird','Grey%20Shrikethrush','Pied%20Currawong',
           'Southern%20Boobook','Spangled%20Drongo','Willie%20Wagtail']