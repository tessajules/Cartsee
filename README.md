#Cartsee

Cartsee uses predictive analytics to plan your next Amazon Fresh grocery order based on your previous spending patterns.  While grocery delivery services are convenient, it still takes time to plan each order, even though customers tend to make similar, predictable orders each week.  Cartsee scrapes data from the Amazon Fresh delivery receipts in your e-mail inbox to provide you with informative, interactive visualizations of your spending history, and analyzes your spending patterns to plan your next grocery order using an original prediction algorithm.  

![alt text](https://github.com/acastanieto/assets/blob/master/cartsee_orders.png "Cartsee orders page")

###Technology Stack
Python, Flask, SQLAlchemy, SQLite, Javascript, JQuery, Ajax, Bootstrap, Numpy, D3, Regex, SocketIO

###APIs
Gmail, Google Oauth

Learn more about the developer:  www.linkedin.com/in/angelacastanieto


###Building custom functionality to pull Amazon Fresh user data

Amazon Fresh does not have an API to pull in user information, so that functionality is built into Cartsee via email scraping.

Cartsee connects to the user's Gmail account via Google Oauth, and pulls in Amazon Fresh delivery receipts from their inbox using the Gmail API.  

The relevant data is scraped from the raw email files, parsed using Regular Expressions, and added to the database.

To illustrate this process in real time, websockets are implemented to display the data in a loading screen while it is being scraped and added to the database.


###D3 visualizations of spending history

Cartsee uses D3.js to construct interactive, responsive visualizations of the user's spending history.  Users can apply filters to the graphs using slide bars, and these filters are automatically applied via Ajax calls to the server to change the view of the graphs.  

![alt text](https://github.com/acastanieto/assets/blob/master/cartsee_d3.png "Cartsee D3 graph page")


###Cartsee's prediction algorithm

Cartsee uses your spending history to predict your cart.  I wrote my own prediction algorithm that calculates two main pieces of information to determine whether an item should go into your cart.  

1. To determine how frequently you buy any given item, the mean number of days between the dates you buy each item in your spending history is calculated.

2.  To determine how regularly you might buy each item, the standard deviation from the mean number of days is calculated, which informs on whether you buy the item regularly or erratically.  

Given a date the user selects, Cartsee evaluates these patterns to determine whether an item should go in your cart.  
![alt text](https://github.com/acastanieto/assets/blob/master/cartsee_prediction.png "Cartsee prediction page")

Items are prioritized by low standard deviation, so the more regularly-purchased items go into the cart first as long as they fit the frequency pattern.  

Since a cart cutoff is set based on average user cart size, items that meet the frequency but do not make the cutoff are added to the recommended list with the more regularly bought items at the top.

This cart is automatically saved to the database, and is editable by the user.  These changes are registered immediately in the database via Ajax calls.  The user can then run the prediction algorithm on top of the saved items, and new suggested items will be appended to the cart.

####Prediction algorithm testing

Cartsee also makes various other calculations to optomize the algorithm, such as selecting the most current data with which to train the algorithm to reflect the user’s most recent spending habits, and dealing with small or old order histories.  I therefore wrote unit tests covering the entire prediction algorithm.  

##How to run this app

Clone or fork this repo:
```python
https://github.com/acastanieto/Cartsee.git
```

Create and activate a virtual environment inside your project directory:

`virtualenv env`

`source env/bin/activate`

Install the requirements:

`pip install -r requirements.txt`

To obtain Google Oauth 2.0 Credentials, create a Google Developer account to obtain a Client ID and Client Secret for web applications 

Edit the web applications section to set the redirect URI to: http://localhost:5000/return_from_oauth/

In the Google Developer Console, turn on the Gmail API.

Store your secret keys, as well as a secret key for your Flask app, in a secrets.sh file to export them to your environment.  

Source your secrets.sh file.

In the Cartsee directory, type this command to start the server:

`python server.py`

Navigate your web browser to: http://localhost:5000
