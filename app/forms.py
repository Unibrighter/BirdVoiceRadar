from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField ,PasswordField
from wtforms.validators import DataRequired,Email,Length

# '''
# This method checks if the email already exist in the database
# '''
# def my_length_check(form, field):
#     check db_view , find key value.

class RegisterForm(FlaskForm):
    # def __init__(self,db_connection):
    #     Form.__init__(self)
    #     self.db_connection=db_connection

    # must follow the format of an email
    email=StringField('email',validators=[Email()])

    # User name
    username=StringField('username',validators=[DataRequired(),Length(-1,32)])

    # password
    password = PasswordField('password', validators=[DataRequired(),Length(6,32)])

    # expert
    expert = BooleanField('expert', default=False)


'''
This form is used for login the user
'''
class LoginForm(FlaskForm):
    # def __init__(self,db_connection):
    #     Form.__init__(self)
    #     self.db_connection=db_connection

    # must follow the format of an email
    email=StringField('email',validators=[Email()])

    # password
    password = PasswordField('password', validators=[DataRequired(),Length(6,32)])

    # remember_me
    remember_me = BooleanField('remember_me', default=False)

