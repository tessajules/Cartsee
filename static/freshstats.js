
function listPredictedCart() {
$.get('/predict_cart', function(json) { // {"cart": [{"item_id": 1, "description": "blah", "unit_price": 500}, ...]}
  var cart = json.cart; // [{"description": "blah", "unit_price": 500}, ...]
  $("#predict-display").append(
    "<table id='predict-table'><tr><th>Item description</th><th>Unit price</th><th></th></tr></table>");

  for (var i = 0; i < cart.length; i++ ) {

      $("#predict-table").append(
      "<tr id=" + cart[i].item_id + ">"
        + "<td>"
        + cart[i].description
        + "</td>"
        + "<td>"
        + "$" + cart[i].unit_price.toFixed(2)/100
        + "</td>"
        + "<td>"
        + "<button class='del-button' id='del-" + cart[i].item_id
        + "' onClick='reply_click(" + cart[i].item_id + ")'>Delete</button>"
        + "</td>"
    + "</tr>"
      );
  }
});
}



function reply_click(clicked_id) {

  $("#" + clicked_id).children('td, th')
    .animate({ padding: 0 })
    .wrapInner('<div class="collapse" />')
    .children()
    .slideUp(function() { $(this).closest('tr').remove(); });
}
// http://blog.slaks.net/2010/12/animating-table-rows-with-jquery.html
// http://stackoverflow.com/questions/4825295/javascript-onclick-to-get-the-id-of-the-clicked-button


function listOrders() {


    $.get('/list_orders', function(user_orders_json) {
      $("#delivery-display").append(
        "<h3>" + user_orders_json["user_gmail"] + "</h3>");
        $("#delivery-display").append("<ol>");
        for (var i = 0; i < user_orders_json["orders"].length; i++)  {
          $("#delivery-display").append(
          "<li>" + "Order # " +
          user_orders_json["orders"][i]["amazon_fresh_order_id"] +
            "<ul>" +
              "<li>" + "delivery date: " + user_orders_json["orders"][i]["delivery_date"] + "</li>" +
              "<li>" + "delivery time: " + user_orders_json["orders"][i]["delivery_time"] + "</li>" +
              "<li id='order_line_items" + i.toString() + "'>items bought <br></li>"
          + "</ul>"
        + "</li>" );
        $("#delivery-display").append("<ol>");


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
  $("#display-div").append("<div id='delivery-display'>this is deliv display</div>");


  }


listOrders();



// D3 AREA CHART BELOW
//http://stackoverflow.com/questions/19901738/d3-area-chart-using-json-object
//http://bl.ocks.org/mohamed-ali/ed4772df6dca7a48f678


function getJsonObject() {
  $.get('/orders_over_time', function(json) {
    data = json["data"]

  console.log("area chart fxn");


  var margin = {top: 20, right: 20, bottom: 30, left: 50},
      width = 960 - margin.left - margin.right,
      height = 500 - margin.top - margin.bottom;

  var parseDate = d3.time.format("%B %d, %Y").parse;
  var formatTime = d3.time.format("%e %b");


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

  var svg = d3.select("#area-display").append("svg")
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

        function transition() {
  d3.selectAll("path")
      .data(function() {
        var d = layers1;
        layers1 = layers0;
        return layers0 = d;
      })
    .transition()
      .duration(2500)
      .attr("d", area);
}
});}

getJsonObject();





/// Bubble chart below

function showBubbleChart() {
  console.log("bubble chart fxn");

  var diameter = 960,
    format = d3.format(",d"),
    color = d3.scale.category20c();

var bubble = d3.layout.pack()
    .sort(null)
    .size([diameter, diameter])
    .padding(1.5);

var svg = d3.select("#bubble-display").append("svg")
    .attr("width", diameter)
    .attr("height", diameter)
    .attr("class", "bubble");

d3.json("/items_by_qty", function(error, root) {
  var node = svg.selectAll(".node")
      .data(bubble.nodes(classes(root))
      .filter(function(d) { return !d.children; }))
    .enter().append("g")
      .attr("class", "node")
      .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

  node.append("title")
      .text(function(d) { return d.className + ": " + format(d.value); });

  node.append("circle")
      .attr("r", function(d) { return d.r; })
      .style("fill", function(d) { return color(d.packageName); });

  node.append("text")
      .attr("dy", ".3em")
      .style("text-anchor", "middle")
      .text(function(d) { return d.className.substring(0, d.r / 3); });
});



// Returns a flattened hierarchy containing all leaf nodes under the root.
function classes(root) {
  var classes = [];

  function recurse(name, node) {
    if (node.children) node.children.forEach(function(child) { recurse(node.name, child); });
    else classes.push({packageName: name, className: node.name, value: node.quantity});
  }

  recurse(null, root);
  return {children: classes};
}

d3.select(self.frameElement).style("height", diameter + "px");


}

showBubbleChart();


// histogram

// Generate a Bates distribution of 10 random variables.

function showHistogram() {
//http://bl.ocks.org/Caged/6476579
  console.log("bar chart fxn");


  var margin = {top: 40, right: 20, bottom: 30, left: 40},
      width = 960 - margin.left - margin.right,
      height = 500 - margin.top - margin.bottom;

  // var formatPercent = d3.format(".0%");

  var x = d3.scale.ordinal()
      .rangeRoundBands([0, width], .1);

  var y = d3.scale.linear()
      .range([height, 0]);

  var xAxis = d3.svg.axis()
      .scale(x)
      .orient("bottom");

  var yAxis = d3.svg.axis()
      .scale(y)
      .orient("left")
      // .tickFormat(formatPercent);

  var tip = d3.tip()
    .attr('class', 'd3-tip')
    .offset([-10, 0])
    .html(function(d) {
      return "<strong>Deliveries:</strong> <span style='color:red'>" + d.deliveries + "</span>";
    })

  var svg = d3.select("#bar-display").append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
    .append("g")
      .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

  svg.call(tip);

  d3.json("/delivery_days", function(error, data) {
    data = data["data"]
    x.domain(data.map(function(d) { return d.day; }));
    y.domain([0, d3.max(data, function(d) { return d.deliveries; })]);
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
        .text("Deliveries");

    svg.selectAll(".bar")
        .data(data)
      .enter().append("rect")
        .attr("class", "bar")
        .attr("x", function(d) { return x(d.day); })
        .attr("width", x.rangeBand())
        .attr("y", function(d) { return y(d.deliveries); })
        .attr("height", function(d) { return height - y(d.deliveries); })
        .on('mouseover', tip.show)
        .on('mouseout', tip.hide)

  });

  function type(d) {
    d.deliveries = +d.deliveries;
    return d;
  }
  }
showHistogram();

$('#chart-control').hide();
$('#predict-control').hide();
$('#bubble-display').hide();
$('#area-display').hide();
$('#bar-display').hide();
$('#predict-display').hide();


$("#cart").on("click", function() {
  $(".control-div").hide();
  $("#predict-control").show();
  $(".display-div").hide();
  $("#predict-display").show();
});

$("#viz").on("click", function() {
  $(".control-div").hide();
  $("#chart-control").show();
  $(".display-div").hide();
  $("#bubble-display").show();
});

$("#bubble-button").on("click", function() {
   $(".display-div").hide();
   $("#bubble-display").show();
});

$("#area-button").on("click", function() {
   $(".display-div").hide();
   $("#area-display").show();
});

$("#bar-button").on("click", function() {
   $(".display-div").hide();
   $("#bar-display").show();
});

$("#deliv").on("click", function() {
   $(".display-div").hide();
   $(".control-div").hide();
   $("#delivery-display").show();
   $("#deliv-control").show();
});
