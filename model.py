"""Models and database functions for Fresh Look"""

from flask_sqlalchemy import SQLAlchemy

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

    def serialize(self):
        return {
            'amazon_fresh_order_id': self.amazon_fresh_order_id,
            'delivery_date': self.delivery_date,
            'delivery_day_of_week': self.delivery_day_of_week,
            'delivery_time': self.delivery_time,
            'user_gmail': self.user_gmail
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
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", backref=db.backref("order_line_items", order_by=order_line_item_id))
    item = db.relationship("Item", backref=db.backref("order_line_items", order_by=order_line_item_id))


    def __repr__(self):
        """Representation string"""

        return "<OrderLineItem order_line_item_id=%d unit_price=%f qty=%d>" %   (self.order_line_item_id,
                                                                                self.unit_price,
                                                                                self.quantity)


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

    def serialize(self):
        return {
            'user_gmail': self.user_gmail
        }


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
