"""Utility file to parse email message data and seed freshlook database"""

from model import Order, OrderLineItem, SavedCartItem, Item, SavedCart, User, db
import re
from datetime import datetime


def store_user(user_gmail, access_token):
    """Adds authenticated user gmail address to database"""

    user = User(user_gmail=user_gmail, access_token=access_token)

    db.session.add(user)
    db.session.commit()

    print "Current authenticated gmail user added to database"



def parse_email_message(email_message):
    """Parses one email message (each of which contains one order) to get extractable data"""
    # TODO:  Might need to add conditional later on to my gmail api method call that only grabs the root email so
    # that I don't get multiple messages for the same order (if the same order shows up multiple times in a
    # forwarded thread, for example) I can't do this now b/c all my emails are forwarded form Jeff's inbox so it's all one long thread.

    line_items_one_order = []

    order_number_string = re.search('#\s\d{3}-\d{7}-\d{7}.', email_message).group(0)[2:]
        # finds the AmazonFresh order number and cuts off the '# ' before the number

    delivery_date_time_string = str(re.search('\d+:\d{2}[apm](.*?)20\d{2}', email_message, re.DOTALL).group(0))
        # finds the delivery time range and date string of the order

    delivery_date_time_list = delivery_date_time_string.replace('\n', ' ').replace('\r', '').strip().split(", ")

    delivery_time, delivery_day_of_week, delivery_date = delivery_date_time_list

    delivery_date = datetime.strptime(delivery_date, "%d %B %Y")

    items_string = re.search('FULFILLED AS ORDERED \*\*\*\r.*\r\n\r\nSubtotal:', email_message, re.DOTALL).group(0)
    # finds the string that includes the line items of the order in the email message
    # needed to rule out the weirdly formatted html strings also coming out.  These ended in <br>\r\nSubtotal

    order_parser = re.compile(r'\r\n\r\n')
    line_items_list = order_parser.split(items_string) # splits block of items from order_string into a list of line item strings

    line_item_parser = re.compile(r'\s{3,}')

    item_description_parser = re.compile(r'\r\n')

    for line_item_string in line_items_list: # iterate through list of line items from one order

            line_item_info = line_item_parser.split(line_item_string.strip())[1:] # strip remaining \n off of each line_item_string and split
                # each line item string into one list of [fulfilled qty (string), line item total ($string), line item description (string)].
                # (Leaving out the 0th in the list, ordered qty (string), because I don't need it.)

            if len(line_item_info) == 3 and line_item_info[0] != "Qty Fulfilled": # if there are exactly three items in the list and is not the header
                fulfilled_qty = int(line_item_info[0]) # change fulfilled quanitity to integer
                unit_price =  (float(line_item_info[1][1:]))/fulfilled_qty # change line item total to unit price as float
                item_description = line_item_info[2] # item_description is the string in the list (last item in list)
                if "\r\n" in item_description:
                    item_description =   " ".join(item_description_parser.split(item_description)) # if item_description has \r\n then get rid of \r\n

                line_items_one_order.append([fulfilled_qty, unit_price, item_description]) # append re-formatted line item info as list to list_items_one_email

    return order_number_string, line_items_one_order, delivery_time, delivery_day_of_week, delivery_date


# TODO:  figure out where to make the db session and engine and stuff

# from sqlalchemy import create_engine
# Base.metadata.create_all(engine)
# DB_URI = "sqlite:///freshlook.db"
# engine = create_engine(DB_URI, echo=True)
# from sqlalchemy.orm import sessionmaker
# Session = sessionmaker(bind=engine)
# session = Session()
# ## do I need the following three lines?  I'd need to change db.Model to base...?##
# from sqlalchemy.ext.declarative import declarative_base
# Base = declarative_base()
# Base.metadata.create_all(engine)
