from flask import Flask, request, redirect, url_for, render_template, jsonify, g
from BirdSongClassification import BirdSong
from flask_login import LoginManager


'''
Config for the flask framework
'''
app = Flask(__name__)
app.config.from_object('config')


'''
Get the login part working for the system
'''
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view='login'


# this import statement can't be placed in the head of the file
# otherwise it becomes a loop reference for itself, which causes exception
from app import views
