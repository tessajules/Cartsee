import apiclient, base64, os, email, json, time, gevent, logging, math, os, httplib2
from flask import Flask, render_template, redirect, request, session, jsonify, Response
from flask.ext.socketio import SocketIO, emit
from oauth2client.client import OAuth2WebServerFlow
from apiclient.discovery import build
from oauth2client.file import Storage
from apiclient import errors
from seed import parse_email_message, add_user, add_order, add_line_item, add_item
from model import Order, OrderLineItem, SavedCartItem, Item, SavedCart, User, db, Message
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sys import argv
from datetime import datetime

logging.basicConfig(filename='server.log',level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY']
socketio = SocketIO(app)

# file information for putting raw emails on hard drive for demo mode
CREATE_DEMO = False
DEMO_FILE = "demo.txt"

# fabricated user information for demo mode
DEMO_GMAIL = "acastanieto@gmail.com"
DEMO_ACCESS_TOKEN = "demo"

### oauth ###

def get_oauth_flow():
    """Instantiates an oauth flow object to acquire credentials to authorize
    app access to user data.  Required to kick off oauth step1"""


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

### end oath ###

### seed ###

def seed_db_order(decoded_message_body, user_gmail):
    """Seeds database with parsed order data and returns amazon fresh order id to query for order object"""

    (amazon_fresh_order_id, line_items_one_order,
     delivery_time, delivery_day_of_week, delivery_date) = parse_email_message(decoded_message_body)

    # adds order to database if not already in database
    add_order(amazon_fresh_order_id, delivery_date, delivery_day_of_week, delivery_time, user_gmail, line_items_one_order)

    return amazon_fresh_order_id


def seed_message_id(message_id, user_gmail):
    """Adds message ID to db session if not in demo mode (when actual user signed in)"""
    if not session.get("demo_gmail", None):
        new_message = Message(message_id=message_id, user_gmail=user_gmail)
        db.session.add(new_message)


def seed_demo():
    """Seeds database in demo mode"""

    # Make list of raw email file dictionaries from txt file on hard drive
    demo_file = open(DEMO_FILE)
    message_raw_dicts = {}
    message_id_dicts = []

    message_id = 1 # fabricated message id for demo mode

    for raw in demo_file:
        message = {'raw': raw.rstrip()} # to put it in same format as gmail api packages it so can
                                        # use seed function

        message_id_dicts.append({'id': message_id}) # to put in same format as gmail api packages it so can use
                                               # seed function

        message_raw_dicts[message_id] =  message

        message_id += 1

    access_token = DEMO_ACCESS_TOKEN

    user_gmail = session["demo_gmail"]

    seed_db_all(user_gmail, access_token, None, message_id_dicts, message_raw_dicts, CREATE_DEMO, DEMO_FILE)


def seed_db_all(user_gmail, access_token, service, message_ids_gmail, message_raw_dicts, create_demo, demo_file):
    """Parses raw messages and adds user info and order info to database; emits data to client via websocket"""

    running_total = 0
    running_quantity = 0
    total_num_orders = len(message_ids_gmail)
    num_orders = 0
    messages_for_demo = []

    add_user(user_gmail, access_token) # stores user_gmail and credentials token in database

    # instantiate user object for latest user credentials
    user = User.query.filter_by(user_gmail=user_gmail).one()

    # make list of message ids currently in database to check against below
    message_ids_db = [message_obj.message_id for message_obj in user.messages]

    for message_id in message_ids_gmail:

        if message_id['id'] not in message_ids_db:

            seed_message_id(message_id['id'], user_gmail)

        if service:
            message_dict = service.users().messages().get(userId="me",
                                                        id=message_id["id"],
                                                        format="raw").execute()

            messages_for_demo.append(message_dict)


        else:
            message_dict = message_raw_dicts[message_id['id']]


        decoded_message_body = base64.urlsafe_b64decode(message_dict['raw'].encode('ASCII'))


        if "Doorstep Delivery" in decoded_message_body: # workaround to rule out 1 strangely formatted email

            amazon_fresh_order_id = seed_db_order(decoded_message_body, user_gmail)

            order = Order.query.filter_by(amazon_fresh_order_id=amazon_fresh_order_id).one()

            num_orders += 1

            # emits the most current order info with the status code of "loading" to client
            order_total, order_quantity = emit_order_info(amazon_fresh_order_id,
                                                            num_orders,
                                                            running_total,
                                                            running_quantity,
                                                            total_num_orders,
                                                            .1,
                                                            "loading")

            running_total += order_total
            running_quantity += order_quantity



    db.session.commit()

    if create_demo:
        demo_file = create_demo_file(demo_file, messages_for_demo)

    session["std_map"] = user.build_std_map()

    # emits the last order info with the status code of "done" to client
    emit_order_info(amazon_fresh_order_id,
                    num_orders,
                    running_total,
                    running_quantity,
                    total_num_orders,
                    .1,
                    "done")

### end seed ###

### make demo file ###

def create_demo_file(demo_filename, messages):
    """Creates a .txt file of raw emails for use in demo mode"""
    # updates the demo file

    if session.get("demo_gmail", None):
        return

    demo_file = open(demo_filename, "w")

    for message in messages: # each message is dictionary of email information and content from gmail api

        decoded_message_body = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

        if "Doorstep Delivery" in decoded_message_body:

            demo_file.write(message["raw"] + "\n")

    demo_file.close()

### end make demo file ###

### websocket helper ###

def emit_order_info(amazon_fresh_order_id, num_orders, running_total, running_quantity, total_num_orders, delay, status):
    """emits order info through websocket and returns last emitted order info"""

    order = Order.query.filter_by(amazon_fresh_order_id=amazon_fresh_order_id).one()

    order_total = order.calc_order_total()
    order_quantity = order.calc_order_quantity()

    emit('my response', {'order_total': running_total,
                         'quantity': running_quantity,
                         'num_orders': num_orders,
                         'total_num_orders': total_num_orders,
                         'status': status
    })

    gevent.sleep(delay)


    return order_total, order_quantity

### end websocket helper ###


### gmail api ###

def query_gmail_api(query, service, credentials):
    """Queries Gmail API for authenticated user information and a list of email
       message ids matching query"""

    message_ids = []

    auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
    user_gmail = auth_user['emailAddress'] # extract user gmail address
    access_token = credentials.access_token

    response = service.users().messages().list(userId="me", q=query).execute()
    message_ids.extend(response['messages'])

    return user_gmail, access_token, message_ids

### end gmail api ###

### D3 tree graph ###

def build_cart_hierarchy(cart_name, item_obj_list):
    """Builds a hierarchy for items in one cart for D3 tree graph"""

    mean_dict = {} # for storing items under their mean frequencies
    std_dict = {} # for storing mean frequencies under their stds

    # Place item descriptions under their respective means (frequencies in mean days between)
    for item in item_obj_list:
       mean, std = item.calc_days_btw()
       mean_dict.setdefault(mean, [])
       mean_dict[mean].append(item)
       std_dict.setdefault(std, [])
       std_dict[std].append(mean)

    # make properly formatted hierarchy of means and items and map them to their stds
    std_nodes =  []


    for std in sorted(std_dict.keys()):
        mean_nodes = []
        for mean in std_dict[std]:

            mean_node = {
             "name": "Frequency: " + ("%.2f" % mean),
             "children": [{"name": item.description} for item in mean_dict[mean]]
             }

            mean_nodes.append(mean_node)

        std_node = {
                     "name": "Deviation: " + ("%.2f" % std),
                     "children": mean_nodes
                    }

        std_nodes.append(std_node)

    return {
            "name": cart_name,
            "children": std_nodes
            }


def build_all_carts_hierarchy(saved_items, primary_items, backup_items):
    """Builds the dictionary that will be used in the collapsible
       tree D3 graph that shows the hierarchy of all three cart types
       (saved, primary, backup) in which the prediction
       algorithm placed the items to go in the predicted cart"""

    saved_cart = build_cart_hierarchy("saved items", saved_items)
    primary_cart = build_cart_hierarchy("primary items", primary_items)
    backup_cart = build_cart_hierarchy("more recommended items", backup_items)

    return {
        "name": "predicted items",
        "children": [saved_cart, primary_cart, backup_cart]
        }

### end D3 tree graph ###

### ROUTES #################################################################

@app.route('/')
def landing_page():
    """Renders landing page html template with Gmail sign-in button
    and demo button"""

    return render_template("index.html")


### oath routes ###

@app.route('/login/')
def login():
    """OAuth step1 kick off - redirects user to auth_uri on app platform"""

    auth_uri = get_oauth_flow().step1_get_authorize_url()

    return redirect(auth_uri)


@app.route('/return-from-oauth/')
def login_callback():
    """This is the auth_uri.  User redirected here after OAuth step1.
    Here the authorization code obtained when user gives app permissions
    is exchanged for a credentials object"""

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

        return redirect("/cartsee")
### END oauth routes ###

### demo route ###
@app.route('/demo')
def enter_demo():
    """Redirects to cartsee in demo mode"""

    session["demo_gmail"] = DEMO_GMAIL

    return redirect('/cartsee')
### END demo route ###

@app.route('/cartsee')
def cartsee():
    """Renders cartsee html template"""

    return render_template("cartsee.html")


@app.route('/list_orders')
def list_orders():
    """Generate json object to list user and order information in browser"""

    if session.get("demo_gmail", []): #change to none instead of []
        email = session["demo_gmail"]
    elif session.get("logged_in_gmail", []): #change to none instead of []
        email = session["logged_in_gmail"]
    else:
        storage = Storage('gmail.storage')
        credentials = storage.get()
        service = build_service(credentials)
        auth_user = service.users().getProfile(userId = 'me').execute() # query for authenticated user information
        email = auth_user['emailAddress']

    user = User.query.filter_by(user_gmail=email).first()

    user_orders_json = jsonify(user_gmail=user.user_gmail,
                               orders=[order.serialize() for order in user.orders])
    # orders_json is now a json object in which orders is a list of dictionaries
    # (json objects) with information about each order.

    return user_orders_json


### loading screen websocket routes ###

@socketio.on('start_loading', namespace='/loads')
def load_data(data):

    if data["data"] == "proceed": # 'proceed' indicates the websocket is done connecting.
        if session.get("demo_gmail", None):
            seed_demo()

        else:

            # get user credentials out of storage
            storage = Storage('gmail.storage')
            credentials = storage.get()
            service = build_service(credentials)

            # query is workaround for having to forward emails to my inbox from Amazon Fresh user's inbox
            query = "from: sheldon.jeff@gmail.com subject:AmazonFresh | Delivery Reminder" # should grab all unique orders.
            # Use from: Amazon Fresh email when signed into Amazon Fresh user's gmail inbox

            # query for list of raw email messages using gmail_api
            user_gmail, access_token, message_ids = query_gmail_api(query, service, credentials)


            # seed db with user information and parsed order information
            seed_db_all(user_gmail, access_token, service, message_ids, None, CREATE_DEMO, DEMO_FILE)


@socketio.on('disconnect', namespace='/loads')
def test_disconnect():
    print "Client disconnected"

### END loading screen websocket routes ###

### D3 routes ###

@app.route('/items_by_qty') # DATA FOR BUBBLE CHART
def items_by_qty():
    """Generates json object from list of items user bought to visualize item clusters using D3"""

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
    max_price_description = ""
    max_qty = 0
    max_qty_description = ""

    for item_tup in item_list:

        description, quantity, unit_price_cents = item_tup
        if description.count(",") >= 1: # if description has at least one comma in it
            description = " ".join(description.split(", ")[:-1]) # get rid of the the last thing separated by comma

        unit_price = float(unit_price_cents)/100
        unit_price_str = "$%.2f" % unit_price


        if unit_price > max_price:
            max_price = unit_price
            max_price_description = description

        if quantity > max_qty:
            max_qty = quantity
            max_qty_description = description

        # if unit price is within the top and bottom ranges, and top and bottom quantities, that the user set,
        # nest items within their respective price range
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
                    "max_qty": max_qty,
                    "max_price_description": max_price_description,
                    "max_qty_description": max_qty_description})

@app.route("/orders_over_time") # time series chart
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

    bottom_date = request.args.get("bottom_date", "01/01/1900")
    top_date = request.args.get("top_date", "12/31/9999")

    order_date_totals, min_date, max_date, min_total, max_total = user.serialize_orders_for_area_chart(top_date, bottom_date)

    return jsonify(data=order_date_totals,
                   min_date=min_date,
                   max_date=max_date,
                   min_total=min_total,
                   max_total=max_total)

@app.route('/delivery_days') # Bar chart
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

### end D3 routes ###

### prediction routes ###

@app.route('/saved_cart') # saved cart when first lang on prediction page
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

@app.route('/predict_cart', methods = ["GET"]) # returns predicted cart contents
def predict_cart():
    """Generate json object with items predicted to be in next order to populate
    predicted cart"""

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


    if session.get("std_map", None):
        std_map = session.get("std_map")

    else:
        std_map = user.build_std_map()

    all_cart_objs, cart_qty = user.predict_cart(date_str, std_map) # list of all item objects from
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


    # pass saved items, primary cart items and backup items into function that
    # builds the prediction hierarchy for visualizing in D3
    prediction_tree = build_all_carts_hierarchy(saved_cart.items, primary_cart_objs, backup_cart_objs)

    return jsonify(primary_cart=primary_cart, backup_cart=backup_cart, prediction_tree=prediction_tree)

@app.route('/add_item', methods = ["POST"]) # adds item to DB
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

    return "item added"

@app.route('/delete_item', methods = ["POST"]) # deletes item from DB
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
    return "item deleted"

### END prediction routes ###




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
