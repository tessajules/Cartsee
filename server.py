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
from model import Order, OrderLineItem, SavedCartItem, Item, SavedCart, User, db, Message
import json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sys import argv
import time
import gevent
import logging
from flask.ext.socketio import SocketIO, emit
from datetime import datetime
import math

logging.basicConfig(filename='server.log',level=logging.DEBUG)

app = Flask(__name__)
# monkey.patch_all()
app.secret_key = "ABC"
socketio = SocketIO(app)

# login_manager = LoginManager()
# login_manager.init_app(app)

DEMO_GMAIL = "acastanieto@gmail.com"
CREATE_DEMO = False



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

    user = User.query.filter_by(user_gmail=user_gmail).one()

    message_ids = [message_obj.message_id for message_obj in user.messages]

    if CREATE_DEMO:
    # updates the demo file
        demo_file = open("demo.txt", "w")

    running_total = 0
    running_quantity = 0
    total_num_orders = len(messages)
    num_orders = 0

    for message in messages:

        if message['id'] not in message_ids:

            new_message = Message(message_id=message['id'], user_gmail = user_gmail)

            db.session.add(new_message)

            message = service.users().messages().get(userId="me",
                                                     id=message['id'],
                                                     format="raw").execute()


            decoded_message_body = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

            if "Doorstep Delivery" not in decoded_message_body:
                total_num_orders -= 1

            else:

                if CREATE_DEMO:
                    demo_file.write(message["raw"] + "\n")


                (amazon_fresh_order_id, line_items_one_order,
                 delivery_time, delivery_day_of_week, delivery_date) = parse_email_message(decoded_message_body)

                add_order(amazon_fresh_order_id, delivery_date, delivery_day_of_week, delivery_time, user_gmail, line_items_one_order)
                    # adds order to database if not already in database

                order = Order.query.filter_by(amazon_fresh_order_id=amazon_fresh_order_id).one()

                order_total = order.calc_order_total()
                order_quantity = order.calc_order_quantity()
                num_orders += 1


                emit('my response', {'order_total': running_total,
                                     'quantity': running_quantity,
                                     'num_orders': num_orders,
                                     'total_num_orders': total_num_orders,
                                     'status': 'loading'
                })

                running_total += order_total
                running_quantity += order_quantity
                gevent.sleep(.1)

                print "Message", message['id'], "order information parsed and added to database"
        else:
            print "Message", message['id'], "order information already in database."

    if CREATE_DEMO:
        demo_file.close()

    db.session.commit()

    emit('my response', {'order_total': running_total,
                         'quantity': running_quantity,
                         'num_orders': num_orders,
                         'total_num_orders': total_num_orders,
                         'status': 'done'})

@app.route('/items_by_qty')
def items_by_qty():
    """Generate json object from list of items user bought to visualize item clusters using D3"""

    if session.get("demo_gmail", []):
        email = session["demo_gmail"]
    elif session.get("logged_in_gmail", []):
        email = session["logged_in_gmail"]
    else:
        storage = Storage('gmail.storage')
        credentials = storage.get()
        service = build_service(credentials)
        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
        email = auth_user['emailAddress']

    item_list = db.session.query(Item.description,
                                 func.sum(OrderLineItem.quantity),
                                 func.max(OrderLineItem.unit_price_cents)).join(
                                 OrderLineItem).join(Order).filter(
                                 Order.user_gmail==email).group_by(
                                 Item.item_id).all()

    bottom_price = int(request.args.get("bottom_price", 0))
    top_price = int(request.args.get("top_price", 1000000000))
    bottom_qty = int(request.args.get("bottom_qty", 0))
    top_qty = int(request.args.get("top_qty", 100000000000))


    price_map = {} # making price map so don't need to iterate over item_list more than
                   # once (it will likely be a huge list)

    max_price = 0
    max_qty = 0

    for item_tup in item_list:

        description, quantity, unit_price_cents = item_tup
        if description.count(",") >= 1: # if description has at least one comma in it
            description = " ".join(description.split(", ")[:-1]) # get rid of the the last thing separated by comma

        unit_price = float(unit_price_cents)/100
        unit_price_str = "$%.2f" % unit_price


        if unit_price > max_price:
            max_price = unit_price

        if quantity > max_qty:
            max_qty = quantity

        if unit_price >= bottom_price and unit_price <= top_price and quantity >= bottom_qty and quantity <= top_qty:
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
    # This used to ensure that the items clustered by price range will show up in
    # a certain order


    price_range_actual = []

    for price_range in price_range_list:
        if price_range in price_map.keys():
            price_range_actual.append(price_range)
            # since some price ranges might not end up being represented in the
            # actual user data, price_range_actual will be generated with the
            # price ranges actually represented in user data

            # TODO: can I use dict.get() above or does it not make sense here?
    for price_range in price_range_actual:

        cluster =  {"name": price_range, "children": []}

        for item_tup in price_map[price_range]:
            cluster["children"].append({"name": item_tup[0] + ", "
                                        + item_tup[2], "quantity": item_tup[1]})

        children.append(cluster)

    if not children:
        return "stop"

    return jsonify({"name": "unit price clusters",
                    "children": children,
                    "max_price": max_price,
                    "max_qty": max_qty})

@app.route('/saved_cart')
def get_saved_cart():
    """Generate json object with items in saved cart, if one exists, to display
    on main prediction page when first land on it"""

    if session.get("demo_gmail", []):
        email = session["demo_gmail"]
    elif session.get("logged_in_gmail", []):
        email = session["logged_in_gmail"]
    else:
        storage = Storage('gmail.storage')
        credentials = storage.get()
        service = build_service(credentials)
        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
        email = auth_user['emailAddress']

    saved_cart = SavedCart.query.filter_by(user_gmail=email).first()

    if saved_cart:
        saved_items = saved_cart.items
        saved_cart = []
        for item_obj in saved_items:
            saved_cart.append({   "item_id": item_obj.item_id,
                            "description": item_obj.description,
                            "unit_price": item_obj.get_last_price() })

        return jsonify(saved_cart=saved_cart)

    else:
        return jsonify(saved_cart=[])



@app.route('/predict_cart', methods = ["GET"])
def predict_cart():
    """Generate json object with items predicted to be in next order to populate predicted cart"""

    if session.get("demo_gmail", []):
        email = session["demo_gmail"]
    elif session.get("logged_in_gmail", []):
        email = session["logged_in_gmail"]
    else:
        storage = Storage('gmail.storage')
        credentials = storage.get()
        service = build_service(credentials)
        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
        email = auth_user['emailAddress']

    user = User.query.filter_by(user_gmail=email).one()

    date_str = request.args.get("cart_date")
    keep_saved = request.args.get("keep_saved", None)

    # using 0 as False and 1 as True here, because that's what I can pass from user input easily

    #TODO:  show saved cart (if any) in browser before predict cart

    all_cart_objs, cart_qty = user.predict_cart(date_str) # list of all item objects from
    # cart prediction algorithm, and quantity cutoff for predicted cart

    # automatically makes new saved cart, or checks if one exists for that user,
    # and adds primary cart items to that saved cart

    saved_cart = SavedCart.query.filter_by(user_gmail=email).first()

    if not saved_cart:
        saved_cart = SavedCart(user_gmail=email)
        db.session.add(saved_cart)
        db.session.commit()

    if not keep_saved:
        for item_obj in saved_cart.items:
            saved_cart_item = SavedCartItem.query.filter_by(item_id=item_obj.item_id,
                                                            saved_cart_id=saved_cart.saved_cart_id).one()
            db.session.delete(saved_cart_item)
        db.session.commit()

    updated_contents = []

    # take out any items in predicted cart that are already in saved cart
    for item_obj in all_cart_objs:
        if item_obj not in saved_cart.items:
            updated_contents.append(item_obj)



    # update the # of spaces left in primary_cart when factor in saved cart items
    updated_cart_qty = cart_qty - len(saved_cart.items)
    if updated_cart_qty < 0:
        updated_cart_qty = 0


    primary_cart_objs = updated_contents[:updated_cart_qty]
    backup_cart_objs = updated_contents[updated_cart_qty:]

    primary_cart = []
    backup_cart = []

    # make list of primary cart item dicts to display
    for item_obj in primary_cart_objs:
        primary_cart.append({   "item_id": item_obj.item_id,
                        "description": item_obj.description,
                        "unit_price": item_obj.get_last_price() })

    # make list of backup cart item dicts to display
    for item_obj in backup_cart_objs:
        backup_cart.append({   "item_id": item_obj.item_id,
                        "description": item_obj.description,
                        "unit_price": item_obj.get_last_price() })

    # add the new primary cart items to the saved cart
    for item_obj in primary_cart_objs:
        saved_cart_item = SavedCartItem(item_id=item_obj.item_id,
                                        saved_cart_id=saved_cart.saved_cart_id)
        db.session.add(saved_cart_item)
    db.session.commit()


    return jsonify(primary_cart=primary_cart, backup_cart=backup_cart)

@app.route('/add_item', methods = ["POST"])
def add_item_to_saved():
    """Adds item from saved cart in database when add to primary cart in browser"""

    if session.get("demo_gmail", []):
        email = session["demo_gmail"]
    elif session.get("logged_in_gmail", []):
        email = session["logged_in_gmail"]
    else:
        storage = Storage('gmail.storage')
        credentials = storage.get()
        service = build_service(credentials)
        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
        email = auth_user['emailAddress']

    saved_cart = SavedCart.query.filter_by(user_gmail=email).first()
    # TODO:  update saved cart whenever something added to primary cart

    saved_cart = SavedCart.query.filter_by(user_gmail=email).first()

    item_id = request.form.get("json") # this is the item_id that was deleted from primary cart
    saved_cart_item = SavedCartItem(item_id=item_id,
                                    saved_cart_id=saved_cart.saved_cart_id)
    db.session.add(saved_cart_item)
    db.session.commit()
    print "item", item_id, "added to saved_cart"
# TODO:  Make the return value be the item_description that becomes a flash message?
# to say that the item has been deleted
    return "blah"

@app.route('/delete_item', methods = ["POST"])
def delete_item_from_saved():
    """Deletes item from saved cart in database when delete from primary cart in browser"""

    if session.get("demo_gmail", []):
        email = session["demo_gmail"]
    elif session.get("logged_in_gmail", []):
        email = session["logged_in_gmail"]
    else:
        storage = Storage('gmail.storage')
        credentials = storage.get()
        service = build_service(credentials)
        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
        email = auth_user['emailAddress']

    saved_cart = SavedCart.query.filter_by(user_gmail=email).first()

    item_id = request.form.get("json") # this is the item_id that was deleted from primary cart
    saved_cart_item = SavedCartItem.query.filter_by(item_id=item_id,
                                                    saved_cart_id=saved_cart.saved_cart_id).one()
    db.session.delete(saved_cart_item)
    db.session.commit()
    print "item", item_id, "deleted from saved_cart"
# TODO:  Make the return value be the item_description that becomes a flash message?
# to say that the item has been deleted
    return "blah"

@app.route('/delivery_days')
def delivery_days():
    """Generate json object with frequency of delivery days of user order for D3 histogram"""

    if session.get("demo_gmail", []):
        email = session["demo_gmail"]
    elif session.get("logged_in_gmail", []):
        email = session["logged_in_gmail"]
    else:
        storage = Storage('gmail.storage')
        credentials = storage.get()
        service = build_service(credentials)
        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
        email = auth_user['emailAddress']

    days_list = db.session.query(Order.delivery_day_of_week,
                                  func.count(Order.delivery_day_of_week)).filter(
                                  Order.user_gmail==email).group_by(
                                  Order.delivery_day_of_week).all() # returns list of (day, count) tuples

    days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        # This used to ensure that the days of week displayed in bar chart will be in this order

    days_map = {}
    days_delivered = []
    data = []

    for day_tup in days_list:
        days_map[day_tup[0]] = day_tup[1] # adds day : day count to day_map
        # make dictionary so only have to iterate over day_list once

        # TODO: GO BACK AND MAKE STUFF LIST COMPREHENSION WHEN POSSIBLE !!!!!!!!!!!!!

    for day in days_of_week:
        if day not in days_map.keys(): #TODO: CHANGE THIS TO SETDEFAULT
            days_map[day] = 0 # if day not represented in user data, add to days_map with value of 0
    for day in days_of_week:
        data.append({"day": day, "deliveries": days_map[day]})

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

        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information

        session["logged_in_gmail"] = auth_user['emailAddress']

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

    if session.get("demo_gmail", []):
        email = session["demo_gmail"]
    elif session.get("logged_in_gmail", []):
        email = session["logged_in_gmail"]
    else:
        storage = Storage('gmail.storage')
        credentials = storage.get()
        service = build_service(credentials)
        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
        email = auth_user['emailAddress']

    user = User.query.filter_by(user_gmail=email).first()



    # this should jsonify list of orders of user.
    # http://stackoverflow.com/questions/21411497/flask-jsonify-a-list-of-objects
    # https://github.com/mitsuhiko/flask/issues/510
    user_orders = sorted(user.orders, reverse=True)
    user_orders_json = jsonify(user_gmail=user.user_gmail,
                               orders=[order.serialize() for order in user_orders])
    # orders_json is now a json object in which orders is a list of dictionaries
    # (json objects) with information about each order.

    return user_orders_json

@app.route("/orders_over_time")
def orders_over_time():
    """Generate json object to visualize orders over time using D3"""

    if session.get("demo_gmail", []):
        email = session["demo_gmail"]
    elif session.get("logged_in_gmail", []):
        email = session["logged_in_gmail"]
    else:
        storage = Storage('gmail.storage')
        credentials = storage.get()
        service = build_service(credentials)
        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
        email = auth_user['emailAddress']

    user = User.query.filter_by(user_gmail=email).first()

    min_date = request.args.get("min_date", "01/01/1900")
    max_date = request.args.get("max_date", "12/31/9999")


    return jsonify(data=user.serialize_orders_for_area_chart(max_date, min_date))

@app.route('/demo')
def enter_demo():
    """Redirects to freshlook in demo mode"""

    session["demo_gmail"] = DEMO_GMAIL
    access_token = "demo"

    add_user(DEMO_GMAIL, "demo") # stores user_gmail and credentials token in database

    return redirect('/freshlook')


@socketio.on('start_loading', namespace='/loads')
def load_data(data):

    if data["data"] == "proceed":
        if session.get("demo_gmail", None):

            demo_file = open("demo.txt")
            raw_list = []
            for raw in demo_file:
                raw_list.append(raw.rstrip())


            running_total = 0
            running_quantity = 0
            num_orders = 0
            total_num_orders = len(raw_list)

            logging.info(total_num_orders)


            for raw_message in raw_list:

                decoded_message_body = base64.urlsafe_b64decode(raw_message.encode('ASCII'))

                (amazon_fresh_order_id, line_items_one_order,
                 delivery_time, delivery_day_of_week, delivery_date) = parse_email_message(decoded_message_body)

                add_order(amazon_fresh_order_id, delivery_date, delivery_day_of_week, delivery_time, DEMO_GMAIL, line_items_one_order)

                order = Order.query.filter_by(amazon_fresh_order_id=amazon_fresh_order_id).one()

                order_total = order.calc_order_total()
                order_quantity = order.calc_order_quantity()
                num_orders += 1


                emit('my response', {'order_total': running_total,
                                     'quantity': running_quantity,
                                     'num_orders': num_orders,
                                     'total_num_orders': total_num_orders,
                                     'status': 'loading'
                })

                running_total += order_total
                running_quantity += order_quantity
                gevent.sleep(.1)




                    # adds order to database if not already in database
                print "Message", amazon_fresh_order_id, "order information parsed and added to database"


            demo_file.close()

            db.session.commit()

            emit('my response', {'order_total': running_total,
                                 'quantity': running_quantity,
                                 'num_orders': num_orders,
                                 'total_num_orders': total_num_orders,
                                 'status': 'done'})
        else:

            storage = Storage('gmail.storage')
            credentials = storage.get()
            service = build_service(credentials)
            auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
            email = auth_user['emailAddress']

            # user = User.query.filter_by(user_gmail=email).first()

            query = "from: sheldon.jeff@gmail.com subject:AmazonFresh | Delivery Reminder" # should grab all unique orders.
            # Need to change this to amazonfresh email when running from jeff's gmail inbox

            query_gmail_api_and_seed_db(query, service, credentials) # need to break this out into two fxns later


@socketio.on('disconnect', namespace='/loads')
def test_disconnect():
    print('Client disconnected')

##############################################################################
# Helper functions

def connect_to_db(app, db, db_name):
    """Connect the database to Flask app."""
    # Configure to use SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
    db.app = app
    db.init_app(app)


    with app.app_context(): # http://stackoverflow.com/questions/19437883/when-scattering-flask-models-runtimeerror-application-not-registered-on-db-w
        # if in reseed mode, delete database so can be reseeded.
        if len(argv) > 1:
            script, mode = argv
            if mode == "reseed":
                os.remove(db_name)
        # if database doesn't exist yet, creates database
        if os.path.isfile(db_name) != True:
            db.create_all()
            logging.info("New database called '%s' created" % db_name)

        logging.info("Connected to %s" % db_name)
    return app

def connect_websocket():
    """Sets up SocketIO server"""
    socketio.run(app)
    logging.info("SocketIO connected")


if __name__ == '__main__':
    logging.info("Starting up server.")
    connect_to_db(app, db, "freshstats.db") # connects server to database immediately upon starting up
    connect_websocket()



    # debug=True gives us error messages in the browser and also "reloads" our web app
    # if we change the code.
    # app.run(debug=True)
    # DebugToolbarExtension(app)

    # TODO:  - the api's for getting the orders and the line items should be restful
                #  - read up on restful and make sure that i'm getting my stuff restful
