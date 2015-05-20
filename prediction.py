from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from model import db, Order, OrderLineItem, Item
from numpy import array, mean, std

def predict_cart_items(user_gmail):
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

            recent_date_query = db.session.query(func.max(Order.delivery_date)).join(
            OrderLineItem).join(Item).filter(Item.description==description).group_by(
            Item.description).one()

            latest_price_cents = db.session.query(OrderLineItem.unit_price_cents).join(Item).join(
            Order).filter(Order.delivery_date==recent_date_query[0], Item.description==description).one()[0]

            std_freq_map.setdefault(mean_freq, [])
            std_freq_map[mean_freq].append((description, latest_price_cents))

    print std_freq_map











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
