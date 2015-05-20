from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from model import db, Order, OrderLineItem, Item
from numpy import array, mean, std
from datetime import datetime

def predict_cart_items(user_gmail, chosen_date_str):
    """Predicts the order total to use as cap for predicted cart"""

    # query for list of item descriptions and all the datetimes they were bought:
    descriptions_dates_list = db.session.query(Item.description,
                                    Order.delivery_date).join(
                                    OrderLineItem).join(Order).filter(Order.user_gmail==user_gmail).all()

    # put item descriptions and datetimes into dictionary ex. {'description': [datetime1, datetime2], ...}
    descriptions_dates_map = {}
    std_freq_map = {}

    for description, delivery_date in descriptions_dates_list:
        descriptions_dates_map.setdefault(description, [])
        descriptions_dates_map[description].append(delivery_date)

    # for each item, calculate mean # of days between dates ordered and standard deviation
    for description in descriptions_dates_map:

        if len(descriptions_dates_map[description]) > 2: # make sure the item has been ordered @ least three times (to get at least two frequencies)
            sorted_dates = sorted(descriptions_dates_map[description]) # sort the datetimes so can calculate days between them
            second_last = len(sorted_dates) - 2 # second to last index in sorted_dates (finding here so don't have to find for each iteration)

            frequencies = []
            for i in range(len(sorted_dates)):
                frequencies.append((sorted_dates[i + 1] - sorted_dates[i]).days) # calculate the difference between the next datetime and the current
                if i == second_last:
                    break
            freq_arr = array(frequencies) # need to make numpy array so can do calculations with numpy library
            mean_freq = mean(frequencies, axis=0) # calculate mean of datetime frequencies
            std_dev = std(frequencies, axis=0) # calculate standard deviation

            # queries to get the latest price of the item:
            recent_date_query = db.session.query(func.max(Order.delivery_date)).join(
            OrderLineItem).join(Item).filter(Item.description==description).group_by(
            Item.description).one()

            latest_price_cents = db.session.query(OrderLineItem.unit_price_cents).join(Item).join(
            Order).filter(Order.delivery_date==recent_date_query[0], Item.description==description).one()[0]

            # dictionary grouping descriptions with their latest price by standard deviation
            std_freq_map.setdefault(mean_freq, [])
            std_freq_map[mean_freq].append((description, latest_price_cents))

    # convert the date user wants predicted order to be delivered to datetime and
    # calculate the number of days between the last order and the predicted order
    chosen_datetime = datetime.strptime(chosen_date_str, "%m/%d/%y")
    # TODO:  this assumes chosen_date_str is input by user as "mm/dd/yy".  Make sure HTML reflects this.
    last_deliv_date = db.session.query(func.max(Order.delivery_date)).one()[0]
    deliv_day_diff = (chosen_datetime - last_deliv_date).days # deliv_day_diff is integer

    # Only items that are bought with a mean frequency of at least 80% of the # of days between
    # last order and predicted order will be added to the predicted cart:
    freq_cutoff = (80 * deliv_day_diff)/100 # to get 80% of deliv_day_diff

    # get average qty of items per order to set cutoff of predicted cart
    tups_items_orders = db.session.query(func.count(OrderLineItem.order_line_item_id)).join(Order).group_by(Order.amazon_fresh_order_id).all()

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
    optim_std_qty = std(optim_qty_arr, axis=0) # not really needed, might delete this later.

    predicted_cart = []

    # for std_dev in sorted(std_freq_map): # sorted so descriptions with matching freq with
                                         # lowest std dev are added to list first

    # make a dictionary of each order's position in order_datetimes as key,
    # with the order total as the value.  No need to store the order #

    # grab order list for user.

    # user = User.query.filter_by(user_gmail=auth_user['emailAddress']).one()

    # for order in user.orders:


    return "blah"


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app, connect_to_db
    connect_to_db(app, db, "freshlook.db")


    # TODO:  figure out where to put create the engine and the session
    # engine = create_engine(DB_URI, echo=True)
