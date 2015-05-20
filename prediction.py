from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from model import db, Order, OrderLineItem, Item
from numpy import array, mean, std
from datetime import datetime, timedelta

def predict_cart_items(user_gmail, chosen_date_str):
    """Predicts the order total to use as cap for predicted cart"""

    # query for list of item descriptions and all the datetimes they were bought:
    descriptions_dates_list = db.session.query(Item.description,
                                    Order.delivery_date).join(
                                    OrderLineItem).join(Order).filter(Order.user_gmail==user_gmail).all()

    # put item descriptions and datetimes into dictionary ex. {'description': [datetime1, datetime2], ...}
    descriptions_dates_map = {}
    std_freq_map = {}

    # TODO:  change this strategy to use more object oriented programming
    # for instance, description_key can be an attribute OR OBJECT METHOD?
    # list of dates can be item object method?
    # for order in item.orderlineitem.orders:
    #     date_list.append(order.delivery_date)

    # the following for loop will make the dictionary: {description_key : [description, date, date, ...]
    # description_key is made of only the alphanumeric characters in the description to rule out
    # treating two descriptions of the same item as unique because of punct or capitalization difference
    for description, delivery_date in descriptions_dates_list:
        description_key = ""
        for char in description:
            if char.isalnum(): # check if character is alpha or number
                description_key += char # if so add to description_key
        description_key = description_key.lower()

        descriptions_dates_map.setdefault(description_key, [description])
        descriptions_dates_map[description_key].append(delivery_date)

    # if last delivery has occured relatively recently AND delivery history six months or longer,
    # then limit how far back you look into delivery history to 3 months before last order
    # (implement history cutoff).  Otherwise just use all of delivery history.
    today = datetime.now() #+ timedelta(1000-5)
    # today variable used so can change today's date manually for testing.

    last_deliv_date = db.session.query(func.max(Order.delivery_date)).one()[0]
    first_deliv_date = db.session.query(func.min(Order.delivery_date)).one()[0]
    days_deliv_history = (last_deliv_date - first_deliv_date).days
    days_since_last_deliv = (today - last_deliv_date).days
    datetime_cutoff = last_deliv_date - timedelta(days=90)


    implement_history_cutoff = False
    if days_since_last_deliv < days_deliv_history and days_deliv_history > 180:
        implement_history_cutoff = True
        print "Implementing item datetime cutoff at 90 days before chosen delivery date (Last order is relatively recent and order history > 180 days.)"
    else:
        print "Datetime cutoff NOT being implemented (Order history < 180 days and/or last order occured a long time ago).)"

    # for each item, calculate mean # of days between dates ordered and standard deviation
    for description_key in descriptions_dates_map:

        # query to get the latest datetime the item was ordered:
        recent_date_query = db.session.query(func.max(Order.delivery_date)).join(
        OrderLineItem).join(Item).filter(
        Item.description==descriptions_dates_map[description_key][0]).group_by(
        Item.description).one()

        # if history cutoff being implemented and the last time the item was bought was before the
        # cutoff, move to next description_key in description dates map
        if implement_history_cutoff and recent_date_query[0] < datetime_cutoff:
            continue # continue to next item in this for loop

        if len(descriptions_dates_map[description_key][1:]) > 2: # make sure the item has been ordered @ least three times (to get at least two frequencies)
            sorted_dates = sorted(descriptions_dates_map[description_key][1:]) # sort the datetimes so can calculate days between them
            second_last = len(sorted_dates) - 2 # second to last index in sorted_dates (finding here so don't have to find for each iteration)

            frequencies = []
            for i in range(len(sorted_dates)):
                frequencies.append((sorted_dates[i + 1] - sorted_dates[i]).days) # calculate the difference between the next datetime and the current
                if i == second_last:
                    break # break completely out of this for loop

            freq_arr = array(frequencies) # need to make numpy array so can do calculations with numpy library
            mean_freq = mean(frequencies, axis=0) # calculate mean of datetime frequencies
            std_dev = std(frequencies, axis=0) # calculate standard deviation

            # query to get the latest price of the item (according to order history):
            latest_price_cents = db.session.query(OrderLineItem.unit_price_cents).join(Item).join(
            Order).filter(Order.delivery_date==recent_date_query[0], Item.description==
                          descriptions_dates_map[description_key][0]).one()[0]


            # dictionary mapping frequencies to grouped descriptions and latest price,
            # all grouped by standard deviation.  ex. {std_dev: {freq: [descript1, descript2], ...}, ...}
            std_freq_map.setdefault(std_dev, {})
            std_freq_map[std_dev].setdefault(mean_freq, [])
            std_freq_map[std_dev][mean_freq].append((descriptions_dates_map[description_key][0], latest_price_cents))

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
        chosen_datetime = last_deliv_date + timedelta(days=min(frequencies)) # to make sure prediction is possible chosen date set within frequency range
        deliv_day_diff = (chosen_datetime - last_deliv_date).days

    else:
        chosen_datetime = input_datetime

    print "CHOSEN DATETIME:", chosen_datetime
    print "INPUT DATETIME", input_datetime
    print "time between today and last deliv", (datetime.now() - last_deliv_date)
    print "if chosen_datetime reset, will be", input_datetime - (today - timedelta(days=min(frequencies)))



    # Only items that are bought with a mean frequency of at least 80% of the # of days between
    # last order and predicted order will be added to the predicted cart (w/ upper limit if implement_history_cutoff == True)
    freq_cutoff = (80 * deliv_day_diff)/100 # to get 80% of deliv_day_diff

    # TODO:  need to make a max datetime cuttof to exclude items that haven't been bought in a long time.


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
    optim_mean_qty = mean(optim_qty_arr, axis=0)
    # optim_std_qty = std(optim_qty_arr, axis=0) # not really needed, might delete this later.

    predicted_cart = []

    # go through list of std_freq_map standard deviation keys, sorted from lowest std
    # to highest std dev, and add items that are at or above the freq_cutoff

    len_optim_qty = len(optim_qty) # to check against before adding items to cart

    for std_dev in sorted(std_freq_map):
        for mean_freq in std_freq_map[std_dev]: # iterate through frequency keys
            if mean_freq >= freq_cutoff:
                spaces_left = len_optim_qty - len(predicted_cart)
                if len(std_freq_map[std_dev][mean_freq]) >= spaces_left:
                    predicted_cart.extend(std_freq_map[std_dev][mean_freq][:spaces_left])
                    if predicted_cart:
                        print predicted_cart
                    return predicted_cart
                predicted_cart.extend(std_freq_map[std_dev][mean_freq])

    print "Predicted cart is empty; is type", type(predicted_cart)


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app, connect_to_db
    connect_to_db(app, db, "freshlook.db")


    # TODO:  figure out where to put create the engine and the session
    # engine = create_engine(DB_URI, echo=True)
