from flask import Flask, render_template, redirect, request, session, jsonify, Response
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
import json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
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

        message = service.users().messages().get(userId="me",
                                                 id=message['id'],
                                                 format="raw").execute()

        decoded_message_body = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

        (amazon_fresh_order_id, line_items_one_order,
         delivery_time, delivery_day_of_week, delivery_date) = parse_email_message(decoded_message_body)

        add_order(amazon_fresh_order_id, delivery_date, delivery_day_of_week, delivery_time, user_gmail, line_items_one_order)
            # adds order to database if not already in database
# @app.route('/test')
# def test_template():
#     return render_template("orders_over_time.html")

@app.route('/items_by_qty')
def items_by_qty():
    """Generate json object from list of items user bought to visualize item clusters using D3"""

    storage = Storage('gmail.storage')
    credentials = storage.get()
    service = build_service(credentials)
    auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information

    item_list = db.session.query(Item.description,
                                 func.sum(OrderLineItem.quantity),
                                 func.max(OrderLineItem.unit_price_cents)).join(
                                 OrderLineItem).join(Order).filter(
                                 Order.user_gmail==auth_user['emailAddress']).group_by(
                                 Item.item_id).all()

    price_map = {}

    for item_tup in item_list:

        description, quantity, unit_price_cents = item_tup
        if description.count(",") >= 1:
            description = " ".join(description.split(", ")[:-1])

        unit_price = float(unit_price_cents)/100
        unit_price_str = "$%.2f" % unit_price

        if unit_price > 30:
            price_map.setdefault("> $30", [])
            price_map["> $30"].append((description, quantity, unit_price_str))
        elif unit_price <= 30 and unit_price > 25:
            price_map.setdefault("<= $30 and > $25", [])
            price_map["<= $30 and > $25"].append((description, quantity, unit_price_str))
        elif unit_price <= 25 and unit_price > 20:
            price_map.setdefault("<= $25 and > $20", [])
            price_map["<= $25 and > $20"].append((description, quantity, unit_price_str))
        elif unit_price <= 20 and unit_price > 15:
            price_map.setdefault("<= $20 and > $15", [])
            price_map["<= $20 and > $15"].append((description, quantity, unit_price_str))
        elif unit_price <= 15 and unit_price > 10:
            price_map.setdefault("<= $15 and > $10", [])
            price_map["<= $15 and > $10"].append((description, quantity, unit_price_str))
        elif unit_price <= 10 and unit_price > 5:
            price_map.setdefault("<= $10 and > $5", [])
            price_map["<= $10 and > $5"].append((description, quantity, unit_price_str))
        else:
            price_map.setdefault("<= $5", [])
            price_map["<= $5"].append((description, quantity, unit_price_str))

    children = []

    price_range_list = ["> $30", "<= $30 and > $25", "<= $25 and > $20",
                        "<= $15 and > $10", "<= $10 and > $5", "<= $5"]
    price_range_actual = []

    for price_range in price_range_list:
        if price_range in price_map.keys():
            price_range_actual.append(price_range)

    print price_range_actual

    for price_range in price_range_actual:

        cluster =  {"name": price_range, "children": []}

        for item_tup in price_map[price_range]:
            cluster["children"].append({"name": item_tup[0] + ", " + item_tup[2], "quantity": item_tup[1]})

        children.append(cluster)

    return jsonify({"name": "unit price clusters", "children": children})

@app.route('/test1')
def test():



    x = {
     "name": "unit price clusters",
     "children": [
        {
         "name": "$30+",
         "children": [
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 1},
          {"name": "Ruffles Ruffles Potato Chips, Party quantity Original, 14.5 Oz, 14.5 Oz", "quantity": 1},
         ]
        },
        {
         "name": "$25-30",
         "children": [
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 2},
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 2},
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 3},
         ]
        },
        {
         "name": "$20-25",
         "children": [
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 3},
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 3},
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 4},

         ]
        },
        {
         "name": "$15-20",
         "children": [
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 4},
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 4},
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 4},
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 5},

         ]
        },
        {
         "name": "$10-15",
         "children": [
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 6},
          {"name": "LinkDistance", "quantity": 6},
          {"name": "MaxFlowMinCut", "quantity": 7},
          {"name": "ShortestPaths", "quantity": 6},
          {"name": "SpanningTree", "quantity": 6}
         ]
        },
        {
         "name": "$5-10",
         "children": [
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 20},
          {"name": "LinkDistance", "quantity": 30},
          {"name": "MaxFlowMinCut", "quantity": 10},
          {"name": "ShortestPaths", "quantity": 10},
          {"name": "SpanningTree", "quantity": 10},
        {"name": "BetweennessCentrality", "quantity": 20},
        {"name": "LinkDistance", "quantity": 20},
        {"name": "MaxFlowMinCut", "quantity": 20},
        {"name": "ShortestPaths", "quantity": 30},
        {"name": "SpanningTree", "quantity": 20}
         ]
        },
        {
         "name": "<$5",
         "children": [
          {"name": "Ruffles Ruffles Potato Chips, Party Size Original, 14.5 Oz, 14.5 Oz", "quantity": 40},
          {"name": "LinkDistance", "quantity": 40},
          {"name": "MaxFlowMinCut", "quantity": 30},
          {"name": "ShortestPaths", "quantity": 44},
          {"name": "SpanningTree", "quantity": 40},
          {"name": "BetweennessCentrality", "quantity": 50},
          {"name": "LinkDistance", "quantity": 50},
          {"name": "MaxFlowMinCut", "quantity": 50},
          {"name": "ShortestPaths", "quantity": 50},
          {"name": "SpanningTree", "quantity": 50},
          {"name": "BetweennessCentrality", "quantity": 50},
          {"name": "LinkDistance", "quantity": 50}
         ]
        }
     ]
    }

    # http://bl.ocks.org/d3noob/13a36f70a4f060b97e41
    return jsonify(x)

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


    return jsonify(data=user.serialize_orders_for_area_chart())
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
    #     - histogram showing delivery count per day of week (ex most deliveries on Monday)
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
