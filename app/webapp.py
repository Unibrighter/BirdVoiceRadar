import os
from flask import Flask, request, redirect, url_for, render_template, jsonify
import numpy as np
from BirdSongClassification import BirdSong
import pickle
import pymongo
import couchdb
import hashlib
import random

# # the place to store the uploaded audio files, must be absolute path
# UPLOAD_FOLDER = '/Users/bitmad/msc_project/tmp'
# # the file formats allowed
# ALLOWED_EXTENSIONS = set(['wav'])

'''
Setting up CouchDB connection for latter use in the json communication and duplication removal
'''
couchdb_server = couchdb.Server('https://bitmad:mylife4aiur@localhost:5984/')
# bird_db = couchdb_server['bird']



'''
Config for the flask framework
'''
app = Flask(__name__)
app.config.from_object('config')




'''
The method used to tell if the file uploaded is in the allowed format
takes file name as input
'''
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


'''
The page where allows users to upload new audio file, update machine learning model,
visualise the location on the map
'''
@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            filename_split = filename.split("_")
            lat, lng = filename_split[-3:-1]
            print lat, lng

            birdsong = BirdSong()

            # load stored model and means and inverse standard deviations
            with open('objs.pickle') as f:
                gmm, means, invstds = pickle.load(f)

            # calculate features for the uploaded file and predict
            mfcc_feat1 = birdsong.file_to_features(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            mfcc_feat = (mfcc_feat1 - means) * invstds
            bird_name, confidence = birdsong.predict_one_bird(mfcc_feat, gmm)

            # if confident enough, add feature to the database. The threshold is set manually as 0.7
            if confidence > 0.7:
                features = mfcc_feat1.tolist()
                connection = pymongo.MongoClient("mongodb://localhost")
                # get a handle to the bird database
                db = connection.bird
                birdFeature = db.birdFeature
                count = birdFeature.find().count() + 1
                a_bird = {'_id': bird_name + '_' + str(count), 'feature': features}
                print('Inserted', bird_name + '_' + str(count))
                try:
                    birdFeature.insert_one(a_bird)

                except Exception as e:
                    print "Unexpected error:", type(e), e

            confidence = "{0:.2f}".format(confidence)

            return render_template('bird.html', name=bird_name, confidence=confidence, lat=lat, lng=lng)

    return render_template('bird.html')


'''
This is the url used to update the stored model using the most up-to-date data
'''
@app.route('/update', methods=['GET', 'POST'])
def update():
    birdsong = BirdSong()

    dic = birdsong.get_feature_dic_mongodb("mongodb://localhost")

    allconcat = np.vstack((dic.values()))

    means = np.mean(allconcat, 0)
    invstds = np.std(allconcat, 0)

    for i, val in enumerate(invstds):
        if val == 0.0:
            invstds[i] = 1.0
        else:
            invstds[i] = 1.0 / val

    normedTrain = birdsong.normed_features(dic, means, invstds)
    gmm = birdsong.train_the_model(normedTrain)

    print(len(gmm), 'len gmm')

    list_to_save = [gmm, means, invstds]

    with open('objs.pickle', 'w') as f:
        pickle.dump(list_to_save, f)

    return redirect(url_for('index'))


'''
New added code, this part will use the Flask-Upload Module to deal with the audio file uploading,
and informs the clients about the status of the results by sending a status json back to the clients.
'''
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = file.filename

            # format and long/latitude
            filename_split = filename.split("_")

            # save the record temporary that may goes well the second json latter.
            file_path_on_server=os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # storing to the server's disk complete, now deal with the audio id and Database.
            file.save(file_path_on_server)

            # generate a record in the database
            lat, lng = filename_split[-3:-1]
            print lat, lng

            birdsong = BirdSong()

            # load stored model and means and inverse standard deviations
            with open('objs.pickle') as f:
                gmm, means, invstds = pickle.load(f)

            # calculate features for the uploaded file and predict
            mfcc_feat1 = birdsong.file_to_features(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            mfcc_feat = (mfcc_feat1 - means) * invstds
            bird_name, confidence = birdsong.predict_one_bird(mfcc_feat, gmm)

            # if confident enough, add feature to the database. The threshold is set manually as 0.7
            if confidence > 0.7:
                features = mfcc_feat1.tolist()
                connection = pymongo.MongoClient("mongodb://localhost")
                # get a handle to the bird database
                db = connection.bird
                birdFeature = db.birdFeature
                count = birdFeature.find().count() + 1
                a_bird = {'_id': bird_name + '_' + str(count), 'feature': features}
                print('Inserted', bird_name + '_' + str(count))
                try:
                    birdFeature.insert_one(a_bird)

                except Exception as e:
                    print "Unexpected error:", type(e), e

            confidence = "{0:.2f}".format(confidence)
            return render_template('bird.html', name=bird_name, confidence=confidence, lat=lat, lng=lng)
    return render_template('bird.html')

# '''
# This function breaks the file stored on the disk into chucks at the size of 4096
# and then return the MD5 value of that particular file on the disk
# '''
# def md5(fname):
#     hash_md5 = hashlib.md5()
#     with open(fname, "rb") as f:
#         for chunk in iter(lambda: f.read(4096), b""):
#             hash_md5.update(chunk)
#     return hash_md5.hexdigest()








'''
test_dummy using a generate to generate a json response to the client
'''
@app.route('/upload_audio', methods=['GET', 'POST'])
def upload_audio():
    if request.method == 'POST':
        file = request.files['upload_audio']
        if file and allowed_file(file.filename):
            filename = file.filename

            md5_key = hashlib.md5(file.read()).hexdigest()
            print "file md5 (as id) ", md5_key

            ### *************
            # Now we could search it in CouchDB using this unique md5 id to ensure that the file is unique
            # and if not, then we should return a failure message for the client
            ### *************### *************
            ### *************
            ### *************
            ### *************

            unique_md5_filename=md5_key+"."+filename.rsplit('.', 1)[1]

            # save the record temporary that may goes well the second json latter.
            file_path_on_server=os.path.join(app.config['UPLOAD_FOLDER'], unique_md5_filename)

            # storing to the server's disk complete, now deal with the audio id and Database.
            file.save(file_path_on_server)

            print "file saved as ", unique_md5_filename

            # generate a record in the database
            # using couchdb latter on

            random_result=get_estimation_rank()
            return jsonify({"status":"uploaded","audio_id":md5_key,"estimation_rank":random_result[0],"confident":random_result[1]})
    return render_template('upload_audio.html')

# def check_record_for_existence(md5_id):


# this method should be latter changed into something uses more than random function but the generated model
'''
Need to be changed into the real model estimator latter on
'''
def get_estimation_rank():
    result_dic={}
    confident=False
    for i in range(8):
        result_dic[i]=random.uniform(0.49, 0.82)
        if result_dic[i]>=0.75:
            confident= True
    return result_dic,confident















if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=False)
