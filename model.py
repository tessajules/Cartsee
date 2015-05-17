"""Models and database functions for Fresh Look"""

from flask_sqlalchemy import SQLAlchemy

# from flask import jsonify

from datetime import datetime

db = SQLAlchemy()

class Order(db.Model):
    """Amazon Fresh Order"""

    __tablename__ = "orders"

    amazon_fresh_order_id = db.Column(db.String(30), primary_key=True)
    delivery_date = db.Column(db.DateTime, nullable=False)
    delivery_day_of_week = db.Column(db.String(10), nullable=False)
    delivery_time = db.Column(db.String(30), nullable=False)
    user_gmail = db.Column(db.String(64), db.ForeignKey('users.user_gmail'), nullable=False)

    user = db.relationship("User", backref=db.backref("orders", order_by=amazon_fresh_order_id))

    def calc_order_total(self):
        """Calculates total $ for all line items bought in order"""
        order_total = 0
        for line_item in self.order_line_items:
            order_total += (line_item.unit_price_cents * line_item.quantity)
        return order_total

    def serialize(self):
        """Converts attributes of order object to serialized form convertable to json"""
        return {
            'amazon_fresh_order_id': self.amazon_fresh_order_id,
            'delivery_date': self.delivery_date.strftime("%B %d, %Y"),
            'delivery_day_of_week': self.delivery_day_of_week,
            'delivery_time': self.delivery_time,
            'user_gmail': self.user_gmail,
            'order_line_items_serialized': [order_line_item.serialize() for order_line_item in self.order_line_items],
            'order_total': self.calc_order_total()
        }



    def __repr__(self):
        """Representation string"""

        return "<Order amazon_fresh_order_id=%s>" % self.amazon_fresh_order_id


class OrderLineItem(db.Model):
    """Line item from actual Amazon Fresh Order"""

    __tablename__ = "order_line_items"

    order_line_item_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    amazon_fresh_order_id = db.Column(db.String(30), db.ForeignKey('orders.amazon_fresh_order_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'), nullable=False)
    unit_price_cents = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", backref=db.backref("order_line_items", order_by=order_line_item_id))
    item = db.relationship("Item", backref=db.backref("order_line_items", order_by=order_line_item_id))

    def serialize(self):
        """Converts attributes of orderlineitem object to serialized form convertable to json"""

        return {
            'order_line_item_id': self.order_line_item_id,
            'amazon_fresh_order_id': self.amazon_fresh_order_id,
            'item_id': self.item_id,
            'unit_price': self.unit_price_cents,
            'quantity': self.quantity,
            'description': self.item.description
        }

    def __repr__(self):
        """Representation string"""

        return "<OrderLineItem order_line_item_id=%d unit_price_cents=%f qty=%d description=%s>" %   (self.order_line_item_id,
                                                                                self.unit_price_cents,
                                                                                self.quantity,
                                                                                self.item.description)


class SavedCartItem(db.Model):
    """Association between Item and SavedCart"""

    __tablename__ = "saved_carts_items"

    saved_cart_item_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.item_id"), nullable=False)
    saved_cart_id = db.Column(db.Integer, db.ForeignKey("saved_carts.saved_cart_id"), nullable=False)


class Item(db.Model):
    """Item that can be in an Amazon Fresh Order"""

    __tablename__ = "items"

    item_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    description = db.Column(db.String(150), nullable=False)

    saved_carts = db.relationship("SavedCart", secondary=SavedCartItem.__tablename__, backref="items")
    # http://stackoverflow.com/questions/16028714/sqlalchemy-type-object-role-user-has-no-attribute-foreign-keys
    def __repr__(self):
        """Representation string"""

        return "<Item item_id=%d description=%s>" % (self.item_id, self.description)

class SavedCart(db.Model):
    """Cart saved by User"""

    __tablename__ = "saved_carts"

    saved_cart_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    user_gmail = db.Column(db.String(64), db.ForeignKey("users.user_gmail"), nullable=False)

    user = db.relationship("User", backref=db.backref("saved_carts", order_by=saved_cart_id))

    def __repr__(self):
        """Representation string"""

        return "<SavedCart saved_cart_id=%d user_gmail=%s>" % (self.saved_cart_id, self.user_gmail)


class User(db.Model):
    """Amazon Fresh user whose orders are being pulled in from Gmail"""

    __tablename__ = "users"

    user_gmail = db.Column(db.String(64), primary_key=True)
    access_token = db.Column(db.String(150), nullable=False)

    def package_order_date_totals(self):
        """Packages order dates and totals to display in browser"""

        amazon_fresh_order_ids = [order.amazon_fresh_order_id for order in self.orders ]

        order_date_totals = {}
        for order in self.orders:
            order_date_totals[order.amazon_fresh_order_id] = {"delivery_date": order.delivery_date.strftime("%B %d, %Y"),
                                                              "order_total": order.calc_order_total()}
        return {"amazon_fresh_order_ids": amazon_fresh_order_ids,
                "order_date_totals": order_date_totals}


    def serialize_orders_for_area_chart(self):
        """Packages order dates and totals as json to pass into D3 area chart function"""

        order_date_totals = []

        for order in self.orders:
            order_date_totals.append({"date" : order.delivery_date.strftime("%B %d, %Y"),
                                      "close" : order.calc_order_total()})

        return order_date_totals



    def __repr__(self):
        """Representation string"""

        return "<User user_gmail=%s>" % self.user_gmail


##############################################################################
# Helper functions

    # this creats session and binds session to engine? so
    # binds engine to the database and we don't need to do the following...?
    # from sqlalchemy import create_engine
    # Base.metadata.create_all(engine)
    # DB_URI = "sqlite:///freshlook.db"
    # engine = create_engine(DB_URI, echo=True)
    # from sqlalchemy.orm import sessionmaker
    # Session = sessionmaker(bind=engine)
    # session = Session()


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app, connect_to_db
    connect_to_db(app, db, "freshlook.db")


    # TODO:  figure out where to put create the engine and the session
    # engine = create_engine(DB_URI, echo=True)
