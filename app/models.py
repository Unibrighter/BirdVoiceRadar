import flask_login

'''
This class is used for represent account about which the users provide credential information
The sole purpose of this class is to maintain the instance of a user for login function
'''


class User(flask_login.UserMixin):
    def __init__(self, email, username, password, expert=False, active=True):
        self.id = email  # now this attribute is used for login function support only
        self.email = email
        self.username = username
        self.password = password
        self.expert = expert
        self.active = active

    def is_active(self):
        # Here you should write whatever the code is
        # that checks the database if your user is active
        return self.active

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True
