from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from model import db, User

def predict_order_total(user_gmail):
    """Predicts the order total to use as cap for predicted cart"""

    # query for list of orders sorted by datetime:
    order_datetimes = db.session.query(Order.amazon_fresh_order_id,
                                       Order.delivery_date, func.sum(
                                       OrderLineItem.unit_price_cents)).join(OrderLineItem).group_by(
                                       Order.amazon_fresh_order_id).order_by(
                                       Order.delivery_date).all()

    # grab order list for user.

    # user = User.query.filter_by(user_gmail=auth_user['emailAddress']).one()

    # for order in user.orders:


    # return order_datetimes


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app, connect_to_db
    connect_to_db(app, db, "freshlook.db")


    # TODO:  figure out where to put create the engine and the session
    # engine = create_engine(DB_URI, echo=True)
