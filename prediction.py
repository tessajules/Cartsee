from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from model import db, Order, OrderLineItem

def predict_order_total(user_gmail):
    """Predicts the order total to use as cap for predicted cart"""

    # query for list of orders & order totals sorted by datetime:
    # orders_datetimes = db.session.query(Order.delivery_date, func.sum(
    #                                    OrderLineItem.unit_price_cents)).join(
    #                                    OrderLineItem).filter(
    #                                    Order.user_gmail==user_gmail).group_by(
    #                                    Order.amazon_fresh_order_id).order_by(
    #                                    Order.delivery_date).all()

    # query for list of item descriptions, the orders they were bought in, and their max price
    latest_price = db.session.query(OrderLineItem.unit_price_cents.filter(Item.description == Item.description,
                                    Order.delivery_date == func.max(Order.delivery_date)).one()
    )
    orders_items = db.session.query(Item.description,
                                    Order.delivery_date, OrderLineItem.unit_price_cents).join(
                                    OrderLineItem).join(Order).filter(Order.user_gmail=="acastanieto@gmail.com").all()



    # make a dictionary of each order's position in order_datetimes as key,
    # with the order total as the value.  No need to store the order #

    # grab order list for user.

    # user = User.query.filter_by(user_gmail=auth_user['emailAddress']).one()

    # for order in user.orders:


    return orders_datetimes


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app, connect_to_db
    connect_to_db(app, db, "freshlook.db")


    # TODO:  figure out where to put create the engine and the session
    # engine = create_engine(DB_URI, echo=True)
