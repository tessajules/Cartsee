import unittest

from model import Order, Item, OrderLineItem, User
from model import db

from server import app, connect_to_db

from datetime import datetime


class PredictCartTestCase(unittest.TestCase):

    def setUp(self):

        """Setting up user and multiple orders, items and line items in db session for
        testing methods on Order, Item, and User classes that are used in prediction algorithm"""

        test_gmail = "test1@gmail.com"
        self.user = User(user_gmail=test_gmail, access_token="test_token")

        db.session.add(self.user)


        date_string_1 = "16 November 2014"
        delivery_date_1 = datetime.strptime(date_string_1, "%d %B %Y")
        amazon_fresh_order_id_1 = "test1"

        self.order_1 = Order(amazon_fresh_order_id=amazon_fresh_order_id_1,
                           delivery_date=delivery_date_1,
                           delivery_day_of_week="Sunday",
                           delivery_time="10:00am - 1:00pm",
                           user_gmail=test_gmail)


        date_string_2 = "3 September 2014"
        delivery_date_2 = datetime.strptime(date_string_2, "%d %B %Y")
        amazon_fresh_order_id_2 = "test2"

        self.order_2 = Order(amazon_fresh_order_id=amazon_fresh_order_id_2,
                           delivery_date=delivery_date_2,
                           delivery_day_of_week="Friday",
                           delivery_time="3:00pm - 6:00pm",
                           user_gmail=test_gmail)

        db.session.add(self.order_1)
        db.session.add(self.order_2)


        self.item_1 = Item(description="Test item 1",
                         description_key="testitem1")

        self.item_2 = Item(description="Test item 2",
                         description_key="testitem2")


        db.session.add(self.item_1)
        db.session.add(self.item_2)

        db.session.flush()

        self.order_line_item_1 = OrderLineItem(amazon_fresh_order_id=amazon_fresh_order_id_1,
                                             item_id=self.item_1.item_id,
                                             unit_price_cents=100,
                                             quantity=2)

        self.order_line_item_2 = OrderLineItem(amazon_fresh_order_id=amazon_fresh_order_id_1,
                                             item_id=self.item_2.item_id,
                                             unit_price_cents=200,
                                             quantity=3)

        self.order_line_item_3 = OrderLineItem(amazon_fresh_order_id=amazon_fresh_order_id_2,
                                             item_id=self.item_2.item_id,
                                             unit_price_cents=200,
                                             quantity=1)

        db.session.add(self.order_line_item_1)
        db.session.add(self.order_line_item_2)
        db.session.add(self.order_line_item_3)


        db.session.flush()

    def tearDown(self):
        db.session.remove()
        # db.session.rollback() will work as well.

    def test_calc_order_total(self):
        """Test of Order object method"""

        order = Order.query.filter_by(amazon_fresh_order_id="test1").one()
        self.assertEqual(order.calc_order_total(), 800)

    def test_calc_order_quantity(self):
        """Test of Order object method"""

        order = Order.query.filter_by(amazon_fresh_order_id="test1").one()
        self.assertEqual(order.calc_order_quantity(), 5)

    def test_get_num_line_items(self):
        """Test of Order object method"""
        order = Order.query.filter_by(amazon_fresh_order_id="test1").one()
        self.assertEqual(order.get_num_line_items(), 2)

    def test_get_last_order_date(self):
        """Test of Item object method"""
        item = Item.query.filter_by(description="Test item 2").one()
        date_string_1 = "16 November 2014"
        delivery_date_1 = datetime.strptime(date_string_1, "%d %B %Y")
        self.assertEqual(item.get_last_order_date(), delivery_date_1)





if __name__ == "__main__":
    connect_to_db(app, db, "freshstats.db")
    unittest.main()
