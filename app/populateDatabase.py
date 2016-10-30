from glob import glob
import os
import sys
from BirdSongClassification import BirdSong
sys.path.insert(0,'..')
import config
import couchdb

'''
Run this code to store features into the database
'''

# def populate_database(mongo_path,trainingDataPath):
#     connection = pymongo.MongoClient(mongo_path)
#     # get a handle to the bird database
#     db = connection.bird
#     birdFeature = db.birdFeature
#
#     bird = BirdSong()
#     files_list = glob(os.path.join(trainingDataPath, '*.wav'))
#     for a_file in files_list:
#         features = bird.file_to_features(a_file).tolist()
#         a_bird = {'_id': a_file, 'feature': features}
#         try:
#             birdFeature.insert_one(a_bird)
#
#         except Exception as e:
#             print "Unexpected error:", type(e), e
#
#
# #Populate the birdFeature collection in the bird database with files from wav folder
# populate_database("mongodb://localhost",'wav')

'''
This code is designed to initialize the database for the latter use
'''
def initialize_couchdb(couchdb_path,training_data_path):
    couchdb_server=couchdb.Server(couchdb_path)

def populate_database(trainingDataPath):
    couch_server = couchdb.Server(config.COUCHDB_SERVER)
    db_bird = couch_server[config.DB_WAV]
    bird = BirdSong()
    files_list = glob(os.path.join(trainingDataPath, '*.wav'))
    avg_distance=None
    for a_file in files_list:
        if (True):
            result=bird.file_to_features(a_file,True)
            feature_list=result[0]
            avg_distance=result[1]
        else:
            feature_list=bird.file_to_features(a_file)

        features = feature_list.tolist()
        a_bird = {'file_path': a_file, 'feature': features,'avg_peak_distance':avg_distance}
        try:
            db_bird.save(a_bird)
            print a_bird['file_path'], " done!"

        except Exception as e:
            print "Unexpected error:", type(e), e


#Populate the birdFeature collection in the bird database with files from wav folder
# the input should follow the pattern like "python populateDatabase.py /home/Ubuntu"

wav_path=sys.argv[1]

populate_database(wav_path)



