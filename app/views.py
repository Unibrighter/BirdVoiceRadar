import os
from flask import Flask, request, redirect, url_for, render_template, jsonify, g, flash
import numpy as np
from BirdSongClassification import BirdSong
import pickle
import pymongo
import hashlib
import random
from app import app, login_manager
from flask_login import login_user, logout_user, current_user, login_required
from models import User
import couchdb

from forms import RegisterForm, LoginForm


# '''
# This method set up connection for CouchDB database
# '''
# def connect_db(db_name):
#     target_db = None
#     couch_server = couchdb.Server(app.config['COUCHDB_SERVER'])
#     db_list = [app.config('DB_USER'), app.config('DB_RECORD'), app.config('DB_MODEL')]
#     if db_name in db_list:
#         target_db = couch_server.get_or_create_db(db_name)
#     return target_db
#
#
# def get_db(db_name):
#     if db_name == app.config('DB_USER') and not hasattr(g, app.config('DB_USER')):
#         g.db_user = connect_db(app.app.config('DB_USER'))
#         return g.db_user
#     if db_name == app.config('DB_RECORD') and not hasattr(g, app.config('DB_RECORD')):
#         g.db_record = connect_db(app.app.config('DB_RECORD'))
#         return g.db_record
#     if db_name == app.config('DB_MODEL') and not hasattr(g, app.config('DB_MODEL')):
#         g.db_model = connect_db(app.app.config('DB_MODEL'))
#         return g.db_model

def get_db():
    couch_server = couchdb.Server(app.config['COUCHDB_SERVER'])
    if not hasattr(g, app.config['DB_BIRD']):
        # create the database if not exited
        if app.config['DB_BIRD'] not in couch_server:
            couch_server.create(app.config['DB_BIRD'])
        g.db_bird = couch_server[app.config['DB_BIRD']]
    return g.db_bird

'''
This function will return a dictionary of users with doc content as value and email as key
'''
def get_user_dict():
    db_bird = get_db()
    user_dict = {}
    for row in db_bird.view("account/account_by_email"):
        user_dict[row.key] = row.value
    if not user_dict:
        return None
    else:
        return user_dict

@login_manager.user_loader
def load_user(id):
    # we have specified that id in User Class is actually the unique email we set
    target_user = get_user_dict()[id]
    return User(email=target_user['email'], username=target_user['username'], password=target_user['password'],expert=target_user['expert'], active=True)


@app.before_request
def before_request():
    g.user = current_user


'''
The method used to tell if the file uploaded is in the allowed format
takes file name as input
'''


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


'''
The page where allows users to upload new audio file, update machine learning model,
visualise the location on the map
'''

@app.route("/", methods=['GET', 'POST'])
@app.route("/index", methods=['GET', 'POST'])
@login_required
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
            file_path_on_server = os.path.join(app.config['UPLOAD_FOLDER'], filename)

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
        print request
        file = request.files['bird_audio']
        print file
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

            unique_md5_filename = md5_key + "." + filename.rsplit('.', 1)[1]

            # save the record temporary that may goes well the second json latter.
            file_path_on_server = os.path.join(app.config['UPLOAD_FOLDER'], unique_md5_filename)

            # storing to the server's disk complete, now deal with the audio id and Database.
            file.save(file_path_on_server)

            print "file saved as ", unique_md5_filename

            # generate a record in the database
            # using couchdb latter on

            random_result = get_estimation_rank()
            return jsonify({"status": "uploaded", "audio_id": md5_key, "estimation_rank": random_result[0],
                            "confident": random_result[1]})
    return render_template('upload_audio.html')


'''
This route takes care of the registration of a user,
'''


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        # now we are going to handle the uniqueness of email address of user account
        db_bird = get_db()

        tmp_new_user = {
            "type": "account",  # the user information, separated from other docs
            "username": form.username.data,
            "email": form.email.data,
            "password": form.password.data,
            "expert": form.expert.data
        }

        print tmp_new_user

        # put the new added account information into the DB
        db_bird.save(tmp_new_user)

        print "after save, tmp obj :", tmp_new_user

        # check if the email is used twice or even more in the database
        email_count = 0
        for row in db_bird.view("account/account_by_email"):
            if row.key == form.email.data:
                email_count += 1

        # delete the record if it appears twice or more, and return an error message
        if email_count >= 2:
            db_bird.delete(tmp_new_user)
            flash("The email has been used. Please try again.")

        flash("A new account has been successfully created!")
        # return redirect(url_for('login'))
        return "Successfully created a new user!"
    return render_template('register.html', title='Register', form=form)


'''
This route takes care of the login of a user,
'''
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method =='POST' and form.validate_on_submit():
        email=form.email.data
        password=form.password.data
        user_dict=get_user_dict()
        if email in user_dict.keys() and password==user_dict[email]['password']: # correct credentials are provided
            remember_me = request.form.get("remember_me", "False") == "True"
            if login_user(load_user(email), remember=remember_me):
                flash("Logged in!")
                return redirect(url_for("index"))
            else:
                flash("Sorry, but you could not log in.")
        else:
            flash("Invalid username or password.")

    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))



# this method should be latter changed into something uses more than random function but the generated model
'''
Need to be changed into the real model estimator latter on
'''
def get_estimation_rank():
    result_dic = {}
    confident = False
    for i in range(8):
        result_dic[i] = random.uniform(0.49, 0.82)
        if result_dic[i] >= 0.75:
            confident = True
    return result_dic, confident
