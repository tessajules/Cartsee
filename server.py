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
    x = {
     "name": "flare",
     "children": [
      {
       "name": "analytics",
       "children": [
        {
         "name": "cluster",
         "children": [
          {"name": "AgglomerativeCluster", "size": 3938},
          {"name": "CommunityStructure", "size": 3812},
          {"name": "HierarchicalCluster", "size": 6714},
          {"name": "MergeEdge", "size": 743}
         ]
        },
        {
         "name": "graph",
         "children": [
          {"name": "BetweennessCentrality", "size": 3534},
          {"name": "LinkDistance", "size": 5731},
          {"name": "MaxFlowMinCut", "size": 7840},
          {"name": "ShortestPaths", "size": 5914},
          {"name": "SpanningTree", "size": 3416}
         ]
        },
        {
         "name": "optimization",
         "children": [
          {"name": "AspectRatioBanker", "size": 7074}
         ]
        }
       ]
      },
      {
       "name": "animate",
       "children": [
        {"name": "Easing", "size": 17010},
        {"name": "FunctionSequence", "size": 5842},
        {
         "name": "interpolate",
         "children": [
          {"name": "ArrayInterpolator", "size": 1983},
          {"name": "ColorInterpolator", "size": 2047},
          {"name": "DateInterpolator", "size": 1375},
          {"name": "Interpolator", "size": 8746},
          {"name": "MatrixInterpolator", "size": 2202},
          {"name": "NumberInterpolator", "size": 1382},
          {"name": "ObjectInterpolator", "size": 1629},
          {"name": "PointInterpolator", "size": 1675},
          {"name": "RectangleInterpolator", "size": 2042}
         ]
        },
        {"name": "ISchedulable", "size": 1041},
        {"name": "Parallel", "size": 5176},
        {"name": "Pause", "size": 449},
        {"name": "Scheduler", "size": 5593},
        {"name": "Sequence", "size": 5534},
        {"name": "Transition", "size": 9201},
        {"name": "Transitioner", "size": 19975},
        {"name": "TransitionEvent", "size": 1116},
        {"name": "Tween", "size": 6006}
       ]
      },
      {
       "name": "data",
       "children": [
        {
         "name": "converters",
         "children": [
          {"name": "Converters", "size": 721},
          {"name": "DelimitedTextConverter", "size": 4294},
          {"name": "GraphMLConverter", "size": 9800},
          {"name": "IDataConverter", "size": 1314},
          {"name": "JSONConverter", "size": 2220}
         ]
        },
        {"name": "DataField", "size": 1759},
        {"name": "DataSchema", "size": 2165},
        {"name": "DataSet", "size": 586},
        {"name": "DataSource", "size": 3331},
        {"name": "DataTable", "size": 772},
        {"name": "DataUtil", "size": 3322}
       ]
      },
      {
       "name": "display",
       "children": [
        {"name": "DirtySprite", "size": 8833},
        {"name": "LineSprite", "size": 1732},
        {"name": "RectSprite", "size": 3623},
        {"name": "TextSprite", "size": 10066}
       ]
      },
      {
       "name": "flex",
       "children": [
        {"name": "FlareVis", "size": 4116}
       ]
      },
      {
       "name": "physics",
       "children": [
        {"name": "DragForce", "size": 1082},
        {"name": "GravityForce", "size": 1336},
        {"name": "IForce", "size": 319},
        {"name": "NBodyForce", "size": 10498},
        {"name": "Particle", "size": 2822},
        {"name": "Simulation", "size": 9983},
        {"name": "Spring", "size": 2213},
        {"name": "SpringForce", "size": 1681}
       ]
      },
      {
       "name": "query",
       "children": [
        {"name": "AggregateExpression", "size": 1616},
        {"name": "And", "size": 1027},
        {"name": "Arithmetic", "size": 3891},
        {"name": "Average", "size": 891},
        {"name": "BinaryExpression", "size": 2893},
        {"name": "Comparison", "size": 5103},
        {"name": "CompositeExpression", "size": 3677},
        {"name": "Count", "size": 781},
        {"name": "DateUtil", "size": 4141},
        {"name": "Distinct", "size": 933},
        {"name": "Expression", "size": 5130},
        {"name": "ExpressionIterator", "size": 3617},
        {"name": "Fn", "size": 3240},
        {"name": "If", "size": 2732},
        {"name": "IsA", "size": 2039},
        {"name": "Literal", "size": 1214},
        {"name": "Match", "size": 3748},
        {"name": "Maximum", "size": 843},
        {
         "name": "methods",
         "children": [
          {"name": "add", "size": 593},
          {"name": "and", "size": 330},
          {"name": "average", "size": 287},
          {"name": "count", "size": 277},
          {"name": "distinct", "size": 292},
          {"name": "div", "size": 595},
          {"name": "eq", "size": 594},
          {"name": "fn", "size": 460},
          {"name": "gt", "size": 603},
          {"name": "gte", "size": 625},
          {"name": "iff", "size": 748},
          {"name": "isa", "size": 461},
          {"name": "lt", "size": 597},
          {"name": "lte", "size": 619},
          {"name": "max", "size": 283},
          {"name": "min", "size": 283},
          {"name": "mod", "size": 591},
          {"name": "mul", "size": 603},
          {"name": "neq", "size": 599},
          {"name": "not", "size": 386},
          {"name": "or", "size": 323},
          {"name": "orderby", "size": 307},
          {"name": "range", "size": 772},
          {"name": "select", "size": 296},
          {"name": "stddev", "size": 363},
          {"name": "sub", "size": 600},
          {"name": "sum", "size": 280},
          {"name": "update", "size": 307},
          {"name": "variance", "size": 335},
          {"name": "where", "size": 299},
          {"name": "xor", "size": 354},
          {"name": "_", "size": 264}
         ]
        },
        {"name": "Minimum", "size": 843},
        {"name": "Not", "size": 1554},
        {"name": "Or", "size": 970},
        {"name": "Query", "size": 13896},
        {"name": "Range", "size": 1594},
        {"name": "StringUtil", "size": 4130},
        {"name": "Sum", "size": 791},
        {"name": "Variable", "size": 1124},
        {"name": "Variance", "size": 1876},
        {"name": "Xor", "size": 1101}
       ]
      },
      {
       "name": "scale",
       "children": [
        {"name": "IScaleMap", "size": 2105},
        {"name": "LinearScale", "size": 1316},
        {"name": "LogScale", "size": 3151},
        {"name": "OrdinalScale", "size": 3770},
        {"name": "QuantileScale", "size": 2435},
        {"name": "QuantitativeScale", "size": 4839},
        {"name": "RootScale", "size": 1756},
        {"name": "Scale", "size": 4268},
        {"name": "ScaleType", "size": 1821},
        {"name": "TimeScale", "size": 5833}
       ]
      },
      {
       "name": "util",
       "children": [
        {"name": "Arrays", "size": 8258},
        {"name": "Colors", "size": 10001},
        {"name": "Dates", "size": 8217},
        {"name": "Displays", "size": 12555},
        {"name": "Filter", "size": 2324},
        {"name": "Geometry", "size": 10993},
        {
         "name": "heap",
         "children": [
          {"name": "FibonacciHeap", "size": 9354},
          {"name": "HeapNode", "size": 1233}
         ]
        },
        {"name": "IEvaluable", "size": 335},
        {"name": "IPredicate", "size": 383},
        {"name": "IValueProxy", "size": 874},
        {
         "name": "math",
         "children": [
          {"name": "DenseMatrix", "size": 3165},
          {"name": "IMatrix", "size": 2815},
          {"name": "SparseMatrix", "size": 3366}
         ]
        },
        {"name": "Maths", "size": 17705},
        {"name": "Orientation", "size": 1486},
        {
         "name": "palette",
         "children": [
          {"name": "ColorPalette", "size": 6367},
          {"name": "Palette", "size": 1229},
          {"name": "ShapePalette", "size": 2059},
          {"name": "SizePalette", "size": 2291}
         ]
        },
        {"name": "Property", "size": 5559},
        {"name": "Shapes", "size": 19118},
        {"name": "Sort", "size": 6887},
        {"name": "Stats", "size": 6557},
        {"name": "Strings", "size": 22026}
       ]
      },
      {
       "name": "vis",
       "children": [
        {
         "name": "axis",
         "children": [
          {"name": "Axes", "size": 1302},
          {"name": "Axis", "size": 24593},
          {"name": "AxisGridLine", "size": 652},
          {"name": "AxisLabel", "size": 636},
          {"name": "CartesianAxes", "size": 6703}
         ]
        },
        {
         "name": "controls",
         "children": [
          {"name": "AnchorControl", "size": 2138},
          {"name": "ClickControl", "size": 3824},
          {"name": "Control", "size": 1353},
          {"name": "ControlList", "size": 4665},
          {"name": "DragControl", "size": 2649},
          {"name": "ExpandControl", "size": 2832},
          {"name": "HoverControl", "size": 4896},
          {"name": "IControl", "size": 763},
          {"name": "PanZoomControl", "size": 5222},
          {"name": "SelectionControl", "size": 7862},
          {"name": "TooltipControl", "size": 8435}
         ]
        },
        {
         "name": "data",
         "children": [
          {"name": "Data", "size": 20544},
          {"name": "DataList", "size": 19788},
          {"name": "DataSprite", "size": 10349},
          {"name": "EdgeSprite", "size": 3301},
          {"name": "NodeSprite", "size": 19382},
          {
           "name": "render",
           "children": [
            {"name": "ArrowType", "size": 698},
            {"name": "EdgeRenderer", "size": 5569},
            {"name": "IRenderer", "size": 353},
            {"name": "ShapeRenderer", "size": 2247}
           ]
          },
          {"name": "ScaleBinding", "size": 11275},
          {"name": "Tree", "size": 7147},
          {"name": "TreeBuilder", "size": 9930}
         ]
        },
        {
         "name": "events",
         "children": [
          {"name": "DataEvent", "size": 2313},
          {"name": "SelectionEvent", "size": 1880},
          {"name": "TooltipEvent", "size": 1701},
          {"name": "VisualizationEvent", "size": 1117}
         ]
        },
        {
         "name": "legend",
         "children": [
          {"name": "Legend", "size": 20859},
          {"name": "LegendItem", "size": 4614},
          {"name": "LegendRange", "size": 10530}
         ]
        },
        {
         "name": "operator",
         "children": [
          {
           "name": "distortion",
           "children": [
            {"name": "BifocalDistortion", "size": 4461},
            {"name": "Distortion", "size": 6314},
            {"name": "FisheyeDistortion", "size": 3444}
           ]
          },
          {
           "name": "encoder",
           "children": [
            {"name": "ColorEncoder", "size": 3179},
            {"name": "Encoder", "size": 4060},
            {"name": "PropertyEncoder", "size": 4138},
            {"name": "ShapeEncoder", "size": 1690},
            {"name": "SizeEncoder", "size": 1830}
           ]
          },
          {
           "name": "filter",
           "children": [
            {"name": "FisheyeTreeFilter", "size": 5219},
            {"name": "GraphDistanceFilter", "size": 3165},
            {"name": "VisibilityFilter", "size": 3509}
           ]
          },
          {"name": "IOperator", "size": 1286},
          {
           "name": "label",
           "children": [
            {"name": "Labeler", "size": 9956},
            {"name": "RadialLabeler", "size": 3899},
            {"name": "StackedAreaLabeler", "size": 3202}
           ]
          },
          {
           "name": "layout",
           "children": [
            {"name": "AxisLayout", "size": 6725},
            {"name": "BundledEdgeRouter", "size": 3727},
            {"name": "CircleLayout", "size": 9317},
            {"name": "CirclePackingLayout", "size": 12003},
            {"name": "DendrogramLayout", "size": 4853},
            {"name": "ForceDirectedLayout", "size": 8411},
            {"name": "IcicleTreeLayout", "size": 4864},
            {"name": "IndentedTreeLayout", "size": 3174},
            {"name": "Layout", "size": 7881},
            {"name": "NodeLinkTreeLayout", "size": 12870},
            {"name": "PieLayout", "size": 2728},
            {"name": "RadialTreeLayout", "size": 12348},
            {"name": "RandomLayout", "size": 870},
            {"name": "StackedAreaLayout", "size": 9121},
            {"name": "TreeMapLayout", "size": 9191}
           ]
          },
          {"name": "Operator", "size": 2490},
          {"name": "OperatorList", "size": 5248},
          {"name": "OperatorSequence", "size": 4190},
          {"name": "OperatorSwitch", "size": 2581},
          {"name": "SortOperator", "size": 2023}
         ]
        },
        {"name": "Visualization", "size": 16540}
       ]
      }
     ]
    }
    # http://bl.ocks.org/d3noob/13a36f70a4f060b97e41
    return jsonify(data=x)

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

    # date_close_list = []
    # for order in user.package_orders_for_area_chart():
    #     date_close = jsonify(date=order["date"], close=order["close"])

    # return jsonify(date=[jsonify(date=order["date"], close=order["close"]) for order in user.package_orders_for_area_chart()])
    return jsonify(data=user.serialize_orders_for_area_chart())
    # return Response(json.dumps(user.package_orders_for_area_chart2()),  mimetype='application/json')
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
