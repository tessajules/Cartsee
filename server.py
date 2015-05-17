from flask import Flask, render_template, redirect, request, session, jsonify
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
from seed import parse_email_message, add_user, add_order, add_line_item, add_item
from model import Order, OrderLineItem, SavedCartItem, Item, SavedCart, User, db

#5243ad3b37

app = Flask(__name__)

app.secret_key = "ABC"

# login_manager = LoginManager()
# login_manager.init_app(app)




def get_oauth_flow():
    """Instantiates an oauth flow object to acquire credentials to authorize
    app access to user data.  Required to kick off oauth step1"""

    # TODO:  move this into another module...perhaps call it "userauthentication.py"?

    flow = OAuth2WebServerFlow( client_id = os.environ['GMAIL_CLIENT_ID'],
                                client_secret = os.environ['GMAIL_CLIENT_SECRET'],
                                scope = 'https://www.googleapis.com/auth/gmail.readonly',
                                redirect_uri = 'http://127.0.0.1:5000/return-from-oauth/')
    return flow

def build_service(credentials):
    """Instantiates a service object and authorizes it to make API requests"""

    http = httplib2.Http()
    http = credentials.authorize(http)
    service = build('gmail', 'v1', http=http) # build gmail service

    return service

def query_gmail_api_and_seed_db(query, service, credentials):
    """Queries Gmail API for authenticated user information, list of email message ids matching query, and
       email message dictionaries (that contain the raw-formatted messages) matching those message ids"""

   # TODO: need to break this out into two fxns later - also need to move out of server.py

    messages = []

    auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
    user_gmail = auth_user['emailAddress'] # extract user gmail address

    access_token = credentials.access_token

    add_user(user_gmail, access_token) # stores user_gmail and credentials token in database

    response = service.users().messages().list(userId="me", q=query).execute()

    messages.extend(response['messages'])

    for message in messages:

        message = service.users().messages().get(userId="me", id=message['id'], format="raw").execute()

        decoded_message_body = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

        (amazon_fresh_order_id, line_items_one_order,
         delivery_time, delivery_day_of_week, delivery_date) = parse_email_message(decoded_message_body)

        add_order(amazon_fresh_order_id, delivery_date, delivery_day_of_week, delivery_time, user_gmail, line_items_one_order)
            # adds order to database if not already in database
# @app.route('/test')
# def test_template():
#     return render_template("orders_over_time.html")

@app.route('/test1')
def test():
    data = [{"date":"1-May-12","close":"582.13"},
    {"date":"30-Apr-12","close":"583.98"},
    {"date":"27-Apr-12","close":"603.00"},
    {"date":"26-Apr-12","close":"607.70"},
    {"date":"25-Apr-12","close":"610.00"},
    {"date":"24-Apr-12","close":"560.28"},
    {"date":"23-Apr-12","close":"571.70"},
    {"date":"20-Apr-12","close":"572.98"},
    {"date":"19-Apr-12","close":"587.44"},
    {"date":"18-Apr-12","close":"608.34"},
    {"date":"17-Apr-12","close":"609.70"},
    {"date":"16-Apr-12","close":"580.13"},
    {"date":"13-Apr-12","close":"605.23"},
    {"date":"12-Apr-12","close":"622.77"},
    {"date":"11-Apr-12","close":"626.20"},
    {"date":"10-Apr-12","close":"628.44"},
    {"date":"9-Apr-12","close":"636.23"},
    {"date":"5-Apr-12","close":"633.68"},
    {"date":"4-Apr-12","close":"624.31"},
    {"date":"3-Apr-12","close":"629.32"},
    {"date":"2-Apr-12","close":"618.63"},
    {"date":"30-Mar-12","close":"599.55"},
    {"date":"29-Mar-12","close":"609.86"},
    {"date":"28-Mar-12","close":"617.62"},
    {"date":"27-Mar-12","close":"614.48"},
    {"date":"26-Mar-12","close":"606.98"},
    {"date":"23-Mar-12","close":"596.05"},
    {"date":"22-Mar-12","close":"599.34"},
    {"date":"21-Mar-12","close":"602.50"},
    {"date":"20-Mar-12","close":"605.96"},
    {"date":"19-Mar-12","close":"601.10"},
    {"date":"16-Mar-12","close":"585.57"},
    {"date":"15-Mar-12","close":"585.56"},
    {"date":"14-Mar-12","close":"589.58"},
    {"date":"13-Mar-12","close":"568.10"},
    {"date":"12-Mar-12","close":"552.00"},
    {"date":"9-Mar-12","close":"545.17"},
    {"date":"8-Mar-12","close":"541.99"},
    {"date":"7-Mar-12","close":"530.69"},
    {"date":"6-Mar-12","close":"530.26"},
    {"date":"5-Mar-12","close":"533.16"},
    {"date":"2-Mar-12","close":"545.18"},
    {"date":"1-Mar-12","close":"544.47"},
    {"date":"29-Feb-12","close":"542.44"},
    {"date":"28-Feb-12","close":"535.41"},
    {"date":"27-Feb-12","close":"525.76"},
    {"date":"24-Feb-12","close":"522.41"},
    {"date":"23-Feb-12","close":"516.39"},
    {"date":"22-Feb-12","close":"513.04"}]
    # http://bl.ocks.org/d3noob/13a36f70a4f060b97e41
    # return render_template("orders_over_time.html")
    return jsonify(data=data)

@app.route('/')
def landing_page():
    """Renders landing page html template with Google sign-in button
    and demo button"""

    # TODO special Google sign-in button
    # https://developers.google.com/identity/protocols/OpenIDConnect

    return render_template("index.html")

# @login_manager.user_loader
# def load_user(userid):
#     return User.get(userid)

# @app.route('/')
# def landing_page():
#     """Renders landing page html template with Google sign-in button
#     and demo button"""
#
#     # TODO special Google sign-in button
#     # https://developers.google.com/identity/protocols/OpenIDConnect
#
#     return render_template("index.html")


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
        storage = Storage('gmail.storage')
        storage.put(credentials)

        service = build_service(credentials) # instatiates a service object authorized to make API requests

        # TODO: move the query and seed db function out of this route and
        # into the visualization space so that i can make a fancy loading screen
        query = "from: sheldon.jeff@gmail.com subject:AmazonFresh | Delivery Reminder" # should grab all unique orders.
        # Need to change this to amazonfresh email when running from jeff's gmail inbox

        query_gmail_api_and_seed_db(query, service, credentials) # need to break this out into two fxns later

        # TODO: login user using Flask-login library?
        # login_user(user, remember = True)
        # next = flask.request.args.get('next')
        # if not next_is_valid(next):
        #     return flask.abort(400)

        return redirect("/freshlook")

@app.route('/freshlook')
def freshlook():
    """Renders freshlook html template"""

    return render_template("freshlook.html")

@app.route('/list_orders')
def list_orders():
    """Generate json object to list user and order information in browser"""

    storage = Storage('gmail.storage')
    credentials = storage.get()

    service = build_service(credentials)

    auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information

    user = User.query.filter_by(user_gmail=auth_user['emailAddress']).first()

    # this should jsonify list of orders of user.
    # http://stackoverflow.com/questions/21411497/flask-jsonify-a-list-of-objects
    # https://github.com/mitsuhiko/flask/issues/510
    user_orders_json = jsonify(user_gmail=user.user_gmail,
                               orders=[order.serialize() for order in user.orders])
    # orders_json is now a json object in which orders is a list of dictionaries
    # (json objects) with information about each order.

    return user_orders_json

@app.route("/orders_over_time")
def orders_over_time():
    """Generate json object to visualize orders over time using D3"""

    storage = Storage('gmail.storage')
    credentials = storage.get()
    service = build_service(credentials)
    auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
    user = User.query.filter_by(user_gmail=auth_user['emailAddress']).first()


    return jsonify(order_info=user.package_order_date_totals())


##############################################################################
# Helper functions

def connect_to_db(app, db, db_name):
    """Connect the database to Flask app."""

    # Configure to use SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
    db.app = app
    db.init_app(app)

    # if database doesn't exist yet, creates database
    if os.path.isfile(db_name) != True:
        db.create_all()
        print "New database called '%s' created" % db_name

    print "Connected to %s" % db_name



if __name__ == '__main__':

    print "Starting up server."
    connect_to_db(app, db, "freshlook.db") # connects server to database immediately upon starting up

    # debug=True gives us error messages in the browser and also "reloads" our web app
    # if we change the code.
    app.run(debug=True)
    DebugToolbarExtension(app)

    # TODO:
    # 1. figure out d3 visualization data sets & work on building the json data sets for those
8    #     - histogram showing delivery count per day of week (ex most deliveries on Monday)
    # http://www.programmableweb.com/category/food/apis?category=20048
    # 2.  feature I can add to my page: simple order history functionality
    #     - click on "show me me order history"
    #     - go to show me order history page
    #         - this has all the orders information in a table
    #         - click on one of the orders
    #         - the row for that order and the rwo below it split apart (expands).
    #             - all the line items show up there. THIS IS ALL JUST SHOWING AJAX AND JSON (json object list of orders, json object list of items for that order)
    #                 - the api's for getting the orders and the line items should be restful
    #                     - read up on restful and make sure that i'm getting my stuff restful
    #
