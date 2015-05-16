function listOrders() {

    $.get('/list_orders', function(user_orders_json) {
      $("#display-div").append(
        "<h3>" + user_orders_json["user_gmail"] + "</h3>");
        $("#display-div").append("<ol>");
        for (var i = 0; i < user_orders_json["orders"].length; i++)  {
          $("#display-div").append(
          "<li>" + "Order # " +
          user_orders_json["orders"][i]["amazon_fresh_order_id"] +
            "<ul>" +
              "<li>" + "delivery date: " + user_orders_json["orders"][i]["delivery_date"] + "</li>" +
              "<li>" + "delivery time: " + user_orders_json["orders"][i]["delivery_time"] + "</li>" +
              "<li id='order_line_items" + i.toString() + "'>items bought <br></li>"
          + "</ul>"
        + "</li>" );
        $("#display-div").append("<ol>");

        for (var j = 0; j < user_orders_json["orders"][i]["order_line_items_serialized"].length; j++) {
          $("#order_line_items" + i.toString()).append(
            "line item # " +
            user_orders_json["orders"][i]["order_line_items_serialized"][j]["order_line_item_id"]
            + ", unit price: " + "$" +
            user_orders_json["orders"][i]["order_line_items_serialized"][j]["unit_price"]
            + " quantity: " +
            user_orders_json["orders"][i]["order_line_items_serialized"][j]["quantity"]
            + " " +
            user_orders_json["orders"][i]["order_line_items_serialized"][j]["description"]
            + "<br>"
          );
          }

        $("#order_line_items" + i.toString()).append(
          "order total: $" +
          user_orders_json["orders"][i]["order_total"])

          }
      }
    );
  };


listOrders();

function ordersOverTime() {
    $("#display-div").empty();

    $.get('/orders_over_time', function(orders) {
      $("#display-div").append("<ol>");
      for (var i = 0;
           i < orders["order_info"]["amazon_fresh_order_ids"].length;
           i++)  {

        var order_id = orders["order_info"]["amazon_fresh_order_ids"][i];
        $("#display-div").append(
        "<li>" +
        "<strong>" + order_id + "</strong>"
        + " delivery date: " +
        orders["order_info"]["order_date_totals"][order_id]["delivery_date"]
        + " order total: " +
        orders["order_info"]["order_date_totals"][order_id]["order_total"]
        + "</li>"
      );
    }
    $("#display-div").append("</ol>");
    }
    );
}

$("#orders-time").on('click', ordersOverTime);
