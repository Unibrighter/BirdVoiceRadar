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
from time import strftime
from forms import RegisterForm, LoginForm
import wikipedia
from flask import request


@app.route('/test')
def test():
    db_bird = get_db()
    doc_rec = db_bird['24eef7f72e62f4b16e4515c9d80da09e']
    return render_template('record_detail.html', audio_name="Test name", audio_record=doc_rec,
                           wiki_info=get_wiki_info(doc_rec['top_estimation_bird']),
                           bird_dict=get_bird_code_dictionary(),
                           expert_assistance_value=app.config['EXPERT_ASSISTANCE_VAULT'])


'''
This method sets up a connection to the target CouchDB Database
'''


def get_db():
    couch_server = couchdb.Server(app.config['COUCHDB_SERVER'])
    if not hasattr(g, app.config['DB_BIRD']):
        # create the database if not exited
        if app.config['DB_BIRD'] not in couch_server:
            couch_server.create(app.config['DB_BIRD'])
        g.db_bird = couch_server[app.config['DB_BIRD']]
    return g.db_bird


'''
This method return the model that has been trained for further prediction
'''


def get_model():
    model = getattr(g, 'model', None)
    if model is None:
        # load stored model and means and inverse standard deviations
        with open('objs.pickle') as f:
            gmm, means, invstds = pickle.load(f)
            model = g.model = (gmm, means, invstds)
    return g.model


'''
This function will return a dictionary of the results defined by the design view
e.g: get_view_as_dict("account/account_by_email")
'''


def get_view_as_dict(view_name, reduce_input=False):
    db_bird = get_db()
    result_dict = {}
    for row in db_bird.view(view_name, reduce=reduce_input):
        key = row.key
        if type(key) is list:
            key = tuple(key)
        result_dict[key] = row.value
    if not result_dict:
        return None
    else:
        return result_dict


@login_manager.user_loader
def load_user(id):
    # we have specified that id in User Class is actually the unique email we set
    target_user = get_view_as_dict("account/account_by_email")[id]
    return User(email=target_user['email'], username=target_user['username'], password=target_user['password'],
                expert=target_user['expert'], active=True)


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


@app.route("/original", methods=['GET', 'POST'])
@login_required
def original():
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
            rank_list, confidence = birdsong.predict_one_bird(mfcc_feat, gmm)

            bird_name = app.config['BIRD_NAME_LIST'][rank_list[0][0]]

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
    # print request.form
    # print request.headers
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            # print request.headers
            # print request.form

            filename = file.filename
            md5_key = hashlib.md5(file.read()).hexdigest()
            file.seek(0)
            print "file md5 (as id) ", md5_key

            # Now we could search it in CouchDB using this unique md5 id to ensure that the file is unique
            # and if not, then we should return a failure message for the client
            record_dict = get_view_as_dict("account/account_by_email")

            # this json is only used for android and iOS
            response_json = {}

            if md5_key in record_dict.keys():
                # the file already existed, we just return the data we stored in database
                response_json['status'] = "existed"
                # ... need to fill up other response attributes as well

                doc_rec = record_dict[md5_key]


            else:

                bird_db = get_db()

                # no matching md5 record in the database,
                # we need to store the new uploaded file on the disk
                print request.form

                tmp_file_name = request.form['submitted_by'].replace("@", "__at__")
                tmp_file_name = tmp_file_name.replace("%40", "__at__")
                print tmp_file_name
                tmp_file_name = tmp_file_name + strftime("%Y%m%d%H%M%S") + "." + filename.rsplit('.', 1)[1]

                print tmp_file_name

                file_path_on_server = os.path.join(app.config['UPLOAD_FOLDER'], tmp_file_name)

                print file_path_on_server
                # storing to the server's disk complete, now deal with the audio id and Database.
                file.save(file_path_on_server)
                print "file saved as ", tmp_file_name

                # print 'Android' in request.headers.get('User-Agent','Browser')

                doc_rec = {
                    "type": "record",
                    # this is the file label that distinguish the user account information from audio records
                    "training_data": "false",
                    # this boolean tells if a record belongs to training data or user uploaded category
                    "client": request.form['client'],  # here the client could be one of ['browser','android','ios']
                    "file_path": file_path_on_server,
                    "md5": md5_key,
                    "location": request.form['location'],
                    "longitude": request.form['longitude'],
                    "latitude": request.form['latitude'],
                    "evaluation": request.form['evaluation'],
                    "submitted_by": request.form['submitted_by'],
                    "date": request.form['date'],
                    "time": request.form['time'],
                    # "estimation_rank":[],
                    # "confidence": "0.82",
                    # "top_estimation_code":get_bird_code(rec['en']),
                    # "top_estimation_bird":rec['en'], # this could be latter expanded to a more mature json with more information
                    "user_comment": request.form['user_comment'],
                    "expert_request_status": "not",
                    # the request status could one of ['not','pending','classified','completed']
                    "expert_comment": ""
                }

                print doc_rec

                # get the model dummy
                birdsong = BirdSong()
                model = get_model()
                gmm = model[0]
                means = model[1]
                invstds = model[2]

                # calculate features for the uploaded file and predict
                mfcc_feat1 = birdsong.file_to_features(file_path_on_server)
                mfcc_feat = (mfcc_feat1 - means) * invstds
                result_list, confidence = birdsong.predict_one_bird(mfcc_feat, gmm)

                # complete the database doc and store it
                doc_rec["estimation_rank"] = result_list
                doc_rec["confidence"] = confidence
                doc_rec["top_estimation_code"] = result_list[0][0]
                doc_rec["top_estimation_bird"] = app.config["BIRD_NAME_LIST"][doc_rec["top_estimation_code"]]

                static_file_url = get_nginx_url(doc_rec)
                doc_rec["url"] = get_nginx_url(doc_rec)

                # add a new record
                bird_db.save(doc_rec)
                print doc_rec

                wiki_brief = get_wiki_info(doc_rec['top_estimation_bird'])

                # and add some other information into the database as well
                response_json['status'] = "uploaded"
                response_json['estimation_rank'] = result_list
                response_json['confidence'] = confidence
                response_json['bird_code_dictionary'] = get_bird_code_dictionary()
                response_json['md5'] = doc_rec['md5']
                response_json['_id'] = doc_rec['_id']
                response_json['file_url'] = static_file_url
                response_json['wiki_brief'] = wiki_brief

            print "response json!!!!!\n", response_json, "\n!!!!!\n"
            # response differently according to the client
            client = request.form['client']
            if client == 'android' or client == 'iOS':
                # respond to the request by different client
                return jsonify(response_json)
            else:  # broswer
                return render_template('record_detail.html', audio_name=tmp_file_name, audio_record=doc_rec,
                                       wiki_info=get_wiki_info(doc_rec['top_estimation_bird']),
                                       bird_dict=get_bird_code_dictionary(),
                                       expert_assistance_value=app.config['EXPERT_ASSISTANCE_VAULT'])

    return render_template('upload_audio.html')


'''
This route takes care of the registration of a user,
'''


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            register_result = save_register_information(form.username.data, form.email.data, form.password.data,
                                                        form.expert.data)

        else:  # app client deals separately
            if request.form['client'] == 'android' or request.form['client'] == 'iOS':
                register_result = save_register_information(request.form['username'], request.form['email'],
                                                            request.form['password'], request.form['expert'])
                print request.form
        flash(register_result[1])
        # return redirect(url_for('login'))
        return jsonify({"status": register_result[0], "message": register_result[1]})

    return render_template('register.html', title='Register', form=form)


'''
This route takes care of the login of a user,
'''


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        # print request.form
        # print request.headers
        if request.form['client'] == 'android' or request.form['client'] == 'iOS':
            print request.form
            email = request.form['email']
            password = request.form['password']
            status, username = check_account_credentials(email, password)

            print status, username
            return jsonify({"status": status, "username": username})

        if form.validate_on_submit():  # the Browser part
            email = form.email.data
            password = form.password.data
            if check_account_credentials(email, password):  # correct credentials are provided
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


@app.route('/record_detail/<record_id>')
def record_detail(record_id):
    db_bird=get_db()
    doc_rec=db_bird[record_id]
    head, tail = os.path.split(doc_rec['file_path'])
    return render_template('record_detail.html', audio_name=tail, audio_record=doc_rec,
                           wiki_info=get_wiki_info(doc_rec['top_estimation_bird']),
                           bird_dict=get_bird_code_dictionary(),
                           expert_assistance_value=app.config['EXPERT_ASSISTANCE_VAULT'])


'''
This view is used to generate details and set up a index page of all the records
'''


@app.route('/')
@app.route("/index", methods=['GET', 'POST'])
def index():
    # first test whether we are going to serve the entire result or just part of it
    result_list = []
    if request.args.get('view'):
        if request.args.get('view') == 'sub':
            return "under develop"
        else:  # get all records as result

            # Now we could search it in CouchDB using this unique md5 id to ensure that the file is unique
            # and if not, then we should return a failure message for the client
            record_dict = get_view_as_dict("record/all_training_and_upload")
            result_list = record_dict.values()
            # print result_list
            # response differently according to the user clients
            if is_from_mobile_app(request.form.get('client','browser'),request.headers['User-Agent']):
                return jsonify({"record_list":result_list})
            else:
                # from the browser
                # return jsonify({"record_list": result_list})
                return render_template("index.html",audio_record_list=result_list)
    else:
        return "Please do the right parameters!"


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


def get_bird_code(bird_name):
    for i in range(app.config['BIRD_NAME_LIST']):
        if bird_name == app.config['BIRD_NAME_LIST'][i]:
            return i
    # not found
    return -1


def check_account_credentials(email, password):
    user_dict = get_view_as_dict("account/account_by_email")
    if email in user_dict.keys() and password == user_dict[email]['password']:
        return True, user_dict[email]['username']
    return False, None


def get_bird_code_dictionary():
    result_dict = {}
    for i in range(len(app.config['BIRD_NAME_LIST'])):
        result_dict[i] = app.config['BIRD_NAME_LIST'][i]
    return result_dict


def save_register_information(username, email, password, expert):
    tmp_new_user = {
        "type": "account",  # the user information, separated from other docs
        "username": username,
        "email": email,
        "password": password,
        "expert": expert
    }
    print tmp_new_user

    db_bird = get_db()
    # put the new added account information into the DB
    db_bird.save(tmp_new_user)

    print "after save, tmp obj :", tmp_new_user

    user_register_success = True
    response_msg = "A new account has been successfully created!"

    # check if the email is used twice or even more in the database
    email_count = 0
    for row in db_bird.view("account/account_by_email"):
        if row.key == email:
            email_count += 1

    # delete the record if it appears twice or more, and return an error message
    if email_count >= 2:
        db_bird.delete(tmp_new_user)
        response_msg = "The email has been used. Please try again."
        user_register_success = False

    return user_register_success, response_msg


'''
This method is used to generate the static file path in order to play the audio for the app or browser
'''


def get_nginx_url(doc_rec):
    target_url = "http://" + app.config['STATIC_SERVER_IP']
    head, tail = os.path.split(doc_rec['file_path'])
    if doc_rec['training_data'] == 'true':
        target_url = target_url + app.config['STATIC_TRAINING_FILE_PATH'] + tail
    else:  # uploaded by users
        target_url = target_url + app.config['STATIC_UPLOAD_FILE_PATH'] + tail
    return target_url


'''
This is used to draw the info from wikipedia and prepare the page content to display in the detail page page
'''


def get_wiki_info(title):
    page = wikipedia.page(title)
    info = {}
    necessary_image_list = []
    for image in page.images:
        if image.endswith('jpg') or image.endswith('JPG'):
            print image
            necessary_image_list.append(image)
    info['images'] = necessary_image_list
    info['summary'] = page.summary
    return info


def is_from_mobile_app(client,user_agent_str):
    if client == 'iOS' or client == 'android':
        return True

    user_agent_str = user_agent_str.lower()
    print user_agent_str
    if 'android' in user_agent_str or 'ios' in user_agent_str:
        return True
    return False
