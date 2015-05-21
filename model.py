"""Models and database functions for Fresh Look"""

from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import func

from datetime import datetime

from numpy import array, mean, std

db = SQLAlchemy()

### constants for User class methods:
DELIV_HISTORY_MIN_LENGTH = 180 # the minimum order history needed to implement history cutoff
DELIV_HISTORY_USED = 90 # if history cutoff implementd, this is the amount algorithm will go
                        # back in user history to predict cart

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


    def get_total_qty(self):
        """Returns the total quantity of line items in the order"""

        return len(self.order_line_items)


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


    def get_last_order_date(self):
        """"Returns the datetime of the last date the item was delivered"""

        return db.session.query(func.max(Order.delivery_date)).join(
                                OrderLineItem).join(Item).filter(
                                Item.item_id==self.item_id).group_by(
                                Item.item_id).one()[0]


    def get_last_price(self):
        """Returns the price (in cents) from the last time the item was ordered"""

        return db.session.query(OrderLineItem.unit_price_cents).join(Item).join(
                                Order).filter(Order.delivery_date==self.get_last_order_date(),
                                              Item.item_id==self.item_id).one()[0]


    def get_deliv_dates(self):
        """Returns an unordered list of datetimes when the item has been delivered"""

        datetimes = []

        # query for list of item descriptions and all the datetimes they were bought:
        datetime_tups =  db.session.query(Order.delivery_date).join(
                                          OrderLineItem).join(Item).filter(
                                          Item.item_id==self.item_id).all()

        for datetime in datetime_tups:
            datetimes.append(datetime[0])

        return datetimes


    def calc_days_btw(self):
        """Calculates and returns the mean number of days between each consecutive
        delivery of the item, and the standard deviation from the mean"""

        days_btw = []

        if len(self.get_deliv_dates()) > 2: # make sure the item has been ordered @ least three times (to get at least two frequencies)
            deliv_dates = sorted(self.get_deliv_dates()) # sort the datetimes so can calculate days between them
            second_last = len(deliv_dates) - 2 # second to last index in delivery dates (finding here so don't have to find for each iteration)
        else:

        for i in range(len(deliv_dates)):
            days_btw.append((deliv_dates[i + 1] - deliv_dates[i]).days)
            if i == second_last:
                break

        days_btw_arr = array(days_btw)

        return mean(days_btw_arr, axis=0), std(days_btw_arr, axis=0)

        # TODO:  add code here to thrwo out outliers


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


    def serialize_orders_for_area_chart(self):
        """Packages user's order dates and totals to pass into D3 area chart function"""
        # TODO: probably should change this entire function to query and move to server (then later to a module)
        # however the strftime would still need to be done at the server.

        date_totals_dict = {}
        order_date_totals = []

        for order in self.orders:
            date_totals_dict[order.delivery_date] = order.calc_order_total()

        sorted_date_totals = sorted(date_totals_dict.keys()) # returns list of sorted dates

        for date in sorted_date_totals:
            order_date_totals.append({"date": date.strftime("%B %d, %Y"),
                                      "close": date_totals_dict[date]})

        return order_date_totals


    def get_items(self):
        """"Gets the complete list of item objects that the user has had delivered"""

        return [[order_line_item.item for order_line_item in order.order_line_items]
                 for order in user.orders][0]


    def get_first_deliv_date(self):
        """Returns the date of the first delivery in the user's delivery history"""

        return db.session.query(func.min(Order.delivery_date)).filter(
                                Order.user_gmail==self.user_gmail).one()[0]


    def get_last_deliv_date(self):
        """Returns the date of the last delivery in the user's delivery history"""

        return db.session.query(func.max(Order.delivery_date)).filter(
                                Order.user_gmail==self.user_gmail).one()[0]


    def implement_hist_cutoff(self):
        """Determines whether should implement a cutoff of items user last had delivered
        before a certain datetime in order history; if so returns True"""
        # if last delivery has occured relatively recently AND delivery history six months or longer,
        # then limit how far back you look into delivery history to 3 months before last order
        # (implement history cutoff).  Otherwise just use all of delivery history.

        today = datetime.now() #+ timedelta(1000-5)
        # today variable used so can change today's date manually for testing.

        days_deliv_history = (self.get_last_deliv_date() - self.get_first_deliv_date()).days
        days_since_last_deliv = (today - self.get_last_deliv_date()).days

        implement_history_cutoff = False
        if days_since_last_deliv < days_deliv_history and days_deliv_history > DELIV_HISTORY_MIN_LENGTH:
            implement_history_cutoff = True
            print "Implementing item datetime cutoff at %d days before chosen delivery date (Last order is relatively recent and order history > %d days.)" % (
                     DELIV_HISTORY_USED, DELIV_HISTORY_MIN_LENGTH)
        else:
            print "Datetime cutoff NOT being implemented (Order history < 180 days and/or last order occured too long ago).)"  % DELIV_HISTORY_MIN_LENGTH

        return implement_history_cutoff

    def calc_cart_qty(self):
        """Returns the upper limit for number of items that will go in the predicted cart based
        on the mean quantities of order_line_items across the user's delivery history"""

        # calculate the mean order size
        quant_arr = array([order.get_total_qty() for order in user.orders])
        mean_qty = mean(quant_arr, axis=0)
        std_qty = std(quant_arr, axis=0)

        # calculate the adjusted order size after throw out outliers above or below 2 x std dev
        filtered_quants_arr = quant_arr[abs(quant_arr - mean(quant_arr)) < 2 * std(quant_arr)]
        return mean(filtered_quants_arr, axis=0)

    def get_min_day_btw(self):
        """Returns the smallest number of days that occurs between items in user's delivery history"""

        return min([item.calc_days_btw() for item in self.get_items()])


    def calc_cart_date(self, date_str):
        """Returns the date the user input for predicted cart delivery, possibly adjusting it
        if too much time has passed since last delivery"""

        # convert the date user wants predicted order to be delivered to datetime and
        input_datetime = datetime.strptime(date_str, "%m/%d/%y")
        # TODO:  this assumes chosen_date_str is input by user as "mm/dd/yy".  Make sure HTML reflects this.

        # difference betwen last delivery date & date user input.
        deliv_day_diff = (input_datetime - self.get_last_deliv_date()).days

        days_deliv_history = self.get_last_deliv_date() - self.get_first_deliv_date()

        # if the time since your last delivery is greater than your entire delivery
        # history, the algorithm won't work.  So here the chosen datetime for the
        # predicted cart is shifted to act as if the orders occured more recently.
        # The user won't know the date used for the prediction has changed.
        if deliv_day_diff >= days_deliv_history:
            # to make sure prediction is possible chosen date set within prediction range:
            adj_datetime = last_deliv_date + timedelta(days=min(self.get_min_day_btw()))
            deliv_day_diff = (adj_datetime - self.get_last_deliv_date()).days
            print "Adjusting datetime used for prediction, to account for delivery history occuring too long ago"

        else:
            adj_datetime = input_datetime
            print "Original datetime input by user being used to predict cart"

        return adj_datetime



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
