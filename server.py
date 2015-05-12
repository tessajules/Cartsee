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
import re



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

def parse_test(string):
    """Test of regex parsing of message string"""
    # return re.search('FULFILLED AS ORDERED.*Subtotal:', string, re.DOTALL).group(0)
    # return re.search('FULFILLED AS ORDERED \*\*\*\r.*\nSubtotal:', string, re.DOTALL).group(0)
    order_string = re.search('FULFILLED AS ORDERED \*\*\*\r.*\r\n\r\nSubtotal:', string, re.DOTALL).group(0)
    # this helped:  http://regexadvice.com/forums/thread/50111.aspx
    # needed to rule out the weirdly formatted html strings also coming out.  These ended in <br>\r\nSubtotal

    order_parser = re.compile(r'\r\n\r\n')
    line_items_list = order_parser.split(order_string) # splits block of items from one order into lists of line items

    # https://docs.python.org/2/howto/regex.html
    # split_line_items = [] # this will end up being a list of lists
    line_item_parser = re.compile(r'\s{3,}')

    for line_item in line_items_list: # iterate through list of line items from one order
        # print line_item
        stripped_line_item = line_item.strip()
        line_item_info_list = line_item_parser.split(stripped_line_item)
        print line_item_info_list
            # split the list of line items from one order into list of qty, qty, price, description
            # and append to split_line_items.  split_line_items is now a list of lists.
    return line_items_list # return a list of (lists of line item info) from one order.


    # return line_items_list # returns list of line items from one order


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

        # print "()()()()()() CODE: ", code

        credentials = get_oauth_flow().step2_exchange(code)

        # print "()()()()()() CREDENTIALS: ", credentials

        http = httplib2.Http()
        http = credentials.authorize(http)

        # print "()()()()()() HTTP: ", http


        service = build('gmail', 'v1', http=http) # build gmail service
        # TODO: make sure parameters 'gmail' and 'v1' correct
        # really confused as to what's going on here. I grabbed this code from
        # https://developers.google.com/gmail/api/quickstart/quickstart-python
        # and I'm not sure if these paramaters are correct for what i want.

        # print "()()()()()() SERVICE: ", service

        # here is where I access the gmail api.

        gmail_user = service.users().getProfile(userId = 'me').execute()


        # print "()()()()()() GMAIL USER: ", gmail_user

        # email = gmail_user['emailAddress']
        # print "()()()()()() EMAIL: ", email

        messages = []
        # unparsed_test_strings = [] # THIS EXISTS FOR TESTING ONLY
        line_items_lists = []

        query = "from: sheldon.jeff@gmail.com subject:AmazonFresh | Delivery Reminder" # should grab all unique orders.  Need to change this to amazonfresh email
        # when running from jeff's gmail inbox
        response = service.users().messages().list(userId="me", q=query).execute()

        messages.extend(response['messages'])
        # print "()()()()()() MESSAGES: ", messages

        for message in messages:
            message = service.users().messages().get(userId="me", id=message['id'], format="raw").execute()
            # import pdb
            # pdb.set_trace()
            # payload= str(message['payload']['body'])
            decoded_message_body = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
            # message_strings.append(payload)
            # message_strings.append(decoded_message_body)
            # unparsed_test_strings.append(decoded_message_body)
            line_items_lists.append(parse_test(decoded_message_body))

        # print "~~~~~~~~~~~~~~~~~~~~~~~NEW-EMAIL~~~~~~~~~~~~~~~~~~~~~~~~".join(unparsed_test_strings)
        # print "~~~~~~~~~~~~~~~~~~~~~~~NEW-EMAIL~~~~~~~~~~~~~~~~~~~~~~~~".join(parse_test_strings)

        # for testing only ####
        # test_lines = []
        # for order in line_items_lists:
        #     for line_item in order:
        #         test_lines.append(line_item)
        #         print "~~~~~~~~~~"
        #         print line_item
        # #####
        #
        #
        # for split_line_items in line_items_lists:
        #     for line_item in split_line_items:
        #         print "~~~~~~~~~~"
        #         print line_item





        # import pdb
        # pdb.set_trace()
        # test_msg = " ".join(message_strings)

        # print test_msg
        ### end of testing only code

        storage = Storage('gmail.storage') # TODO: make sure parameter is correct

        storage.put(credentials) # find a more permanent way to store credentials.  user database

        access_token = credentials.access_token
        # print  "()()()()()() ACCESS TOKEN: ", access_token


        # TODO:  grab credentials.access_token and add to a database

        # print "()()()()()() STORAGE is storing credentials: ", storage

        credentials = storage.get() # not sure this goes here
        # print "()()()()()() CREDENTIALS RETRIEVED FROM STORAGE."
        # print "()()()()()() RETRIEVED CREDENTIALS: ", credentials

        # TODO: login user using Flask-login library

        # login_user(user, remember = True)

        # next = flask.request.args.get('next')
        # if not next_is_valid(next):
        #     return flask.abort(400)

        # print "()()()()()() REDIRECTING TO /visualization/"

        # return parse_test(test_msg)

        return "blah"
        # return "~~~~~~~~~~~~~~~~~~~~~~~NEW-EMAIL~~~~~~~~~~~~~~~~~~~~~~~~".join(parse_test_strings)
        # return test_msg # temporary return value for testing
        # return ("<br>~~~~<br>").join(test_lines)


@app.route('/visualization/')
def visualize():
    """Visualize cart data here"""

    return "Here's where I will visualize the data"

if __name__ == '__main__':
    # debug=True gives us error messages in the browser and also "reloads" our web app
    # if we change the code.
    app.run(debug=True)
    DebugToolbarExtension(app)
