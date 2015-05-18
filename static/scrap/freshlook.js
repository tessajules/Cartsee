function listOrders() {

   $("#display-div").empty();


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
            user_orders_json["orders"][i]["order_line_items_serialized"][j]["unit_price"].toFixed(2)/100
            + " quantity: " +
            user_orders_json["orders"][i]["order_line_items_serialized"][j]["quantity"]
            + " " +
            user_orders_json["orders"][i]["order_line_items_serialized"][j]["description"]
            + "<br>"
          );
          }

        $("#order_line_items" + i.toString()).append(
          "order total: $" +
          user_orders_json["orders"][i]["order_total"].toFixed(2)/100)

          }
      }
    );
  };


listOrders();
$("#order-list").on('click', listOrders);




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
        + " order total: $" +
        orders["order_info"]["order_date_totals"][order_id]["order_total"].toFixed(2)/100
        + "</li>"
      );
    }
    $("#display-div").append("</ol>");
    }
    );
}

$("#orders-time").on('click', ordersOverTime);

// D3 AREA CHART BELOW
//http://stackoverflow.com/questions/19901738/d3-area-chart-using-json-object
//http://bl.ocks.org/mohamed-ali/ed4772df6dca7a48f678

function showAreaChart(data) {

  console.log(data);
  var margin = {top: 20, right: 20, bottom: 30, left: 50},
      width = 960 - margin.left - margin.right,
      height = 500 - margin.top - margin.bottom;

  var parseDate = d3.time.format("%b %d, %Y").parse;
  var formatTime = d3.time.format("%b %d '%y");


  var x = d3.time.scale()
      .range([0, width]);

  var y = d3.scale.linear()
      .range([height, 0]);

  var xAxis = d3.svg.axis()
      .scale(x)
      .orient("bottom");

  var yAxis = d3.svg.axis()
      .scale(y)
      .orient("left");

  var area = d3.svg.area()
      .x(function(d) { return x(d.date); })
      .y0(height)
      .y1(function(d) { return y(d.close); });

  var svg = d3.select("#display-div").append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

      var div = d3.select("#display-div").append("div")
    .attr("class", "tooltip")
    .style("opacity", 0);

    data.forEach(function(d) {
      d.date = parseDate(d.date);
      d.close = d.close.toFixed(2)/100
      d.close = +d.close;
    });

    x.domain(d3.extent(data, function(d) { return d.date; }));
    y.domain([0, d3.max(data, function(d) { return d.close; })]);

    svg.append("path")
        .datum(data)
        .attr("class", "area")
        .attr("d", area);

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
      .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .text("Price ($)");

svg.selectAll("dot")
        .data(data)
    .enter().append("circle")
        .attr("r", 5)
        .attr("cx", function(d) { return x(d.date); })
        .attr("cy", function(d) { return y(d.close); })
        .on("mouseover", function(d) {
            div.transition()
                .duration(200)
                .style("opacity", .9);
            div .html(formatTime(d.date) + "<br/>"  + d.close)
                .style("left", (d3.event.pageX) + "px")
                .style("top", (d3.event.pageY - 28) + "px");
            })
        .on("mouseout", function(d) {
            div.transition()
                .duration(500)
                .style("opacity", 0);
        });
}


function getJsonObject() {
  $("#display-div").empty();
  $.get('/orders_over_time', function(json) {
    data = json["data"]
    showAreaChart(data);
  });
}

$("#area-chart-button").on('click', getJsonObject);
//http://www.d3noob.org/2013/01/adding-tooltips-to-d3js-graph.html
