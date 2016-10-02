from glob import glob
import os
from BirdSongClassification import BirdSong
#import pymongo
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





