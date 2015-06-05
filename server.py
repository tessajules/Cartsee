from flask import Flask, render_template, redirect, request, session, jsonify, Response
from flask.ext.socketio import SocketIO, emit
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
                    "max_qty": max_qty,
                    "max_price_description": max_price_description,
                    "max_qty_description": max_qty_description})

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

def build_cart_hierarchy(cart_name, item_obj_list):
    """Builds a hierarchy for items in one cart for D3 tree graph"""

    mean_dict = {} # for storing items under their mean
    std_dict = {}

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
        for mean in sorted(std_dict[std]):

            mean_node = {
             "name": std_dict[std],
             "children": [{"name": item.description} for item in mean_dict[mean] for mn in std_dict[std]]}

            mean_nodes.append(mean_node)

        std_node = {
                     "name": std,
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

    # for tree layout of prediction hierarchy, new_item_primary lists the children
    # of the predicted items node - items that are new to the predicted cart that weren't saved before.
    if saved_cart.items:
        new_items_primary = [obj for obj in primary_cart_objs if obj not in saved_cart.items]

    else:
        new_items_primary = []

    # pass saved items, primary cart items and backup items into function that
    # builds the prediction hierarchy for visualizing in D3
    prediction_tree = build_all_carts_hierarchy(saved_cart.items, new_items_primary, backup_cart_objs)
    print prediction_tree
    return jsonify(primary_cart=primary_cart, backup_cart=backup_cart, prediction_tree=prediction_tree)


@app.route('/test')
def treetest():

    dict = {'name': 'predicted items', 'children': [{'name': 'saved items', 'children': [{'name': 0.9428090415820634, 'children': [{'name': [7.333333333333333], 'children': [{'name': u'Organic Greenhouse Grape Tomatoes, 1 Pint'}]}]}, {'name': 1.0, 'children': [{'name': [50.0, 39.0], 'children': [{'name': u'Lipton Recipe Secrets Recipe Soup & Dip Mix, Beefy Onion 2.2 oz'}, {'name': u'Lipton Recipe Secrets Recipe Soup & Dip Mix, Beefy Onion 2.2 oz'}]}, {'name': [50.0, 39.0], 'children': [{'name': u'Sparkle Paper Towels, 2-Ply, 8 Rolls'}, {'name': u'Sparkle Paper Towels, 2-Ply, 8 Rolls'}]}]}, {'name': 2.160246899469287, 'children': [{'name': [16.0], 'children': [{'name': u'Organic Lacinato (Dinosaur) Kale, 1 Bunch'}]}]}, {'name': 2.5, 'children': [{'name': [16.5, 10.5], 'children': [{'name': u'Cascadian Farm, Organic Cut Green Beans, 10 oz (Frozen)'}, {'name': u'Cascadian Farm, Organic Cut Green Beans, 10 oz (Frozen)'}, {'name': u'Just BARE Fresh, Hand-Trimmed Boneless Skinless Chicken Breast Fillets (Raised without Antibiotics), 14oz'}, {'name': u'Just BARE Fresh, Hand-Trimmed Boneless Skinless Chicken Breast Fillets (Raised without Antibiotics), 14oz'}]}, {'name': [16.5, 10.5], 'children': [{'name': u'Westbrae Natural Vegetarian Organic Garbanzo Beans, 15 Oz'}, {'name': u'Westbrae Natural Vegetarian Organic Garbanzo Beans, 15 Oz'}]}]}, {'name': 3.5, 'children': [{'name': [10.5, 156.5, 31.5, 31.5], 'children': [{'name': u'Cascadian Farm, Organic Cut Green Beans, 10 oz (Frozen)'}, {'name': u'Cascadian Farm, Organic Cut Green Beans, 10 oz (Frozen)'}, {'name': u'Cascadian Farm, Organic Cut Green Beans, 10 oz (Frozen)'}, {'name': u'Cascadian Farm, Organic Cut Green Beans, 10 oz (Frozen)'}, {'name': u'Just BARE Fresh, Hand-Trimmed Boneless Skinless Chicken Breast Fillets (Raised without Antibiotics), 14oz'}, {'name': u'Just BARE Fresh, Hand-Trimmed Boneless Skinless Chicken Breast Fillets (Raised without Antibiotics), 14oz'}, {'name': u'Just BARE Fresh, Hand-Trimmed Boneless Skinless Chicken Breast Fillets (Raised without Antibiotics), 14oz'}, {'name': u'Just BARE Fresh, Hand-Trimmed Boneless Skinless Chicken Breast Fillets (Raised without Antibiotics), 14oz'}]}, {'name': [10.5, 156.5, 31.5, 31.5], 'children': [{'name': u'Bartlett Pear, 1 Pear (Washington)'}, {'name': u'Bartlett Pear, 1 Pear (Washington)'}, {'name': u'Bartlett Pear, 1 Pear (Washington)'}, {'name': u'Bartlett Pear, 1 Pear (Washington)'}, {'name': u'Brussels Sprout, 1lb Package (United States or Mexico)'}, {'name': u'Brussels Sprout, 1lb Package (United States or Mexico)'}, {'name': u'Brussels Sprout, 1lb Package (United States or Mexico)'}, {'name': u'Brussels Sprout, 1lb Package (United States or Mexico)'}]}, {'name': [10.5, 156.5, 31.5, 31.5], 'children': [{'name': u'Bartlett Pear, 1 Pear (Washington)'}, {'name': u'Bartlett Pear, 1 Pear (Washington)'}, {'name': u'Bartlett Pear, 1 Pear (Washington)'}, {'name': u'Bartlett Pear, 1 Pear (Washington)'}, {'name': u'Brussels Sprout, 1lb Package (United States or Mexico)'}, {'name': u'Brussels Sprout, 1lb Package (United States or Mexico)'}, {'name': u'Brussels Sprout, 1lb Package (United States or Mexico)'}, {'name': u'Brussels Sprout, 1lb Package (United States or Mexico)'}]}, {'name': [10.5, 156.5, 31.5, 31.5], 'children': [{'name': u'Oggi Eco-Liner Compost Pail Liners'}, {'name': u'Oggi Eco-Liner Compost Pail Liners'}, {'name': u'Oggi Eco-Liner Compost Pail Liners'}, {'name': u'Oggi Eco-Liner Compost Pail Liners'}]}]}, {'name': 4.0, 'children': [{'name': [25.0, 82.0, 46.0], 'children': [{'name': u'Green Beans, 1 lb'}, {'name': u'Green Beans, 1 lb'}, {'name': u'Green Beans, 1 lb'}]}, {'name': [25.0, 82.0, 46.0], 'children': [{'name': u'Red Bell Pepper, Large'}, {'name': u'Red Bell Pepper, Large'}, {'name': u'Red Bell Pepper, Large'}]}, {'name': [25.0, 82.0, 46.0], 'children': [{'name': u'Tampax Pearl Plastic, Super Plus Absorbency, Scented Tampons, 36 Count'}, {'name': u'Tampax Pearl Plastic, Super Plus Absorbency, Scented Tampons, 36 Count'}, {'name': u'Tampax Pearl Plastic, Super Plus Absorbency, Scented Tampons, 36 Count'}]}]}, {'name': 4.027681991198191, 'children': [{'name': [11.666666666666666], 'children': [{'name': u'President, Feta, Crumbl ed, 6 oz'}]}]}, {'name': 4.5, 'children': [{'name': [25.5], 'children': [{'name': u'Fresh Beef, 80-85% Lean Ground Beef, 16oz'}]}]}, {'name': 5.5533773507659285, 'children': [{'name': [13.4], 'children': [{'name': u'Taylor Farms Organic Baby Spinach, 16 oz Clamshell'}]}]}, {'name': 6.0, 'children': [{'name': [77.0], 'children': [{'name': u'Pork Boneless Loin Chop, Fresh, 6oz Each (4 Pc)'}]}]}, {'name': 6.5, 'children': [{'name': [84.5, 70.5], 'children': [{'name': u'Celestial Seasonings, Sleepytime, 100% Natural, 20 ct'}, {'name': u'Celestial Seasonings, Sleepytime, 100% Natural, 20 ct'}]}, {'name': [84.5, 70.5], 'children': [{'name': u'Ziploc Freezer Bags Value Pack, Gallon, 30 ct'}, {'name': u'Ziploc Freezer Bags Value Pack, Gallon, 30 ct'}]}]}, {'name': 6.649979114420001, 'children': [{'name': [30.333333333333332], 'children': [{'name': u'Brussels Sprouts, 1 lb Package'}]}]}]}, {'name': 'primary items', 'children': []}, {'name': 'more recommended items', 'children': [{'name': 6.5, 'children': [{'name': [13.5], 'children': [{'name': u'Barilla Pasta, Spaghetti, 16 Ounce'}]}]}, {'name': 7.0, 'children': [{'name': [14.0], 'children': [{'name': u'Just BARE Fresh, Whole Chicken without Giblets & Neck (Raised without Antibiotics), 58.4oz'}]}]}, {'name': 7.5, 'children': [{'name': [27.5], 'children': [{'name': u"Loving Pets Nature's Choice 100-Percent Natural Rawhide White Retriever Rolls Dog Treat, 10-Inch, 5/Pack"}]}]}, {'name': 8.0, 'children': [{'name': [27.0], 'children': [{'name': u'Applegate, Savory Turkey Breakfast Sausage, 7 oz (frozen)'}]}]}, {'name': 8.73053390247253, 'children': [{'name': [25.666666666666668], 'children': [{'name': u'Asparagus, Medium, 1lb Bunch (United States, Peru or Mexico)'}, {'name': u'Starbucks Breakfast Blend Whole Bean Coffee (Mild), 12 oz'}]}]}, {'name': 9.85936613539207, 'children': [{'name': [17.846153846153847], 'children': [{'name': u'Yellow Onion, Large'}]}]}, {'name': 10.154183276685966, 'children': [{'name': [19.272727272727273], 'children': [{'name': u'Creekstone All Natural Ground Beef, Brick Fresh, 16 Ounce'}]}]}, {'name': 10.466878978738388, 'children': [{'name': [19.333333333333332], 'children': [{'name': u'Taylor Farms Organic Spinach, 16 oz Clamshell'}]}]}, {'name': 10.467874134173035, 'children': [{'name': [17.583333333333332], 'children': [{'name': u'Just Bare Chicken Family Pack Thighs (Raised without Antibiotics), 2.25 lb'}]}]}, {'name': 10.5, 'children': [{'name': [16.5, 52.5], 'children': [{'name': u"Mrs. Cubbison's Seasoned Croutons, 5 oz"}, {'name': u"Mrs. Cubbison's Seasoned Croutons, 5 oz"}]}, {'name': [16.5, 52.5], 'children': [{'name': u'DiGiorno Shredded Parmesan Cup, 6 oz'}, {'name': u'DiGiorno Shredded Parmesan Cup, 6 oz'}]}]}, {'name': 10.609429767899874, 'children': [{'name': [19.8], 'children': [{'name': u'Just Bare Chicken Family Pack B/S Breast (Raised without Antibiotics), 2 lb'}, {'name': u'Asparagus, 1 Bunch'}]}]}, {'name': 10.873004286866728, 'children': [{'name': [14.666666666666666], 'children': [{'name': u'Love Beets Cooked Beets, 8.8 oz'}]}]}, {'name': 11.0, 'children': [{'name': [17.0, 18.0, 31.0], 'children': [{'name': u'Navel Orange, 1 Large Orange (United States, Australia or Chile)'}, {'name': u'Navel Orange, 1 Large Orange (United States, Australia or Chile)'}, {'name': u'Navel Orange, 1 Large Orange (United States, Australia or Chile)'}]}, {'name': [17.0, 18.0, 31.0], 'children': [{'name': u'Broccoli Crowns, 1lb Package'}, {'name': u'Broccoli Crowns, 1lb Package'}, {'name': u'Broccoli Crowns, 1lb Package'}, {'name': u'Tyson Applewood Smoked Bacon, 1 lb'}, {'name': u'Tyson Applewood Smoked Bacon, 1 lb'}, {'name': u'Tyson Applewood Smoked Bacon, 1 lb'}]}, {'name': [17.0, 18.0, 31.0], 'children': [{'name': u'Organic Valley, Heavy Whipping Cream, Organic, Pint, 16 oz'}, {'name': u'Organic Valley, Heavy Whipping Cream, Organic, Pint, 16 oz'}, {'name': u'Organic Valley, Heavy Whipping Cream, Organic, Pint, 16 oz'}]}]}, {'name': 12.0, 'children': [{'name': [18.0], 'children': [{'name': u'Broccoli Crowns, 1lb Package'}, {'name': u'Tyson Applewood Smoked Bacon, 1 lb'}]}]}, {'name': 12.229290885229428, 'children': [{'name': [37.666666666666664], 'children': [{'name': u'Lemon, Medium'}, {'name': u'Organic Kale, 1 Bunch'}]}]}, {'name': 12.355835328567093, 'children': [{'name': [54.0], 'children': [{'name': u'Organic, Green Bell Pepper, Large'}, {'name': u'Sliced White Mushrooms, 8 oz Package'}]}]}, {'name': 12.5, 'children': [{'name': [73.5], 'children': [{'name': u'Thomas, Everything Bagels, 6 ct, 20 oz'}, {'name': u"Secret Original Unscented Women's Invisible Solid pH Balanced Antiperspirant & Deodorant 2.6 Oz"}]}]}, {'name': 12.784365451597509, 'children': [{'name': [21.6], 'children': [{'name': u'Garlic, Medium'}]}]}, {'name': 13.0, 'children': [{'name': [49.0], 'children': [{'name': u'Ginger,  8 oz Package (Brazil or China)'}]}]}, {'name': 13.199326582148888, 'children': [{'name': [16.333333333333332], 'children': [{'name': u'California Ranch Fresh Large Grade A Eggs, 18 ct'}]}]}, {'name': 13.5, 'children': [{'name': [21.5], 'children': [{'name': u'Cauliflower, 1 Head'}]}]}, {'name': 14.0, 'children': [{'name': [42.0, 21.0], 'children': [{'name': u'Berkeley Farms Whole Milk, Quart'}, {'name': u'Berkeley Farms Whole Milk, Quart'}, {'name': u'Kale, Organic, 1 Bunch (United States)'}, {'name': u'Kale, Organic, 1 Bunch (United States)'}]}, {'name': [42.0, 21.0], 'children': [{'name': u'Oroweat, 100% Whole Wheat Bread, 24 oz'}, {'name': u'Oroweat, 100% Whole Wheat Bread, 24 oz'}]}]}, {'name': 14.218298069740978, 'children': [{'name': [19.8], 'children': [{'name': u'Just Bare Chicken Family Pack B/S Breast (Raised without Antibiotics), 2 lb'}, {'name': u'Asparagus, 1 Bunch'}]}]}, {'name': 15.369522511198006, 'children': [{'name': [35.666666666666664], 'children': [{'name': u'Suave Body Wash, Sweet Pea & Violet, 12 Fl Oz'}]}]}, {'name': 15.788896611174168, 'children': [{'name': [26.727272727272727], 'children': [{'name': u'Starbucks Breakfast Blend Whole Bean Coffee (Medium), 12 oz'}]}]}, {'name': 16.224980739587952, 'children': [{'name': [40.5], 'children': [{'name': u'Gold Potatoes, 3 lb'}]}]}, {'name': 16.408839081421938, 'children': [{'name': [26.5], 'children': [{'name': u'Lemon, 1 Lemon (United States)'}]}]}, {'name': 16.5, 'children': [{'name': [60.5], 'children': [{'name': u'Tillamook Butter, Sweet Cream, Salted, 1 lb'}]}]}, {'name': 16.719340064127255, 'children': [{'name': [18.58823529411765], 'children': [{'name': u'Tillamook Butter, Sweet Cream, Unsalted, 1 lb'}]}]}, {'name': 17.190113437671084, 'children': [{'name': [23.0], 'children': [{'name': u'Spinach, Organic, 1 Bunch (United States)'}]}]}, {'name': 17.46106780494506, 'children': [{'name': [25.666666666666668], 'children': [{'name': u'Asparagus, Medium, 1lb Bunch (United States, Peru or Mexico)'}, {'name': u'Starbucks Breakfast Blend Whole Bean Coffee (Mild), 12 oz'}]}]}, {'name': 17.55806692907036, 'children': [{'name': [24.0], 'children': [{'name': u'Yellow Onion, 1 Large Onion (United States)'}]}]}, {'name': 18.00617178142601, 'children': [{'name': [39.666666666666664], 'children': [{'name': u'Peeled Baby Carrot, 1 lb Bag (United States)'}]}]}, {'name': 18.208667044996886, 'children': [{'name': [32.333333333333336], 'children': [{'name': u'Broccoli Crowns, 1lb Package (United States)'}]}]}, {'name': 18.2208671582886, 'children': [{'name': [21.0], 'children': [{'name': u'Berkeley Farms Whole Milk, Quart'}, {'name': u'Kale, Organic, 1 Bunch (United States)'}]}]}, {'name': 18.5, 'children': [{'name': [38.5, 31.5], 'children': [{'name': u'Barilla, Spaghetti, 16 oz'}, {'name': u'Barilla, Spaghetti, 16 oz'}]}, {'name': [38.5, 31.5], 'children': [{'name': u"Stouffer's, Macaroni & Cheese, Family Size, 40 oz (Frozen)"}, {'name': u"Stouffer's, Macaroni & Cheese, Family Size, 40 oz (Frozen)"}]}]}, {'name': 18.933683608849073, 'children': [{'name': [32.375], 'children': [{'name': u'Beef Flat Iron Steak, Center Cut, USDA Choice, Fresh, 8oz Each (2 pc)'}]}]}, {'name': 19.0, 'children': [{'name': [32.0], 'children': [{'name': u'MontchC3A8vre, Goat Cheese , Crumbled, 4 oz'}]}]}, {'name': 19.014614262602212, 'children': [{'name': [30.333333333333332], 'children': [{'name': u'Hillshire Farms, Polska Kielbasa, 14 oz'}, {'name': u'Asparagus, Medium, 1 lb Bunch'}]}]}, {'name': 19.5, 'children': [{'name': [49.5], 'children': [{'name': u'Bausch & Lomb ReNu MultiPlus Multi-Purpose Solution, 12 Fl Oz'}]}]}, {'name': 20.43417616532547, 'children': [{'name': [30.333333333333332], 'children': [{'name': u'Hillshire Farms, Polska Kielbasa, 14 oz'}, {'name': u'Asparagus, Medium, 1 lb Bunch'}]}]}, {'name': 21.96724834839357, 'children': [{'name': [25.2], 'children': [{'name': u'Fuji Apple, Organic, 1 Apple (United States)'}]}]}, {'name': 22.13276699827656, 'children': [{'name': [23.875], 'children': [{'name': u'Broccoli Crowns, 1 lb'}]}]}, {'name': 22.20270253820467, 'children': [{'name': [27.8], 'children': [{'name': u'Earthbound Farm Organic Power Greens, 5 oz Clamshell'}]}]}, {'name': 23.03388807822075, 'children': [{'name': [24.2], 'children': [{'name': u'Premium Cuts, Natural Beef Boneless Top Sirloin Steak, Center Cut, USDA Choice, Fresh, 8oz Each (2 pc)'}]}]}, {'name': 23.034959843681083, 'children': [{'name': [58.875], 'children': [{'name': u"High Endurance Invisible Solid Pure Sport Scent Men's Anti-Perspirant & Deodorant 3 Oz"}]}]}, {'name': 23.95035233900808, 'children': [{'name': [22.705882352941178], 'children': [{'name': u'California Ranch Fresh Large Grade AA Eggs, 18 ct'}]}]}, {'name': 24.0, 'children': [{'name': [67.0], 'children': [{'name': u'Natural Pork Boneless Shoulder Roast, 3 lb'}]}]}, {'name': 24.468091466234142, 'children': [{'name': [35.25], 'children': [{'name': u'Baby Carrots, 1 lb'}]}]}, {'name': 26.284765338288427, 'children': [{'name': [42.333333333333336], 'children': [{'name': u'Just Bare Chicken Family Pack, Thighs, 36 oz'}]}]}, {'name': 26.837127360406473, 'children': [{'name': [22.363636363636363], 'children': [{'name': u'Just BARE Fresh, Hand-Trimmed Boneless Skinless Chicken Breast Fillets, 14oz'}]}]}, {'name': 27.236107569833756, 'children': [{'name': [29.166666666666668], 'children': [{'name': u'Fage, Greek Fat Free Yogurt, Yogurt, Honey, 5.3 oz'}]}]}, {'name': 27.3597433386272, 'children': [{'name': [37.333333333333336], 'children': [{'name': u'Just BARE Fresh, Whole Chicken without Giblets & Neck, 58.4oz'}, {'name': u'Just BARE Fresh, Bone-In Chicken Thighs, 20oz'}]}]}, {'name': 27.5, 'children': [{'name': [35.5], 'children': [{'name': u'Taylor Farms Stringless Sugar Snap Pea, 8 oz'}]}]}, {'name': 28.83308756924083, 'children': [{'name': [30.285714285714285], 'children': [{'name': u'Lactaid, Reduced Fat 2% Milk, 100% Lactose Free, Half Gallon, 64 oz'}]}]}, {'name': 28.986586936412884, 'children': [{'name': [63.333333333333336], 'children': [{'name': u'Green Onions (Scallions), Bunch'}]}]}, {'name': 29.166547618804664, 'children': [{'name': [48.75], 'children': [{'name': u'Cauliflower, 1 Large Head'}]}]}, {'name': 32.0, 'children': [{'name': [75.0, 60.0], 'children': [{'name': u'Dole Dates, Pitted, 8 oz'}, {'name': u'Dole Dates, Pitted, 8 oz'}]}, {'name': [75.0, 60.0], 'children': [{'name': u'Bags on Board Regular Bag Refill Pack, 120 Bags'}, {'name': u'Bags on Board Regular Bag Refill Pack, 120 Bags'}]}]}, {'name': 35.5, 'children': [{'name': [97.5], 'children': [{'name': u'Sparkle Tissues, Giant Roll, Pick-A-Size, 8 ct'}]}]}, {'name': 36.98498193711725, 'children': [{'name': [37.666666666666664], 'children': [{'name': u'Lemon, Medium'}, {'name': u'Organic Kale, 1 Bunch'}]}]}, {'name': 37.5, 'children': [{'name': [73.5], 'children': [{'name': u'Thomas, Everything Bagels, 6 ct, 20 oz'}, {'name': u"Secret Original Unscented Women's Invisible Solid pH Balanced Antiperspirant & Deodorant 2.6 Oz"}]}]}, {'name': 38.0, 'children': [{'name': [53.0], 'children': [{'name': u'TRESemme European Conditioner with Pro-Vitamin B5 & Aloe for All Hair Types, Remoisturize, 32 oz'}]}]}, {'name': 43.57177985806869, 'children': [{'name': [40.0], 'children': [{'name': u'Quaker Chewy Granola Bars Dipps Peanut Butter, 6 ct, 1.05 oz each'}]}]}, {'name': 45.614325235244536, 'children': [{'name': [54.0], 'children': [{'name': u'Organic, Green Bell Pepper, Large'}, {'name': u'Sliced White Mushrooms, 8 oz Package'}]}]}, {'name': 48.14561246884289, 'children': [{'name': [65.0], 'children': [{'name': u'Garlic, 1 Large Head (United States or Mexico)'}]}]}, {'name': 51.91300415117584, 'children': [{'name': [46.2], 'children': [{'name': u'Mahatma Enriched Extra Long Grain White Rice, 32 Oz'}]}]}, {'name': 53.717367355032906, 'children': [{'name': [37.333333333333336], 'children': [{'name': u'Just BARE Fresh, Whole Chicken without Giblets & Neck, 58.4oz'}, {'name': u'Just BARE Fresh, Bone-In Chicken Thighs, 20oz'}]}]}, {'name': 55.07167047483569, 'children': [{'name': [58.666666666666664], 'children': [{'name': u'Oroweat, Country Buttermilk Bread, 24 oz'}]}]}, {'name': 56.95807424959364, 'children': [{'name': [112.33333333333333], 'children': [{'name': u'Glad Tall Kitchen Drawstring Trash Bags, 13 Gallon, 45 ct'}]}]}, {'name': 62.72708745031926, 'children': [{'name': [73.25], 'children': [{'name': u'Oscar Mayer, Bacon, 16 oz'}]}]}, {'name': 65.5, 'children': [{'name': [80.5], 'children': [{'name': u'Ziploc Snack Bags, 50 ct'}]}]}, {'name': 67.0, 'children': [{'name': [109.0, 95.0], 'children': [{'name': u'Berkeley Farms Sour Cream, 16 oz'}, {'name': u'Berkeley Farms Sour Cream, 16 oz'}, {'name': u'Progresso Bread Crumbs, Plain, 15 Oz'}, {'name': u'Progresso Bread Crumbs, Plain, 15 Oz'}]}, {'name': [109.0, 95.0], 'children': [{'name': u'Ginger,  8 oz'}, {'name': u'Ginger,  8 oz'}]}]}, {'name': 74.0, 'children': [{'name': [95.0], 'children': [{'name': u'Berkeley Farms Sour Cream, 16 oz'}, {'name': u'Progresso Bread Crumbs, Plain, 15 Oz'}]}]}, {'name': 78.37250793486196, 'children': [{'name': [103.5], 'children': [{'name': u'Lipton Recipe Secrets Soup & Dip Mix, Onion , 2 ct'}]}]}, {'name': 78.5, 'children': [{'name': [85.5], 'children': [{'name': u'Kraft Singles, American, 16 Slices, 12 oz'}]}]}, {'name': 80.0, 'children': [{'name': [193.0], 'children': [{'name': u'Guerrero, 6 Inch White Corn Tortillas, 80 ct, 4.17 lb'}]}]}, {'name': 80.14237331150107, 'children': [{'name': [58.0], 'children': [{'name': u'Lactaid, Reduced Fat Milk, 100% Lactose Free, Half Gallon'}]}]}, {'name': 80.93058754265905, 'children': [{'name': [49.2], 'children': [{'name': u'Cascadian Farm, Broccoli, Cuts, Organic, 16 oz (Frozen)'}]}]}, {'name': 81.39218328562025, 'children': [{'name': [100.25], 'children': [{'name': u"Nature's Way Lactase formula, Enzyme Active, 100 Capsules"}]}]}, {'name': 82.23721785177317, 'children': [{'name': [72.8], 'children': [{'name': u'Tejava, Iced Tea, Unsweetened, 1  Liter'}]}]}, {'name': 92.33287605181592, 'children': [{'name': [74.2], 'children': [{'name': u'Oroweat, Country Potato Bread, 24 oz'}]}]}, {'name': 93.5, 'children': [{'name': [105.5], 'children': [{'name': u'Jimmy Dean Foods Sausage Egg and Cheese Croissant, 18 oz (frozen)'}]}]}, {'name': 97.25224933131366, 'children': [{'name': [152.0], 'children': [{'name': u"Campbell's Cream of Mushroom Soup, 10.75 oz"}]}]}, {'name': 102.29478101165387, 'children': [{'name': [114.66666666666667], 'children': [{'name': u'Dawn Ultra Antibacterial Hand Soap Orange Scent Dishwashing Liquid, 24 Fl Oz'}]}]}, {'name': 108.4875824947517, 'children': [{'name': [154.33333333333334], 'children': [{'name': u'Crisco, Pure Vegetable Oil, 48 oz'}]}]}, {'name': 128.2038307626657, 'children': [{'name': [163.66666666666666], 'children': [{'name': u'Napa Valley, Organic Extra Virgin Olive Oil, 25.4 oz'}]}]}, {'name': 157.0, 'children': [{'name': [164.0], 'children': [{'name': u'Muir Glen Organic Italian Herb Pasta Sauce, 25.5 oz'}]}]}, {'name': 228.5, 'children': [{'name': [242.5], 'children': [{'name': u'Ziploc Freezer Bags Value Pack, Quart Size, 38 ct'}]}]}]}]}    # dict = {
    #  "name": "flare",
    #  "children": [
    #   {
    #    "name": "analytics",
    #    "children": [
    #     {
    #      "name": "cluster",
    #      "children": [
    #       {"name": "Blah, blah, blah, blah, blah"},
    #       {"name": "Blah, blah, blah, blah, blah"},
    #       {"name": "Blah, blah, blah, blah, blah"},
    #       {"name": "Blah, blah, blah, blah, blah"}
    #      ]
    #     },
    #     {
    #      "name": "graph",
    #      "children": [
    #       {"name": "BetweennessCentrality"},
    #       {"name": "LinkDistance"},
    #       {"name": "MaxFlowMinCut"},
    #       {"name": "ShortestPaths"},
    #       {"name": "SpanningTree"}
    #      ]
    #     },
    #     {
    #      "name": "optimization",
    #      "children": [
    #       {"name": "AspectRatioBanker", "size": 7074}
    #      ]
    #     }
    #    ]
    #   },
    #   {
    #    "name": "animate",
    #    "children": [
    #     {"name": "Easing", "size": 17010},
    #     {"name": "FunctionSequence", "size": 5842},
    #     {
    #      "name": "interpolate",
    #      "children": [
    #       {"name": "ArrayInterpolator", "size": 1983},
    #       {"name": "ColorInterpolator", "size": 2047},
    #       {"name": "DateInterpolator", "size": 1375},
    #       {"name": "Interpolator", "size": 8746},
    #       {"name": "MatrixInterpolator", "size": 2202},
    #       {"name": "NumberInterpolator", "size": 1382},
    #       {"name": "ObjectInterpolator", "size": 1629},
    #       {"name": "PointInterpolator", "size": 1675},
    #       {"name": "RectangleInterpolator", "size": 2042}
    #      ]
    #     },
    #     {"name": "ISchedulable", "size": 1041},
    #     {"name": "Parallel", "size": 5176},
    #     {"name": "Pause", "size": 449},
    #     {"name": "Scheduler", "size": 5593},
    #     {"name": "Sequence", "size": 5534},
    #     {"name": "Transition", "size": 9201},
    #     {"name": "Transitioner", "size": 19975},
    #     {"name": "TransitionEvent", "size": 1116},
    #     {"name": "Tween", "size": 6006}
    #    ]
    #   },
    #   {
    #    "name": "data",
    #    "children": [
    #     {
    #      "name": "converters",
    #      "children": [
    #       {"name": "Converters", "size": 721},
    #       {"name": "DelimitedTextConverter", "size": 4294},
    #       {"name": "GraphMLConverter", "size": 9800},
    #       {"name": "IDataConverter", "size": 1314},
    #       {"name": "JSONConverter", "size": 2220}
    #      ]
    #     },
    #     {"name": "DataField", "size": 1759},
    #     {"name": "DataSchema", "size": 2165},
    #     {"name": "DataSet", "size": 586},
    #     {"name": "DataSource", "size": 3331},
    #     {"name": "DataTable", "size": 772},
    #     {"name": "DataUtil", "size": 3322}
    #    ]
    #   },
    #   {
    #    "name": "display",
    #    "children": [
    #     {"name": "DirtySprite", "size": 8833},
    #     {"name": "LineSprite", "size": 1732},
    #     {"name": "RectSprite", "size": 3623},
    #     {"name": "TextSprite", "size": 10066}
    #    ]
    #   },
    #   {
    #    "name": "flex",
    #    "children": [
    #     {"name": "FlareVis", "size": 4116}
    #    ]
    #   },
    #   {
    #    "name": "physics",
    #    "children": [
    #     {"name": "DragForce", "size": 1082},
    #     {"name": "GravityForce", "size": 1336},
    #     {"name": "IForce", "size": 319},
    #     {"name": "NBodyForce", "size": 10498},
    #     {"name": "Particle", "size": 2822},
    #     {"name": "Simulation", "size": 9983},
    #     {"name": "Spring", "size": 2213},
    #     {"name": "SpringForce", "size": 1681}
    #    ]
    #   },
    #   {
    #    "name": "query",
    #    "children": [
    #     {"name": "AggregateExpression", "size": 1616},
    #     {"name": "And", "size": 1027},
    #     {"name": "Arithmetic", "size": 3891},
    #     {"name": "Average", "size": 891},
    #     {"name": "BinaryExpression", "size": 2893},
    #     {"name": "Comparison", "size": 5103},
    #     {"name": "CompositeExpression", "size": 3677},
    #     {"name": "Count", "size": 781},
    #     {"name": "DateUtil", "size": 4141},
    #     {"name": "Distinct", "size": 933},
    #     {"name": "Expression", "size": 5130},
    #     {"name": "ExpressionIterator", "size": 3617},
    #     {"name": "Fn", "size": 3240},
    #     {"name": "If", "size": 2732},
    #     {"name": "IsA", "size": 2039},
    #     {"name": "Literal", "size": 1214},
    #     {"name": "Match", "size": 3748},
    #     {"name": "Maximum", "size": 843},
    #     {
    #      "name": "methods",
    #      "children": [
    #       {"name": "add", "size": 593},
    #       {"name": "and", "size": 330},
    #       {"name": "average", "size": 287},
    #       {"name": "count", "size": 277},
    #       {"name": "distinct", "size": 292},
    #       {"name": "div", "size": 595},
    #       {"name": "eq", "size": 594},
    #       {"name": "fn", "size": 460},
    #       {"name": "gt", "size": 603},
    #       {"name": "gte", "size": 625},
    #       {"name": "iff", "size": 748},
    #       {"name": "isa", "size": 461},
    #       {"name": "lt", "size": 597},
    #       {"name": "lte", "size": 619},
    #       {"name": "max", "size": 283},
    #       {"name": "min", "size": 283},
    #       {"name": "mod", "size": 591},
    #       {"name": "mul", "size": 603},
    #       {"name": "neq", "size": 599},
    #       {"name": "not", "size": 386},
    #       {"name": "or", "size": 323},
    #       {"name": "orderby", "size": 307},
    #       {"name": "range", "size": 772},
    #       {"name": "select", "size": 296},
    #       {"name": "stddev", "size": 363},
    #       {"name": "sub", "size": 600},
    #       {"name": "sum", "size": 280},
    #       {"name": "update", "size": 307},
    #       {"name": "variance", "size": 335},
    #       {"name": "where", "size": 299},
    #       {"name": "xor", "size": 354},
    #       {"name": "_", "size": 264}
    #      ]
    #     },
    #     {"name": "Minimum", "size": 843},
    #     {"name": "Not", "size": 1554},
    #     {"name": "Or", "size": 970},
    #     {"name": "Query", "size": 13896},
    #     {"name": "Range", "size": 1594},
    #     {"name": "StringUtil", "size": 4130},
    #     {"name": "Sum", "size": 791},
    #     {"name": "Variable", "size": 1124},
    #     {"name": "Variance", "size": 1876},
    #     {"name": "Xor", "size": 1101}
    #    ]
    #   },
    #   {
    #    "name": "scale",
    #    "children": [
    #     {"name": "IScaleMap", "size": 2105},
    #     {"name": "LinearScale", "size": 1316},
    #     {"name": "LogScale", "size": 3151},
    #     {"name": "OrdinalScale", "size": 3770},
    #     {"name": "QuantileScale", "size": 2435},
    #     {"name": "QuantitativeScale", "size": 4839},
    #     {"name": "RootScale", "size": 1756},
    #     {"name": "Scale", "size": 4268},
    #     {"name": "ScaleType", "size": 1821},
    #     {"name": "TimeScale", "size": 5833}
    #    ]
    #   },
    #   {
    #    "name": "util",
    #    "children": [
    #     {"name": "Arrays", "size": 8258},
    #     {"name": "Colors", "size": 10001},
    #     {"name": "Dates", "size": 8217},
    #     {"name": "Displays", "size": 12555},
    #     {"name": "Filter", "size": 2324},
    #     {"name": "Geometry", "size": 10993},
    #     {
    #      "name": "heap",
    #      "children": [
    #       {"name": "FibonacciHeap", "size": 9354},
    #       {"name": "HeapNode", "size": 1233}
    #      ]
    #     },
    #     {"name": "IEvaluable", "size": 335},
    #     {"name": "IPredicate", "size": 383},
    #     {"name": "IValueProxy", "size": 874},
    #     {
    #      "name": "math",
    #      "children": [
    #       {"name": "DenseMatrix", "size": 3165},
    #       {"name": "IMatrix", "size": 2815},
    #       {"name": "SparseMatrix", "size": 3366}
    #      ]
    #     },
    #     {"name": "Maths", "size": 17705},
    #     {"name": "Orientation", "size": 1486},
    #     {
    #      "name": "palette",
    #      "children": [
    #       {"name": "ColorPalette", "size": 6367},
    #       {"name": "Palette", "size": 1229},
    #       {"name": "ShapePalette", "size": 2059},
    #       {"name": "SizePalette", "size": 2291}
    #      ]
    #     },
    #     {"name": "Property", "size": 5559},
    #     {"name": "Shapes", "size": 19118},
    #     {"name": "Sort", "size": 6887},
    #     {"name": "Stats", "size": 6557},
    #     {"name": "Strings", "size": 22026}
    #    ]
    #   },
    #   {
    #    "name": "vis",
    #    "children": [
    #     {
    #      "name": "axis",
    #      "children": [
    #       {"name": "Axes", "size": 1302},
    #       {"name": "Axis", "size": 24593},
    #       {"name": "AxisGridLine", "size": 652},
    #       {"name": "AxisLabel", "size": 636},
    #       {"name": "CartesianAxes", "size": 6703}
    #      ]
    #     },
    #     {
    #      "name": "controls",
    #      "children": [
    #       {"name": "AnchorControl", "size": 2138},
    #       {"name": "ClickControl", "size": 3824},
    #       {"name": "Control", "size": 1353},
    #       {"name": "ControlList", "size": 4665},
    #       {"name": "DragControl", "size": 2649},
    #       {"name": "ExpandControl", "size": 2832},
    #       {"name": "HoverControl", "size": 4896},
    #       {"name": "IControl", "size": 763},
    #       {"name": "PanZoomControl", "size": 5222},
    #       {"name": "SelectionControl", "size": 7862},
    #       {"name": "TooltipControl", "size": 8435}
    #      ]
    #     },
    #     {
    #      "name": "data",
    #      "children": [
    #       {"name": "Data", "size": 20544},
    #       {"name": "DataList", "size": 19788},
    #       {"name": "DataSprite", "size": 10349},
    #       {"name": "EdgeSprite", "size": 3301},
    #       {"name": "NodeSprite", "size": 19382},
    #       {
    #        "name": "render",
    #        "children": [
    #         {"name": "ArrowType", "size": 698},
    #         {"name": "EdgeRenderer", "size": 5569},
    #         {"name": "IRenderer", "size": 353},
    #         {"name": "ShapeRenderer", "size": 2247}
    #        ]
    #       },
    #       {"name": "ScaleBinding", "size": 11275},
    #       {"name": "Tree", "size": 7147},
    #       {"name": "TreeBuilder", "size": 9930}
    #      ]
    #     },
    #     {
    #      "name": "events",
    #      "children": [
    #       {"name": "DataEvent", "size": 2313},
    #       {"name": "SelectionEvent", "size": 1880},
    #       {"name": "TooltipEvent", "size": 1701},
    #       {"name": "VisualizationEvent", "size": 1117}
    #      ]
    #     },
    #     {
    #      "name": "legend",
    #      "children": [
    #       {"name": "Legend", "size": 20859},
    #       {"name": "LegendItem", "size": 4614},
    #       {"name": "LegendRange", "size": 10530}
    #      ]
    #     },
    #     {
    #      "name": "operator",
    #      "children": [
    #       {
    #        "name": "distortion",
    #        "children": [
    #         {"name": "BifocalDistortion", "size": 4461},
    #         {"name": "Distortion", "size": 6314},
    #         {"name": "FisheyeDistortion", "size": 3444}
    #        ]
    #       },
    #       {
    #        "name": "encoder",
    #        "children": [
    #         {"name": "ColorEncoder", "size": 3179},
    #         {"name": "Encoder", "size": 4060},
    #         {"name": "PropertyEncoder", "size": 4138},
    #         {"name": "ShapeEncoder", "size": 1690},
    #         {"name": "SizeEncoder", "size": 1830}
    #        ]
    #       },
    #       {
    #        "name": "filter",
    #        "children": [
    #         {"name": "FisheyeTreeFilter", "size": 5219},
    #         {"name": "GraphDistanceFilter", "size": 3165},
    #         {"name": "VisibilityFilter", "size": 3509}
    #        ]
    #       },
    #       {"name": "IOperator", "size": 1286},
    #       {
    #        "name": "label",
    #        "children": [
    #         {"name": "Labeler", "size": 9956},
    #         {"name": "RadialLabeler", "size": 3899},
    #         {"name": "StackedAreaLabeler", "size": 3202}
    #        ]
    #       },
    #       {
    #        "name": "layout",
    #        "children": [
    #         {"name": "AxisLayout", "size": 6725},
    #         {"name": "BundledEdgeRouter", "size": 3727},
    #         {"name": "CircleLayout", "size": 9317},
    #         {"name": "CirclePackingLayout", "size": 12003},
    #         {"name": "DendrogramLayout", "size": 4853},
    #         {"name": "ForceDirectedLayout", "size": 8411},
    #         {"name": "IcicleTreeLayout", "size": 4864},
    #         {"name": "IndentedTreeLayout", "size": 3174},
    #         {"name": "Layout", "size": 7881},
    #         {"name": "NodeLinkTreeLayout", "size": 12870},
    #         {"name": "PieLayout", "size": 2728},
    #         {"name": "RadialTreeLayout", "size": 12348},
    #         {"name": "RandomLayout", "size": 870},
    #         {"name": "StackedAreaLayout", "size": 9121},
    #         {"name": "TreeMapLayout", "size": 9191}
    #        ]
    #       },
    #       {"name": "Operator", "size": 2490},
    #       {"name": "OperatorList", "size": 5248},
    #       {"name": "OperatorSequence", "size": 4190},
    #       {"name": "OperatorSwitch", "size": 2581},
    #       {"name": "SortOperator", "size": 2023}
    #      ]
    #     },
    #     {"name": "Visualization", "size": 16540}
    #    ]
    #   }
    #  ]
    # }


    return jsonify(dict)


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
    # add redirect to "/" if not logged in? or not in demo mode?

    return render_template("freshlook.html")

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

@app.route('/demo')
def enter_demo():
    """Redirects to freshlook in demo mode"""

    session["demo_gmail"] = DEMO_GMAIL
    access_token = "demo"

    add_user(DEMO_GMAIL, "demo") # stores user_gmail and credentials token in database

    return redirect('/freshlook')

def seed_demo():
    """Seeds database in demo mode"""

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


@socketio.on('start_loading', namespace='/loads')
def load_data(data):

    if data["data"] == "proceed": # 'proceed' indicates the websocket is done connecting.
        if session.get("demo_gmail", None):
            seed_demo()

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
    print "Client disconnected"

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
