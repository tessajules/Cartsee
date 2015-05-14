from flask import Flask, render_template, redirect, request, session
from oauth2client.client import OAuth2WebServerFlow
import httplib2 # used in login_callback()
from apiclient.discovery import build
import apiclient # used in login_callback()
import os # to get gmail client secrets from os.environ
from oauth2client.file import Storage # used in login_callback()
# from flask.ext.login import LoginManager, login_user, logout_user, current_user
import base64
import email
from apiclient import errors
from seed import parse_email_message #, store_user



app = Flask(__name__)

app.secret_key = "ABC"

# login_manager = LoginManager()
# login_manager.init_app(app)


def get_oauth_flow():
    """Instantiates an oauth flow object to acquire credentials to authorize
    app access to user data.  Required to kick off oauth step1"""

    flow = OAuth2WebServerFlow( client_id = os.environ['GMAIL_CLIENT_ID'],
                                client_secret = os.environ['GMAIL_CLIENT_SECRET'],
                                scope = 'https://www.googleapis.com/auth/gmail.readonly',
                                redirect_uri = 'http://127.0.0.1:5000/return-from-oauth/')
    return flow


@app.route('/')
def landing_page():
    """Renders landing page html template with Google sign-in button
    and demo button"""

    # TODO special Google sign-in button
    # https://developers.google.com/identity/protocols/OpenIDConnect

    return 'This is the landing page.  <html><body><a href="/login/">Login</a></body></html>'

# @login_manager.user_loader
# def load_user(userid):
#     return User.get(userid)


@app.route('/login/')
def login():
    """OAuth step1 kick off - redirects user to auth_uri on app platform"""

    # TODO if user already authenticated, redirect to ???
    # If user already authenticated, do I need to use AccessTokenCredentials here?
    # To quote the oauth python docs, 'The oauth2client.client.AccessTokenCredentials class
    # is used when you have already obtained an access token by some other means.
    # You can create this object directly without using a Flow object.'
    # https://developers.google.com/api-client-library/python/guide/aaa_oauth#oauth2client

    auth_uri = get_oauth_flow().step1_get_authorize_url()

    return redirect(auth_uri)

@app.route('/return-from-oauth/')
def login_callback():
    """This is the auth_uri.  User redirected here after OAuth step1.
    Here the authorization code obtained when user gives app permissions
    is exchanged for a credentials object"""

    # TODO if user declines authentication, redirect to landing page

    code = request.args.get('code') # the authorization code 'code' is the query
                                    # string parameter
    if code == None:
        print "code = None"
        return redirect('/')

    else:

        credentials = get_oauth_flow().step2_exchange(code)

        http = httplib2.Http()
        http = credentials.authorize(http)

        access_token = credentials.access_token

        service = build('gmail', 'v1', http=http) # build gmail service

        gmail_user = service.users().getProfile(userId = 'me').execute()

        user_gmail = gmail_user['emailAddress']

        # store_user(user_gmail, access_token)

        storage = Storage('gmail.storage') # TODO: make sure parameter is correct

        storage.put(credentials) # find a more permanent way to store credentials.  user database

        # TODO:  grab credentials.access_token and add to a database


        credentials = storage.get()

        messages = []

        query = "from: sheldon.jeff@gmail.com subject:AmazonFresh | Delivery Reminder" # should grab all unique orders.  Need to change this to amazonfresh email
        # when running from jeff's gmail inbox

        response = service.users().messages().list(userId="me", q=query).execute()

        messages.extend(response['messages'])

        for message in messages:

            message = service.users().messages().get(userId="me", id=message['id'], format="raw").execute()

            decoded_message_body = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

            (order_number_string, line_items_one_order,
             delivery_time, delivery_day_of_week, delivery_date) = parse_email_message(decoded_message_body)

             # TODO: add all these to databases.

            print "~" * 20
            print order_number_string
            print delivery_time
            print delivery_day_of_week
            print delivery_date
            print line_items_one_order
            print "~" * 20



        # TODO: login user using Flask-login library

        # login_user(user, remember = True)

        # next = flask.request.args.get('next')
        # if not next_is_valid(next):
        #     return flask.abort(400)

        return "blah"


@app.route('/visualization/')
def visualize():
    """Visualize cart data here"""

    return "Here's where I will visualize the data"



if __name__ == '__main__':
    # debug=True gives us error messages in the browser and also "reloads" our web app
    # if we change the code.
    app.run(debug=True)
    DebugToolbarExtension(app)
