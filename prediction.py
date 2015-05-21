from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from model import db, Order, OrderLineItem, Item
from numpy import array, mean, std
from datetime import datetime, timedelta

def calc_predicted_qty():
    """Finds the upper limit for number of items that will go in the predicted
    cart based on the average quantities of items across order history"""

    # get average qty of items per order to set cutoff of predicted cart
    tups_items_orders = db.session.query(func.count(OrderLineItem.order_line_item_id)).join(
    Order).group_by(Order.amazon_fresh_order_id).all()

    qty_items_orders = []

    for qty in tups_items_orders:
        qty_items_orders.append(qty[0]) # to get a list of line item total quants

    # calculate the mean order size
    qty_items_orders_arr = array(qty_items_orders)
    mean_qty = mean(qty_items_orders_arr, axis=0)
    std_qty = std(qty_items_orders_arr, axis=0)

    optim_qty = []

    # calculate the optimized mean order size (throw out outliers above or below std dev)
    for qty in qty_items_orders:
        if qty <= mean_qty + std_qty and qty >= mean_qty - std_qty:
            optim_qty.append(qty)

    optim_qty_arr = array(optim_qty)
    optim_mean_qty = int(mean(optim_qty_arr, axis=0))
    return optim_mean_qty

def add_items_to_cart(optim_mean_qty, std_freq_map, freq_cutoff):
    """Adds items to predicted cart that meet the frequency cutoff, starting from lowest
    standard deviation to highest, up to the historical mean cart size"""

    predicted_cart = []

    for std_dev in sorted(std_freq_map):
        for mean_freq in std_freq_map[std_dev]: # iterate through frequency keys
            if mean_freq >= freq_cutoff:
                spaces_left = optim_mean_qty - len(predicted_cart)

                if len(std_freq_map[std_dev][mean_freq]) >= spaces_left:
                    predicted_cart.extend(std_freq_map[std_dev][mean_freq][:spaces_left])
                    return predicted_cart
                predicted_cart.extend(std_freq_map[std_dev][mean_freq])

    print "Sorry, we cannot predict your next Amazon Fresh cart at this time."

def set_cart_date(chosen_date_str, last_deliv_date, days_deliv_history, frequencies):
    """Gets the date the user input for predicted cart delivery, possibly adjusting it
    if too much time has passed since last delivery"""

    # convert the date user wants predicted order to be delivered to datetime and
    # calculate the number of days between the last order and the predicted order
    input_datetime = datetime.strptime(chosen_date_str, "%m/%d/%y")
    # TODO:  this assumes chosen_date_str is input by user as "mm/dd/yy".  Make sure HTML reflects this.

    # difference betwen last deliv. date & predicted.  deliv_day_diff is integer
    deliv_day_diff = (input_datetime - last_deliv_date).days

    # if the time since your last delivery is greater than your entire delivery
    # history, the algorithm won't work.  So here the chosen datetime for the
    # predicted cart is shifted to act as if the orders occured more recently.
    # This will all be hidden from the user.
    if deliv_day_diff >= days_deliv_history:
        adjusted_datetime = last_deliv_date + timedelta(days=min(frequencies)) # to make sure prediction is possible chosen date set within frequency range
        deliv_day_diff = (adjusted_datetime - last_deliv_date).days

    else:
        adjusted_datetime = input_datetime

    return adjusted_datetime, deliv_day_diff

def add_item_info(frequencies, recent_date_query, descriptions_dates_map, item_id, std_freq_map):
    """Adds the mean frequency & standard deviation, and latest price of the current item
    to the std_dev_map"""

    freq_arr = array(frequencies) # need to make numpy array so can do calculations with numpy library
    mean_freq = mean(frequencies, axis=0) # calculate mean of datetime frequencies
    std_dev = std(frequencies, axis=0) # calculate standard deviation

    # query to get the latest price of the item (according to order history):
    latest_price_cents = db.session.query(OrderLineItem.unit_price_cents).join(Item).join(
    Order).filter(Order.delivery_date==recent_date_query[0], Item.description==
                  descriptions_dates_map[item_id][0]).one()[0]


    # dictionary mapping frequencies to grouped descriptions and latest price,
    # all grouped by standard deviation.  ex. {std_dev: {freq: [descript1, descript2], ...}, ...}
    std_freq_map.setdefault(std_dev, {})
    std_freq_map[std_dev].setdefault(mean_freq, [])
    std_freq_map[std_dev][mean_freq].append((descriptions_dates_map[item_id][0], latest_price_cents))

def build_std_freq_map(descriptions_dates_map, implement_history_cutoff, last_deliv_date):
    """Builds a dictionary of standard deviation keys mapped to their mean frequencies, with
    item descriptions matching the frequencies listed under respective mean frequency"""
    std_freq_map = {}

    # for each item, calculate mean # of days between dates ordered and standard deviation
    for item_id in descriptions_dates_map:

        # query to get the latest datetime the item was ordered:
        recent_date_query = db.session.query(func.max(Order.delivery_date)).join(
        OrderLineItem).join(Item).filter(
        Item.description==descriptions_dates_map[item_id][0]).group_by(
        Item.description).one()

        # if history cutoff being implemented and the last time the item was bought was before the
        # cutoff, move to next item_id in description dates map
        if implement_history_cutoff:
            datetime_cutoff = last_deliv_date - timedelta(days=90)
            if recent_date_query[0] < datetime_cutoff:
                continue # continue to next item in this for loop

        if len(descriptions_dates_map[item_id][1:]) > 2: # make sure the item has been ordered @ least three times (to get at least two frequencies)
            sorted_dates = sorted(descriptions_dates_map[item_id][1:]) # sort the datetimes so can calculate days between them
            second_last = len(sorted_dates) - 2 # second to last index in sorted_dates (finding here so don't have to find for each iteration)

            frequencies = []
            for i in range(len(sorted_dates)):
                frequencies.append((sorted_dates[i + 1] - sorted_dates[i]).days) # calculate the difference between the next datetime and the current
                if i == second_last:
                    break # break completely out of this for loop

            add_item_info(frequencies, recent_date_query, descriptions_dates_map, item_id, std_freq_map)
    return frequencies, std_freq_map

def build_descript_dates_map(user_gmail):
    """Builds a dictionary of item descriptions mapped to all the dates they were ordered by user"""

    descriptions_dates_map = {}

    # TODO:  change this strategy to use more object oriented programming for instance, item_id can be an attribute
    # OR OBJECT METHOD? list of dates can be item object method?
    # for order in item.orderlineitem.orders:
    #     date_list.append(order.delivery_date)

    # query for list of item descriptions and all the datetimes they were bought:
    descriptions_dates_list = db.session.query(Item.item_id, Item.description,
                                    Order.delivery_date).join(
                                    OrderLineItem).join(Order).filter(Order.user_gmail==user_gmail).all()

    # the following for loop will make the dictionary: {item_id : [description, date, date, ...]
    for item_id, description, delivery_date in descriptions_dates_list:
        descriptions_dates_map.setdefault(item_id, [description])
        descriptions_dates_map[item_id].append(delivery_date)

    return descriptions_dates_map

def determ_history_cutoff():
    """Determines whether should implement a cutoff of items last delivered before a
    certain datetime; if so, sets datetime_cutoff to that datetime """
    # if last delivery has occured relatively recently AND delivery history six months or longer,
    # then limit how far back you look into delivery history to 3 months before last order
    # (implement history cutoff).  Otherwise just use all of delivery history.
    today = datetime.now() #+ timedelta(1000-5)
    # today variable used so can change today's date manually for testing.

    last_deliv_date = db.session.query(func.max(Order.delivery_date)).one()[0]
    first_deliv_date = db.session.query(func.min(Order.delivery_date)).one()[0]
    days_deliv_history = (last_deliv_date - first_deliv_date).days
    days_since_last_deliv = (today - last_deliv_date).days

    implement_history_cutoff = False
    if days_since_last_deliv < days_deliv_history and days_deliv_history > 180:
        implement_history_cutoff = True
        print "Implementing item datetime cutoff at 90 days before chosen delivery date (Last order is relatively recent and order history > 180 days.)"
    else:
        print "Datetime cutoff NOT being implemented (Order history < 180 days and/or last order occured a long time ago).)"

    return last_deliv_date, days_deliv_history, implement_history_cutoff


def build_predicted_cart(user_gmail, chosen_date_str):
    """Populates and returns predicted cart"""

    last_deliv_date, days_deliv_history, implement_history_cutoff = determ_history_cutoff()

    descriptions_dates_map = build_descript_dates_map(user_gmail)

    frequencies, std_freq_map = build_std_freq_map(descriptions_dates_map, implement_history_cutoff, last_deliv_date)

    adjusted_datetime, deliv_day_diff = set_cart_date(chosen_date_str, last_deliv_date, days_deliv_history, frequencies)

    # Only items that are bought with a mean frequency of at least 80% of the # of days between
    # last order and predicted order will be added to the predicted cart (w/ upper limit if implement_history_cutoff == True)
    freq_cutoff = (80 * deliv_day_diff)/100 # to get 80% of deliv_day_diff

    optim_mean_qty = calc_predicted_qty()

    return add_items_to_cart(optim_mean_qty, std_freq_map, freq_cutoff) # returns final predicted cart

if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app, connect_to_db
    connect_to_db(app, db, "freshlook.db")


    # TODO:  figure out where to put create the engine and the session
    # engine = create_engine(DB_URI, echo=True)
