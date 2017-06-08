
## About - Item Catalog Project
This project is an app which lists different category of Sports and also various items related to that particular sport. User can login by using third party Authentication and Authorization, here it is Google. Users can Create sports/items and can also edit or delete their own items.

## How to Setup and Run the project
1. Install Vagrant Virtual Machine.
2. Vagrant VM has PostgreSQL installed and configured.
3. clone or download the project files in catalog folder under vagrant as /vagrant/catalog
4. Create projects in developer.google.com, get the client id and get the client_secrets.json file. Place this file within the catalog folder. Also replace the <client-id> within the /catalog/templates/login.html with your client id.
5. Navigate to /vagrant and start the vagrant VM by writing "vagrant up" and "vagrant ssh".
6. Navigate to $/vagrant/catalog which will have files as
    
    a. database_setup.sql  - Code for setting up Database Schema

    b. application.py - Various functions to connect to database, manipulate database and also to render the data/template on the browser.

7.  Now when in catalog folder, write below command to setup the database:

               $ python database_setup.py

8. To run the application write below command:

                $ python application.py
9. Access the application by visiting http://localhost:5000 locally on your browser.

## How to Navigate the application

1. Application has one home page which shows the list of all sports. Homepage can be accessed by using either of the below links:

            localhost:5000
            localhost:5000/sport

2. If the User is not login then there is Login button on the top right side. If user clicks on any of the sports, it shows all items for that sport. Clicking on the sport item takes to another page which shows the details of the item.

3. Once User is login, the page shows all the button to Create Sport/Item, Add Sport, Edit Item, Delete Item etc. 
User can logout by clicking on the Logout button.

4. One user can not edit/delete other user's sport/item.

5. For Creating Sport/Item, User has to be login.

##Prerequisites

1.  To properly use all the functionalities of this app, User should have google login account.
2.  User need to have client id and secret id created from developer.google.com and should also have client_secret.json file.
   
## Skills involved
1. Python
2. Flask
3. SQLAlchemy
4. HTML
5. CSS
6. Bootstrap
