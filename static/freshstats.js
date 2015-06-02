  $(document).ready(function() {
    $("#bubble-price").bootstrapSlider({});
  });



$(document).ajaxStart(function() {
  NProgress.start();
})


$(document).ajaxStop(function() {
  NProgress.done();
})

$(document).ready(function () {
    $('#date-input').datepicker({dateFormat:'mm/dd/yy', minDate:1, maxDate:10});
    }
);

$(document).ready(function () {
    $('#min-date').datepicker({dateFormat:'mm/dd/yy'});
    }
);

$(document).ready(function () {
    $('#max-date').datepicker({dateFormat:'mm/dd/yy'});
    }
);



$('#date-input').on('change', function () {
  $('#predict-submit').removeAttr('disabled');
});

var socket = io.connect('http://' + document.domain + ':' + location.port + '/loads');

socket.on('connect', function() {
    socket.emit('start_loading', {data: 'proceed'});
});

socket.on('my response', function(data) {
  $("#numorders-display").html("Number of orders: " + data.num_orders);
  $("#quantity-display").html("Number of items: " + data.quantity);
    $("#total-display").html("Order totals: $" + data.order_total.toFixed(2)/100);
    $("#percent-display").html("Percent complete: " + (data.num_orders/data.total_num_orders * 100).toFixed(2) + "%")

    if (data.status === "done") {

      listOrders();

      showAreaChart('/orders_over_time')
      showBubbleChart('/items_by_qty');
      showHistogram();
      $(".loading-display").removeClass("show");
      $(".data-display").addClass("show");

    }
});

    function showSavedCart() {

      $(".chart-button").removeAttr("disabled");
      $(".toggle-button").removeAttr("disabled");
      $("#cart").attr("disabled", true);
      $(".control-div").addClass("show");
      $("#predict-control").addClass("show");
      $(".display-div").removeClass("show");
      $("#predict-display").addClass("show");
      $(".control-div").removeClass("show");
      $("#predict-control").addClass("show");

      $.get('/saved_cart', function(json) {
        if (json.saved_cart.length === 0) {
          $("#saved-table").empty();
          $("#predict-table").empty();



        $("#saved-table").append("<h3>You currently have no saved items in your cart.</h3>")
        } else {
          $("#saved-table").empty();
          $("#predict-table").empty();
          $("#keep-saved").addClass("show");

        $("#saved-table").append("<h3>Your current saved items:</h3>");
        $("#saved-table").append(

          "<tr><th>Item description</th><th>Unit price</th><th></th><th></th></tr>");

          var saved_cart = json.saved_cart;

            $.each(saved_cart, function(i, item) {
              var $tr = $('#saved-table').append(
                $('<tr>').addClass('item').attr('id', item.item_id).attr('data-item_id', item.item_id).append(
                  $('<td class="description-td">').text(item.description),
                  $('<td class="price-td">').text("$" + item.unit_price.toFixed(2)/100),
                  $('<td class="del-td">').html("<button class='del-primary' id='del-" + item.item_id
                                 + "' onClick='delete_item(" + item.item_id + ")'>Delete</button>"),
                 $('<td class="amazon">').html("<a href='https://fresh.amazon.com/Search?input=" + encodeURIComponent(item.description) + "' target='_blank'>"
                                + "<img src='http://g-ec2.images-amazon.com/images/G/01/omaha/images/badges/af-badge-160x50.png' height=20px alt='AmazonFresh button'>"
                                + "</a>")
            ));});}});}

    function showPredictedCart(evt) {

      $(".cart-button").removeClass("show");

        evt.preventDefault();

        $("#predict-table").empty();
        $("#control-table").empty();
        $("#saved-table").empty();
        $(".keep-saved").addClass("show");



        $.get('/saved_cart', function(json) {

          var keep_saved = $("#keep-saved").val();



            $("#saved-table").append("<h3>Predicted Items:</h3>");
            $("#saved-table").append(

              "<tr><th>Item description</th><th>Unit price</th><th></th><th></th></tr>");

              if ($("#keep-saved").prop("checked")) {

              var saved_cart = json.saved_cart;

                $.each(saved_cart, function(i, item) {
                  var $tr = $('#saved-table').append(
                    $('<tr>').addClass('item').attr('id', item.item_id).attr('data-item_id', item.item_id).append(
                      $('<td class="description-td">').text(item.description),
                      $('<td class="price-td">').text("$" + item.unit_price.toFixed(2)/100),
                      $('<td class="del-td">').html("<button class='del-primary' id='del-" + item.item_id
                                     + "' onClick='delete_item(" + item.item_id + ")'>Delete</button>"),
                     $('<td class="amazon">').html("<a href='https://fresh.amazon.com/Search?input=" + encodeURIComponent(item.description) + "' target='_blank'>"
                                    + "<img src='http://g-ec2.images-amazon.com/images/G/01/omaha/images/badges/af-badge-160x50.png' height=20px alt='AmazonFresh button'>"
                                    + "</a>")
                ));});

          }});

          var url = "/predict_cart?" + $("#date-form").serialize();


          $.get(url, function(json) {

            var primary_cart = json.primary_cart; // [{"description": "blah", "unit_price": 500}, ...]
            var backup_cart = json.backup_cart;


                $.each(primary_cart, function(i, item) {
                    var $tr = $('#predict-table').append(
                        $('<tr>').addClass('item').attr('id', item.item_id).attr('data-item_id', item.item_id).append(
                        $('<td class="description-td">').text(item.description),
                        $('<td class="price-td">').text("$" + item.unit_price.toFixed(2)/100),
                        $('<td class="price-td">').html("<button class='del-primary' id='del-" + item.item_id
                                       + "' onClick='delete_item(" + item.item_id + ")'>Delete</button>"),
                        $('<td class="amazon">').html("<a href='https://fresh.amazon.com/Search?input=" + encodeURIComponent(item.description) + "' target='_blank'>"
                                       + "<img src='http://g-ec2.images-amazon.com/images/G/01/omaha/images/badges/af-badge-160x50.png' height=20px alt='AmazonFresh button'>"
                                       + "</a>")
                      )
                    );
                });
                $("#control-table").append("<h3>More recommended items:</h3>");

            $("#control-table").append(
            "<tr><th>Item description</th><th>Unit price</th><th></th></tr>");

            $.each(backup_cart, function(i, item) {
                var $tr = $('#control-table').append(
                    $('<tr>').attr('id', item.item_id).append(
                    $('<td class="description-td">').text(item.description),
                    $('<td class="price-td">').text("$" + item.unit_price.toFixed(2)/100),
                    $('<td class="add-td">').html("<button class='add-backup' id='add-" + item.item_id
                            + "' data-item_id='" + item.item_id + "'"
                            + "' data-description='" + item.description + "'"
                            + "' data-unit_price='" + item.unit_price + "'"
                            + "' onClick='add_item(" + item.item_id + ")'>Add</button>")
                  )
                );
            });
            $(".cart-button").addClass("show");
            $(".backup-search").addClass("show");
            });


            }


      $("#date-form").on('submit', showPredictedCart)



function delete_item(clicked_id) {
  $("#" + clicked_id).children('td, th')
    .animate({ padding: 0 })
    .wrapInner('<div class="collapse" />')
    .children()
    .slideUp(function() { $(this).closest('tr').remove(); });
        $.ajax({
            url: '/delete_item',
            type: 'POST',
            data: { json: JSON.stringify(clicked_id)},
            dataType: 'json'
        });
}

function add_item(clicked_id) {

  $("#" + clicked_id).children('td, th')
    .animate({ padding: 0 })
    .wrapInner('<div class="collapse" />')
    .children()
    .slideUp(function() { $(this).closest('tr').remove(); });

    var item_id = $("#add-" + clicked_id).data("item_id");
    var description = $("#add-" + clicked_id).data("description");
    var unit_price = $("#add-" + clicked_id).data("unit_price");

            $('#predict-table').append(
            $('<tr>').addClass('item').attr('id', item_id).attr('data-item_id', item_id).append(
            $('<td class="description-td">').text(description),
            $('<td class="price-td">').text("$" + unit_price.toFixed(2)/100),
            $('<td class="del-td">').html("<button class='del-primary' id='del-" + item_id
                           + "' onClick='delete_item(" + item_id + ")'>Delete</button>"),
            $('<td class="amazon">').html("<a href='https://fresh.amazon.com/Search?input=" + encodeURIComponent(description) + "' target='_blank'>"
                           + "<img src='http://g-ec2.images-amazon.com/images/G/01/omaha/images/badges/af-badge-160x50.png' height=20px alt='AmazonFresh button'>"
                           + "</a>")
          )
        );


    $("#" + item_id)
    .animate({ padding: 0 })
    .find('td')
    .wrapInner('<div style="border: none; display: none;" />')
    .parent()
    .find('td > div')
    .slideDown()

    $.ajax({
        url: '/add_item',
        type: 'POST',
        data: { json: JSON.stringify(item_id)},
        dataType: 'json'
    });
}

function showSavedMessage () {
$("#saved-message").fadeIn(function() {
    setTimeout(function() {
        $("#saved-message").fadeOut(1000);
    }, 3000);
});
}





function listOrders() {

  $("#deliv").attr("disabled", true);

    $("#delivery-display").addClass("show");

    $.get('/list_orders', function(user_orders_json) {

      $.each(user_orders_json.orders, function(i, order) {

          $("#delivery-display").append(
            $('<div class="order" id="order-' + i + '">').append(
              $('<div class="header" id="header-' + i + '" onClick="get_id(' + i + ')">').append(
                $("<span class='row number'>").text(order.amazon_fresh_order_id),
                $("<span class='row deliv-date'>").text(order.delivery_date),
                $("<span class='row delivery-time'>").text(order.delivery_time),
                $("<span class='row order-total'>").text("$" + order.order_total.toFixed(2)/100),
                $("<span class='row' id='expand-" + i + "'>")//.text("+")
               ),
              $("<div class='items-div' id='items-div-" + i + "'>").append(
                $("<table class='items-table'>").attr("cellspacing", "0").attr("width", "100%").append(
                  $("<thead>").append(
                    $("<tr class='header-row'>").append(
                      $("<th class='header-descript'>").text("Item Description"),
                      $("<th  class='header-price'>").text("Unit Price"),
                      $("<th class='header-quantity'>").text("Unit Quantity")
                     )
                   ),
                  $("<tbody id='body-" + i + "'>")
                 )
               )
             )
           );

          $.each(order.order_line_items_serialized, function (j, item) {

            $('#body-' + i).append(
              $('<tr>').addClass('items-row').append(
                $('<td class="row-descript">').text(item.description),
                $('<td class="row-price">').text("$" + item.unit_price.toFixed(2)/100),
                $('<td class="row-quantity">').text(item.quantity)
               )
             );


            });

  });

});}



function get_id(clicked) {

  $("#items-div-" + clicked).slideToggle(500);

  // if ($("#header-" + clicked).find("#expand-" + clicked).text() == "+") {
  //     $("#header-" + clicked).find("#expand-" + clicked).text("-");
  //   } else {
  //     $("#header-" + clicked).find("#expand-" + clicked).text("+");
  //   }

  }


$('#search').keyup(function (e) {


  var val = $.trim($(this).val()).toLowerCase();

  var $rows = $('.items-table tr');

if (val.length > 2 || val.length === 0) {
  $rows.show().filter(function () {
    var text = $(this).text().toLowerCase();
    if (text.includes(val)) {
      $(this).parent().parent().parent().stop(true, true).delay(1000).slideDown();
    }

    if (val.length === 0 && e.keyCode === 8) { // keycode for Macs, not sure about PCs...need to figure out
      $(this).parent().parent().parent().stop(true, true).slideUp();
    }


    return !~text.indexOf(val);

  }).hide();
}
});



$('#backup-search').keyup(function (e) {


  var val = $.trim($(this).val()).toLowerCase();

  var $rows = $('#control-table tr');

if (val.length > 2) {
  $rows.show().filter(function () {
    var text = $(this).text().toLowerCase();

    return !~text.indexOf(val);

  }).hide();
}

if (val.length === 0 ) {
  $rows.show()
}

});

// D3 AREA CHART BELOW
//http://stackoverflow.com/questions/19901738/d3-area-chart-using-json-object
//http://bl.ocks.org/mohamed-ali/ed4772df6dca7a48f678


function showAreaChart(url) {
  $.get(url, function(json) {
    data = json["data"]

    $("#area-display").empty();

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


$("#area-form").on("change", function(evt) {
  evt.preventDefault();
  var url = '/orders_over_time?' + $(this).serialize();

    showAreaChart(url);

});



//http://stackoverflow.com/questions/10934853/d3-js-loading-json-without-a-http-get
/// Bubble chart below

function showBubbleChart(url) {


  $("#bubble-display").empty();

  $.get(url, function(json) {


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

  var root = json
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

});
}

// range selector for bubble chart

$("#bubble-form").on("change", function(evt) {
  evt.preventDefault();
  var url = '/items_by_qty?' + $(this).serialize();

    showBubbleChart(url);

});

// need: min_price, max_price, list from min to max of six values, (min-max)/5 (for step)

// also for qty, same thing



var bubblePriceSlider = $("#bubble-price").bootstrapSlider({ min: 0,
                                                    max: 100,
                                                    step: 20,
                                                    value: [20, 80],
                                                    ticks: [0, 20, 40, 60, 80, 100],
                                                    ticks_labels: ['0', '20', '40', '60', '80', '100'],
                                                    focus: true });

var bubbleQtySlider = $("#bubble-quantity").bootstrapSlider({ min: 0,
                                                    max: 100,
                                                    step: 20,
                                                    value: [20, 80],
                                                    ticks: [0, 20, 40, 60, 80, 100],
                                                    ticks_labels: ['0', '20', '40', '60', '80', '100'],
                                                    focus: true });
bubblePriceSlider.on('change', function () {
  var value = $(this).bootstrapSlider('getValue');
  console.log(value)
});


bubbleQtySlider.on('change', function () {
  var value = $(this).bootstrapSlider('getValue');
  console.log(value)
});








// histogram

// Generate a Bates distribution of 10 random variables.

function showHistogram() {
//http://bl.ocks.org/Caged/6476579


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




$("#cart").on("click", showSavedCart);

$("#viz").on("click", function() {
  $(".control-div").removeClass("show");
  $("#chart-control").addClass("show");
  $(".display-div").removeClass("show");
  $("#bubble-display").addClass("show");
  $(".toggle-button").removeAttr("disabled");
  $(this).attr("disabled", true);
  $(".chart-button").removeAttr("disabled");
  $("#bubble-button").attr("disabled", true);
});

$("#bubble-button").on("click", function() {
   $(".display-div").removeClass("show");
   $("#bubble-display").addClass("show");
   $(".chart-button").removeAttr("disabled");
   $(this).attr("disabled", true);

});

$("#area-button").on("click", function() {
   $(".display-div").removeClass("show");
   $("#area-display").addClass("show");
   $(".chart-button").removeAttr("disabled");
   $(this).attr("disabled", true);
});

$("#bar-button").on("click", function() {
   $(".display-div").removeClass("show");
   $("#bar-display").addClass("show");
   $(".chart-button").removeAttr("disabled");
   $(this).attr("disabled", true);
});

$("#deliv").on("click", function() {
   $(".display-div").removeClass("show");
   $(".control-div").removeClass("show");
   $("#delivery-display").addClass("show");
   $("#deliv-control").addClass("show");
   $(".toggle-button").removeAttr("disabled");
   $(".chart-button").removeAttr("disabled");
   $(this).attr("disabled", true);



});

//loading screen flow:
// 1. Click login that goes to oauth, get oauth callback
// 2. redirect user to loading page (main page for app)
// 3.  that connects the web socket.
// 4.  start processing the emails
// 5.  after each email, send the updated totals through the web socket and update the page.
// 6.  after you're done processing the emails, send a message through the websocket saying you're done
// 7.  when you receive the done message, then use javascript to build all the rest of the page (make all the calls to get your data and stuff)
// You don't want to do a page refresh afte rhte loading screen.  So your message through the web socket should be json.
// it should have a status and all the different totals you want to show.  When you receive that json, if the status is still loading or processing, then you just
// update the totals.  but if you receive the status and the status is done/complete loading, you hide the loading section and show the rest of the page and trigger off
// all the calls to load the data.  but you're not actually doing a refresh of the entire page, you're using javascript.
// read a websockets tutorial and see how to use websockets with flask.  may need to find jquery plugin to use websockets with jquery.

// for demo mode have it instead of reading data in the database, have it load the database using
// stored versions of the emails.  store emails as text files.  only difference is it doesn't connect to gmail.
