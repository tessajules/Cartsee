function showVisualization() {

    $.get('/visualization', function(user_orders_json) {
      $("#display-div").append(
        "<h3>" + user_orders_json["user_gmail"] + "</h3>");
        $("#display-div").append("<ol>")
        for (var i = 0; i < user_orders_json["orders"].length; i++)  {
          $("#display-div").append(
          "<li>" + "Order # " +
          user_orders_json["orders"][i]["amazon_fresh_order_id"] +
            "<ul>" +
            "<li>" + "delivery date: " + user_orders_json["orders"][i]["delivery_date"] + "</li>" +
            "<li>" + "delivery time: " + user_orders_json["orders"][i]["delivery_time"] + "</li>" 

            + "</ul>"
          + "</li>"
          );
          }
        $("#display-div").append("<ol>")


      }

    );

  }

showVisualization()
