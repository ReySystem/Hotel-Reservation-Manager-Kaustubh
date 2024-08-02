import re
from datetime import datetime, timedelta
from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_mail import *
from pymongo import MongoClient
from conditions_check import *

PAGE_SIZE = 10
app = Flask(__name__,  static_folder='static')
app.secret_key ='price_1P50D7RphYJacvg1h2Ul49lJ'
UNSPLASH_ACCESS_KEY = 'DT6pfSgIhwxASBHWZMDA1hzDR5Pb9H4_aAdQzxCpNto'
UNSPLASH_API_URL = "https://api.unsplash.com/photos/random"



# MongoDB connection settings
mongo_uri = "mongodb://localhost:27017/"
client = MongoClient(mongo_uri)
db = client['Hotel_Reservation']
collection_users = db['users'] 
collection_booking_0 = db['booking_0']
collection_booking_1 = db['booking_1']
collection_rooms = db['rooms']
collection_meals = db['meals']
collection_countries = db['countries']

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEBUG'] = False
app.config['MAIL_USERNAME'] = 'yo51st23@gmail.com'
app.config['MAIL_PASSWORD'] = 'lahmbruzubzctaxd'
mail = Mail(app)

username = ''
start_date = datetime.now().date()
end_date = start_date + timedelta(days=90)


def send_verification_email(email, verification_token, forget_flag=False):
    """
    function to send verification email

    params:
    email: email ID
    verification_token: verification_token
    forget_flag: flag to display alert in html page
    """

    if forget_flag:
        subject = 'Forgot Your Password'
        body = f'Click the following link to reset your password: {request.url_root}verify/forget/{verification_token}'
    
    else:
        subject = 'Verify Your Email'
        body = f'Click the following link to verify your email: {request.url_root}verify/{verification_token}'

    msg = Message(subject, sender='yo51st23@gmail.com', recipients=[email])
    msg.body = body
    mail.send(msg)

def send_email_confirmation(email, details_email):
    """
    function to send email booking confirmation

    params:
    email: email ID
    details_email: list of booking details
    """
    
    subject = 'Booking Confirmation'
    body = f'Your booking has been confirmed. Here are your details:\n\n\
            Customer Name: {details_email[0]}\n\
            Adults: {details_email[1]}\n\
            Children: {details_email[2]}\n\
            Check-In Date: {details_email[3]}\n\
            Check-Out Date: {details_email[4]}\n\
            Room Type: {details_email[5]}\n\
            Meals: {details_email[6]}\n\
            Total Price: {details_email[7]}\n'
    

    msg = Message(subject, sender='yo51st23@gmail.com', recipients=[email])
    msg.body = body
    mail.send(msg)

# Clear the session
def clear_session():
    """
    function clear session variables
    """

    session_keys = list(session.keys())  # Get a list of keys to avoid RuntimeError
    for key in session_keys:
        session.pop(key, None)


@app.route('/verify/<verification_token>', methods=['GET'])
def verify_email(verification_token):
    """
    function to app route verify_email

    params:
    verification token: randomly generated verification token
    """
    user = collection_users.find_one({'token': verification_token})

    if user:
        # Update user data into MongoDB
        collection_users.update_one({'token': verification_token}, {'$set': {'is_verified': True}, '$unset':{'token': None}})

        flash('Email verified. You can now log in.', 'success')
    else:
        flash('Invalid verification link.', 'danger')
    return redirect(url_for('login'))

@app.route('/rooms', methods=['GET', 'POST'])
def rooms():
    """
    function to app route rooms page

    """

    if request.method=='POST':
        check_in = request.form.get('checkin')
        check_out = request.form.get('checkout')

        room_type = request.form.get('room_type')

        
        ip_date_list = []
        for date in [check_in, check_out]:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            converted_date = parsed_date.strftime("%d-%m-%Y")
            ip_date_list.append(converted_date)

        date_list = get_dates_between(ip_date_list[0], ip_date_list[1])

        
        get_availability_collection = collection_rooms.find({'Room Type':room_type})

        document = next(get_availability_collection)


        availability_dict = document['Availability']  

        sliced_availability_dict = {k: availability_dict[k] for k in date_list}
        
        no_rooms = False
        print(sliced_availability_dict)
        for v in sliced_availability_dict.values():
            if v == 0:
                no_rooms = True
                return redirect(url_for('index', no_rooms=no_rooms))


        collection_get_room_details = collection_rooms.find({'Room Type':room_type}, {'Beds':1, 'Utilities':1, 'price':1, 'Maximum Guests':1,'_id':0})
        room_details = list(collection_get_room_details)

        beds_list = [item.strip() for item in room_details[0]['Beds'].split(',')]
        utilities_list = [item.strip() for item in room_details[0]['Utilities'].split(',')]
        price = room_details[0]['price']
        max_guests = room_details[0]['Maximum Guests']

        # Store form data in localStorage
        session['check_in'] = ip_date_list[0]
        session['check_out'] = ip_date_list[1]
        session['room_type'] = room_type
        session['max_guests'] = max_guests
        session['room_price'] = price
        session['beds_list'] = beds_list
        session['utilities_list'] = utilities_list


        return render_template('rooms.html', room_type=room_type, beds_list = beds_list, utilities_list = utilities_list, price= price, max_guests=max_guests, check_in = ip_date_list[0], check_out=ip_date_list[1])
    
    else:
        # For GET request, retrieve data from query parameters
        check_in = session.get('check_in', '')
        check_out = session.get('check_out', '')
        room_type = session.get('room_type', '')
        max_guests = session.get('max_guests', '')
        room_price = session.get('room_price', '')
        beds_list = session.get('beds_list', '')
        utilities_list = session.get('utilities_list', '')

        max_guests = int(max_guests)
        return render_template('rooms.html', room_type=room_type, beds_list = beds_list, utilities_list = utilities_list, price= room_price, max_guests=max_guests, check_in = check_in, check_out=check_out)
    

@app.route('/booking_form', methods=['GET', 'POST'])
def booking_form():
    """
    function to app route booking form page

    """

    if request.method == 'POST':
        if 'username' not in session:
            no_login = True
            return redirect(url_for('index', no_login=no_login))

        check_in = session['check_in']
        check_out = session['check_out']
        room_type = session['room_type']
        max_guests = session['max_guests']


        countries_collection = collection_countries.find({},{'Country':1, '_id':0})
        doc_countries = list(countries_collection)
        country_vals = [country['Country'] for country in doc_countries]

        meals_collection = collection_meals.find({}, {'Meal Type':1 , '_id':0})
        doc_meals = list(meals_collection)
        meal_vals = [meal['Meal Type'] for meal in doc_meals]
    
        return render_template('booking_form.html', check_in = check_in, check_out=check_out, country_vals = country_vals, room_type=room_type, meal_vals=meal_vals, max_guests=max_guests)
    
    else:
        check_in = session.get('check_in', '')
        check_out = session.get('check_out', '')
        room_type = session.get('room_type', '')

        countries_collection = collection_countries.find({},{'Country':1, '_id':0})
        doc_countries = list(countries_collection)
        country_vals = [country['Country'] for country in doc_countries]

        meals_collection = collection_meals.find({}, {'Meal Type':1 , '_id':0})
        doc_meals = list(meals_collection)
        meal_vals = [meal['Meal Type'] for meal in doc_meals]
    return render_template('booking_form.html', check_in = check_in, check_out=check_out,room_type=room_type, country_vals = country_vals, meal_vals=meal_vals)
 

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    function to app route index page

    """

    room_types = list(collection_rooms.find({}, {'_id': 0, 'Room Type': 1}))

    if request.method == 'POST':
        pay_success = True
        total_people_count = int(session['adults']) + int(session['children'])

        db_val = get_db_on_hash(total_people_count)
        print('get_val', db_val)

        if db_val == 0:
            id_val = get_next_id(collection_booking_0)
            doc_usr_details = collection_users.find({'username':session['username']}, {'email':1})

            send_email_confirmation(doc_usr_details[0]['email'], [session['name'], session['adults'], session['children'], session['check_in'], session['check_out'], session['room_type'], session['meal_type'], session['total_price']])

            collection_booking_0.insert_one({'_id':id_val, 'Customer ID': doc_usr_details[0]['_id'], 'username': session['username'], 
                                             'Customer Names': session['name'], 'Email IDs': doc_usr_details[0]['email'], 'Country': session['country'],
                                             'adults':int(session['adults']),'children':int(session['children']), 'Total People': total_people_count, 
                                             'Reserved Room Type': session['room_type'], 'check_in': datetime.strptime(session['check_in'], '%d-%m-%Y'), 
                                             'check_out': datetime.strptime(session['check_out'], '%d-%m-%Y'),
                                             'Meals':session['meal_type'], 'reservation_status': 'Reserved', 'Price': float(session['total_price'])})

            date_list = get_dates_between(session['check_in'], session['check_out'])
         
            date_list = date_list[:-1]

            col_rooms = collection_rooms.find({'Room Type': session['room_type']}, {'price':1, 'Availability':1, '_id':0})
            doc_list_rooms = list(col_rooms)

            filtered_availability = {}

            for date in date_list:
                if date in doc_list_rooms[0]['Availability']:
                    filtered_availability[date] = doc_list_rooms[0]['Availability'][date]

            # needed for updating count availability
            

            updated_availability = decrement_availability(filtered_availability)
            update_dict = {'Availability.' + k: v for k, v in updated_availability.items()}
            collection_rooms.update_one({'Room Type':session['room_type']}, {'$set': update_dict}, upsert=False)

            # Get all keys in session
            keys = list(session.keys())

            # Iterate over keys and pop them if they are not 'username'
            for key in keys:
                if key != 'username':
                    session.pop(key, None)
        else:
            id_val = get_next_id(collection_booking_1)
            doc_usr_details = collection_users.find({'username':session['username']}, {'email':1})

            collection_booking_1.insert_one({'_id':id_val, 'Customer ID': doc_usr_details[0]['_id'], 'username': session['username'], 
                                             'Customer Names': session['name'], 'Email IDs': doc_usr_details[0]['email'], 'Country': session['country'],
                                             'adults':int(session['adults']),'children':int(session['children']), 'Total People': total_people_count, 
                                             'Reserved Room Type': session['room_type'], 'check_in': datetime.strptime(session['check_in'], '%d-%m-%Y'), 
                                             'check_out': datetime.strptime(session['check_out'], '%d-%m-%Y'),
                                             'Meals':session['meal_type'], 'reservation_status': 'Reserved', 'Price': float(session['total_price'])})

            date_list = get_dates_between(session['check_in'], session['check_out'])
            # print(date_list)
            date_list = date_list[:-1]
            col_rooms = collection_rooms.find({'Room Type': session['room_type']}, {'price':1, 'Availability':1, '_id':0})
            doc_list_rooms = list(col_rooms)

            filtered_availability = {}

            for date in date_list:
                if date in doc_list_rooms[0]['Availability']:
                    filtered_availability[date] = doc_list_rooms[0]['Availability'][date]

            # needed for updating count availability
            

            updated_availability = decrement_availability(filtered_availability)
            update_dict = {'Availability.' + k: v for k, v in updated_availability.items()}
            collection_rooms.update_one({'Room Type':session['room_type']}, {'$set': update_dict}, upsert=False)
            # Get all keys in session
            keys = list(session.keys())

            # Iterate over keys and pop them if they are not 'username'
            for key in keys:
                if key != 'username':
                    session.pop(key, None)

        return render_template('index.html',pay_success=pay_success, room_types=room_types)
    
    for doc in collection_rooms.find():
        key_list = doc.keys()
        if 'Availability' not in key_list:
            update_availability(collection_rooms, doc['Maximum Rooms'], doc['Room Type'])
        else:
            update_existing_availability(collection_rooms, doc['Maximum Rooms'], doc['Room Type'])
   

    if 'username' in session:
        global username
        username = session['username']

        return render_template('index.html', username=session['username'], room_types=room_types)
    else:
        return render_template('index.html', room_types=room_types)

@app.route('/verify/forget/<verification_token>', methods=['GET'])
def verify_email_forget(verification_token):
    """
    function to app route verify_email_forget page

    params:
    verification_token: randomly generated verification token
    """

    user = collection_users.find_one({'token': verification_token})
    if user:
        return redirect(url_for('forget', verification_token=verification_token, notequal = False, success_forget_password = False, success = True))
    

@app.route('/forget', methods=['GET','POST'])
def forget():
    """
    function to app route forget password page

    """

    verification_token = request.args.get('verification_token')
    if request.method == 'POST':
        password = request.form.get('password')
        confPassword = request.form.get('confpassword')
        form_token = request.form.get('token')
        
        if 'username' in session and 'username' == 'db_manager' and password == confPassword:
            collection_users.update_one({'username':session['username']}, {'$set':{'password':hash_password(password)}})
            clear_session()

        if 'username' in session and password == confPassword:
            collection_users.update_one({'username':session['username']}, {'$set':{'password':hash_password(password)}})
            clear_session()
            return render_template('login.html', verification_token=verification_token, notequal =False, forget_success = True, success = False)
        
        if password == confPassword:
            collection_users.update_one({'token':form_token}, {'$set':{'password':hash_password(password)}, '$unset': {'token':None}})
            clear_session()
            return render_template('login.html', verification_token=verification_token, notequal =False, forget_success = True, success = False)
        
        else:
            return render_template('forget.html', verification_token=verification_token, notequal = True, forget_success = False, success = False)
    return render_template('forget.html', verification_token=verification_token, notequal = False, forget_success = False, success = True)

@app.route('/admin/index')
def index_admin():
    """
    function to app route admin dashboard page

    """

    user_counts = collection_users.count()

    bookings_count_0 = collection_booking_0.count({'reservation_status':'Check-Out'})
    bookings_count_1 = collection_booking_1.count({'reservation_status':'Check-Out'})
    bookings_count = bookings_count_0 + bookings_count_1

    room_types_count = collection_rooms.count()
    meals_count = collection_meals.count()
    return render_template('admin/index.html', username = session['username'], user_counts = user_counts, 
                                   bookings_count = bookings_count, room_types_count=room_types_count, meals_count=meals_count)


@app.route('/admin/users', methods=['GET','POST'])
def users_admin():
    """
    function to app route admin users page

    """

    if request.method == 'POST':
        query = request.form.get('search_query_user')

        if query:
            search_regex = re.compile(re.escape(query), re.IGNORECASE)
            query_result = collection_users.find({'$or': [{'username': {'$regex': search_regex}}, {'email': {'$regex': search_regex}}]})

            result_list = list(query_result)
            return render_template('admin/users.html', username = session['username'], users=result_list)
        else:
            return 'Please provide a query parameter.', 400


    return render_template('admin/users.html', username = session['username'])

@app.route('/admin/rooms', methods=['GET','POST'])
def users_rooms():
    """
    function to app route admin rooms page

    """

    if request.method == 'POST':
        query = request.form.get('search_query_user')

        if query:
            search_regex = re.compile(re.escape(query), re.IGNORECASE)
            query_result = list(collection_rooms.find({'Room Type': {'$regex': search_regex}}))
            result_list = query_result
            return render_template('admin/rooms.html', username = session['username'], rooms=result_list)
        else:
            return 'Please provide a query parameter.', 400
        
    return render_template('admin/rooms.html', username = session['username'])
            


@app.route('/admin/meals', methods=['GET','POST'])
def users_meals():
    """
    function to app route admin meals page

    """

    if request.method == 'POST':
        query = request.form.get('search_query_user')

        if query:
            search_regex = re.compile(re.escape(query), re.IGNORECASE)
            query_result = list(collection_meals.find({'Meal Type': {'$regex': search_regex}}))
            result_list = query_result
            return render_template('admin/meals.html', username = session['username'], meals=result_list)
        else:
            return 'Please provide a query parameter.', 400

    # get_total_meals = list(collection_meals.find())

    return render_template('admin/meals.html', username = session['username'])

@app.route('/admin/bookings', methods=['GET','POST'])
def users_bookings():
    """
    function to app route admin bookings page

    """

    if request.method == 'POST':
        query = request.form.get('search_query_user')

        if query:
            search_regex = re.compile(re.escape(query), re.IGNORECASE)
            query_result_0 = list(collection_booking_0.find({'$or': [{'username': {'$regex': search_regex}}, {'email': {'$regex': search_regex}}, {'Customer Names': {'$regex': search_regex}}]}))
            query_result_1 = list(collection_booking_1.find({'$or': [{'username': {'$regex': search_regex}}, {'email': {'$regex': search_regex}}, {'Customer Names': {'$regex': search_regex}}]}))


            result_list = query_result_0 + query_result_1
            return render_template('admin/bookings.html', username = session['username'], bookings=result_list)
        else:
            return 'Please provide a query parameter.', 400

    return render_template('admin/bookings.html', username = session['username'])

@app.route('/emailVerify', methods=['GET', 'POST'])
def emailVerify():
    """
    function to app route email verification page

    """

    if request.method == 'POST':
        email = request.form.get('email')

        db_email = collection_users.find_one({'email':email})

        if db_email is None:
            return render_template('emailVerify.html', notExist=True, success=False)
        
        # generate unique token
        unique_token = generate_verification_token()

        # Insert the data in database
        collection_users.update_one({'email':email}, {'$set':{'token':unique_token}})

        # email verification
        send_verification_email(email, unique_token, forget_flag=True)

        return render_template('emailVerify.html', notExist=False, success=True)
    
    return render_template('emailVerify.html', notExist=False, success=False)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    function to app route login page

    """

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user_document = collection_users.find_one({'$or':[{'username':username}, {'email':username}]})

        if user_document is None:
            return render_template('login.html', notExist=True, success=False, unverified=False)
        
        if user_document['is_verified'] == False:
            return render_template('login.html', notExist=False, success=False, unverified=True)
        
        if not verify_password(password, user_document['password']):
            return render_template('login.html', notExist=False, notPass = True, success=False, unverified=False)
        
 
        session['username'] = user_document['username']
        
        if user_document['username'] == 'db_manager':
            return redirect(url_for('index_admin'))
        return redirect(url_for('index'))

    return render_template('login.html', notExist=False, success=False, notPass =False, unverified=False)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    function to app route signup page

    """

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if username or email already exists
        if is_duplicate_entry(collection_users, username, email):
            return render_template('signup.html', duplicate=True, success=False)

        # Hash the password before storing it in the database
        hashed_password = hash_password(password)

        # get user ID
        user_id = get_next_id(collection_users)

        # generate unique token
        unique_token = generate_verification_token()

        # Add the record to the database
        user_data = {'_id':user_id, 'username': username, 'email': email, 'password':hashed_password, "token":unique_token, "is_verified": False}

        # email verification
        send_verification_email(email, unique_token)

        # Insert the data in database
        collection_users.insert_one(user_data)

        # print(f"Adding record to database: Username - {username}, Email - {email}")
        return render_template('signup.html', duplicate=False, success=True)

    return render_template('signup.html', duplicate=False, success=False)


@app.route('/delete_user', methods=['GET','POST'])
def delete_user():
    """
    function to app route delete user

    """

    if request.method == 'POST':
        # Perform deletion from MongoDB
        username = request.form.get('username')

        find_count_booking_0 = collection_booking_0.find({'username': username})
        find_count_booking_1 = collection_booking_1.find({'username': username})
        all_bookings = list(find_count_booking_0) + list(find_count_booking_1)

        for doc in all_bookings:
            formatted_check_in = doc['check_in'].strftime('%Y-%m-%d')
            formatted_check_out = doc['check_out'].strftime('%Y-%m-%d')
            room_type = doc['Reserved Room Type']
            update_availability_dict(formatted_check_in, formatted_check_out, collection_rooms, room_type, 'increment')

        result = collection_users.delete_one({'username': username})
        collection_booking_0.delete_many({'username': username})
        collection_booking_1.delete_many({'username': username})

        if result.deleted_count == 1:
            del_flag = True
            return redirect(url_for('users_admin',del_flag=del_flag))  # Redirect to the users_admin route after successful deletion
        else:
            # Handle deletion failure (optional)
            return "Error: Record not found or deletion failed"
    else:
        return "Invalid request method"
    
@app.route('/delete_room', methods=['GET','POST'])
def delete_room():
    """
    function to app route delete room

    """

    if request.method == 'POST':
        # Perform deletion from MongoDB
        room_type = request.form.get('room_type')
        result = collection_rooms.delete_one({'Room Type': room_type})
        if result.deleted_count == 1:
            delRoom = True
            return redirect(url_for('users_rooms', delRoom=delRoom))  # Redirect to the users_admin route after successful deletion
        else:
            # Handle deletion failure (optional)
            return "Error: Record not found or deletion failed"
    else:
        return "Invalid request method"

@app.route('/update_room', methods=['GET','POST'])
def update_room():
    """
    function to app route update room

    """

    if request.method == 'POST':
        # Perform deletion from MongoDB
        room_type_old = request.form.get('room_type_old')
        max_room_old = request.form.get('max_room_old')


        room_type = request.form.get('room_type')
        room_price = request.form.get('room_price')
        room_bed = request.form.get('room_beds')
        room_utility = request.form.get('room_utilities')
        room_counts = request.form.get('room_counts')
        room_counts = int(room_counts)
        room_price = float(room_price)
        max_room_old = int(max_room_old)


        if room_counts < max_room_old:
            room_counts_min_collection = collection_rooms.find({'Room Type':room_type_old}, {'Availability':1, '_id':0})
            doc_room_counts_min_collection = next(room_counts_min_collection)
            avail_list = list(doc_room_counts_min_collection['Availability'].values())

            
            neg_diff = room_counts - max_room_old


            if (neg_diff + min(avail_list)) < 0:
                return redirect(url_for('users_rooms', neg_val_error=True))
            
            else:
                update_admin_all_availability_dates(neg_diff, collection_rooms, room_type_old)
        
        elif room_counts > max_room_old:
            positive_diff = room_counts - max_room_old
            update_admin_all_availability_dates(positive_diff, collection_rooms, room_type_old)            
        ## changed currently same
        result = collection_rooms.update_one({'Room Type':room_type_old}, {'$set':{'Room Type': room_type, 'price': room_price, 'Beds': room_bed, 'Utilities':room_utility, 'Maximum Rooms':room_counts}})
        if result:
            updRoom = True
            return redirect(url_for('users_rooms',updRoom=updRoom))  # Redirect to the users_admin route after successful deletion
        else:
            # Handle deletion failure (optional)
            return "Error: Update failed"
    else:
        return "Invalid request method"

@app.route('/add_room', methods=['GET','POST'])
def add_room():
    """
    function to app route add room

    """

    if request.method == 'POST':
        # Perform deletion from MongoDB
        room_type_add = request.form.get('room_type')
        room_price_add = request.form.get('room_price')
        room_bed_add = request.form.get('room_beds')
        room_utility_add = request.form.get('room_utilities')
        room_count_add = request.form.get('room_counts')
        room_count_add = int(room_count_add)

        # get meal ID
        room_id = get_next_id(collection_rooms)

        result = collection_rooms.insert_one({'_id': room_id ,'Room Type': room_type_add, 'price': float(room_price_add), 'Beds':room_bed_add, 
                                              'Utilities': room_utility_add, 'Maximum Rooms': room_count_add})
        update_availability(collection_rooms, room_count_add, room_type_add)

        if result:
            addRoom = True
            return redirect(url_for('users_rooms', addRoom=addRoom))  # Redirect to the users_admin route after successful deletion
        else:
            # Handle deletion failure (optional)
            return "Error: Add failed"
    else:
        return "Invalid request method"

@app.route('/delete_meal', methods=['GET','POST'])
def delete_meal():
    """
    function to app route delete meals

    """

    if request.method == 'POST':
        # Perform deletion from MongoDB
        meal_type = request.form.get('meal_type')
        result = collection_meals.delete_one({'Meal Type': meal_type})
        if result.deleted_count == 1:
            delMeal = True
            return redirect(url_for('users_meals',delMeal=delMeal))  # Redirect to the users_admin route after successful deletion
        else:
            # Handle deletion failure (optional)
            return "Error: Record not found or deletion failed"
    else:
        return "Invalid request method"

@app.route('/update_meal', methods=['GET','POST'])
def update_meal():
    """
    function to app route update meals

    """

    if request.method == 'POST':
        # Perform deletion from MongoDB
        meal_type_old = request.form.get('meal_type_old')
        meal_type_update = request.form.get('meal_type')
        meal_price_update = request.form.get('meal_price')
        result = collection_meals.update_one({'Meal Type':meal_type_old}, {'$set':{'Meal Type': meal_type_update, 'price': float(meal_price_update)}})
        if result:
            updMeal = True
            return redirect(url_for('users_meals', updMeal=updMeal))  # Redirect to the users_admin route after successful deletion
        else:
            # Handle deletion failure (optional)
            return "Error: Update failed"
    else:
        return "Invalid request method"

@app.route('/add_meal', methods=['GET','POST'])
def add_meal():
    """
    function to app route add meals
    """

    if request.method == 'POST':
        # Perform deletion from MongoDB
        meal_type_add = request.form.get('meal_type')
        meal_price_add = request.form.get('meal_price')

        # get meal ID
        meal_id = get_next_id(collection_meals)

        result = collection_meals.insert_one({'_id':meal_id, 'Meal Type': meal_type_add, 'price': float(meal_price_add)})
        if result:
            addMeal = True
            return redirect(url_for('users_meals', addMeal=addMeal))  # Redirect to the users_admin route after successful deletion
        else:
            # Handle deletion failure (optional)
            return "Error: Add failed"
    else:
        return "Invalid request method"
    
@app.route('/update_status', methods=['GET','POST'])
def update_status():
    """
    function to app route update booking status

    """

    if request.method == 'POST':
        # Perform deletion from MongoDB
        booking_status = request.form.get('status_type')
        booking_id = request.form.get('booking_id')
        booking_p_count = request.form.get('people_count')

        db_val_num = get_db_on_hash(int(booking_p_count))
        
        if db_val_num == 0:
            collection_booking_0.update_one({'_id':int(booking_id)}, {'$set':{'reservation_status': booking_status}})
        else:
            collection_booking_1.update_one({'_id':int(booking_id)}, {'$set':{'reservation_status': booking_status}})

        print('status id total people db_val', booking_status, booking_id, booking_p_count, db_val_num)
        return redirect(url_for('users_bookings'))  # Redirect to the users_admin route after successful deletion
    else:
        return "Invalid request method"

@app.route('/logout')
def logout():
    """
    function to app route logout page

    """

    clear_session()
    return redirect(url_for('index'))

@app.route('/checkout', methods=['POST', 'GET'])
def checkout():
    """
    function to app route checkout page

    """

    if request.method == 'POST':
        checkin = session['check_in']
        checkout = session['check_out']
        max_guests = session['max_guests']
        room_type = session['room_type']

        name = request.form.get('name')
        country = request.form.get('country')
        adults = request.form.get('adults')
        children = request.form.get('children')
        meal_type = request.form.get('meal')

        session['name'] = name
        session['country'] = country
        session['adults'] = adults
        session['children'] = children
        session['meal_type'] = meal_type
        
        total_people = int(adults) + int(children)

        if total_people == 0:
            no_val_people = True
            return redirect(url_for('booking_form', no_val_people = no_val_people))
        
        max_val = False
        if total_people>int(max_guests):
            max_val = True
            return redirect(url_for('booking_form', max_val = max_val))

        return render_template('checkout.html',checkin=checkin, checkout=checkout, name=name, country=country, adults=adults, children=children, room_type=room_type, meal_type=meal_type)

    else:
        checkin = session.get('check_in')
        checkout = session.get('check_out')
        name = session.get('name')
        country = session.get('country')
        adults = session.get('adults')
        room_type = session.get('room_type')
        meal_type = session.get('meal_type')
        children = session.get('children')
        return render_template('checkout.html',checkin=checkin, checkout=checkout, name=name, country=country, adults=adults, children=children, room_type=room_type, meal_type=meal_type)


@app.route('/process_payment', methods=['POST', 'GET'])
def process_payment():
    """
    function to app route process payment page

    """

    if request.method == 'POST':
        checkin = request.form.get('check_in')
        checkout = request.form.get('check_out')
        name = request.form.get('name')
        country = request.form.get('country')
        adults = request.form.get('adults')
        children = request.form.get('children')
        room_type = request.form.get('room_type')
        meal_type = request.form.get('meal')

        
        date_list = get_dates_between(checkin, checkout)


        col_rooms = collection_rooms.find({'Room Type': room_type}, {'price':1, 'Availability':1, '_id':0})
        col_meals = collection_meals.find({'Meal Type': meal_type}, {'price':1, '_id':0})
        doc_list_rooms = list(col_rooms)
        doc_list_meals = list(col_meals)
        filtered_availability = {}

        for date in date_list:
            if date in doc_list_rooms[0]['Availability']:
                filtered_availability[date] = doc_list_rooms[0]['Availability'][date]

        # needed for updating count availability
        

        updated_availability = decrement_availability(filtered_availability)
    
        room_price = float(doc_list_rooms[0]['price']) * (len(date_list) - 1)
        meal_price = float(doc_list_meals[0]['price']) * (len(date_list) - 1)
        total_price = room_price + meal_price
        session['meal_price'] = meal_price
        session['total_price'] = total_price


        # send_confirmation_email(app, email_val, details_email)
        return render_template('process_payment.html',checkin=checkin, checkout=checkout, name=name, country=country, adults=adults, children=children, room_type=room_type, meal_type=meal_type, updated_availability=updated_availability, total_price=total_price)
    else:
        total_price = session.get('total_price')
        return render_template('process_payment.html', total_price=total_price)

@app.route('/my_bookings', methods=['POST', 'GET'])
def my_bookings():
    """
    function to app route user bookings page page

    """

    booking_user_doc_0 = collection_booking_0.find({'username':session['username']}, {'Reserved Room Type':1, 'adults':1,'children':1, 'Total People':1,
                                                                                    'check_in':1, 'check_out':1, 'Meals':1,
                                                                                    'reservation_status':1, 'Price':1})
    booking_user_doc_1 = collection_booking_1.find({'username':session['username']}, {'Reserved Room Type':1, 'adults':1,'children':1, 'Total People':1,
                                                                                    'check_in':1, 'check_out':1, 'Meals':1,
                                                                                    'reservation_status':1, 'Price':1})
    
    first_db = list(booking_user_doc_0)
    second_db = list(booking_user_doc_1)

    total_user_data = first_db + second_db

    # Convert datetime objects to strings in "dd-mm-yyyy" format
    for data in total_user_data:
        data['check_in'] = data['check_in'].strftime("%d-%m-%Y")
        data['check_out'] = data['check_out'].strftime("%d-%m-%Y")

    today = datetime.today().date()
    formatted_date_today = today.strftime('%d-%m-%Y')

    
    for data in total_user_data:
        today_date = datetime.strptime(formatted_date_today, '%d-%m-%Y').date()
        date_to_compare = datetime.strptime(data['check_in'], '%d-%m-%Y').date()

        if date_to_compare < today_date:
            data['upd_del_flag'] = False
        else:
            data['upd_del_flag'] = True

    print('get book: ',total_user_data, formatted_date_today)
    return render_template('my_bookings.html', total_user_data = total_user_data)

@app.route('/update_date', methods=['POST', 'GET'])
def update_date():
    """
    function to app route update dates

    """

    if request.method == "POST":
        cin_new = request.form.get('check_in')
        cout_new = request.form.get('check_out')
        room_type = request.form.get('room_type')
        bid = request.form.get('booking_id')
        cin_old = request.form.get('check_in_old')
        cout_old = request.form.get('check_out_old')
        total_people = request.form.get('total_people_count')

        date_list1 = get_dates_between(cin_new, cout_new)

        date_list1 = date_list1[:-1]

        col_rooms = collection_rooms.find({'Room Type': room_type}, {'price':1, 'Availability':1, '_id':0})
        doc_list_rooms1 = list(col_rooms)

        filtered_availability = {}

        for date in date_list1:
            if date in doc_list_rooms1[0]['Availability']:
                filtered_availability[date] = doc_list_rooms1[0]['Availability'][date]

        if any(value == 0 for value in filtered_availability.values()):
            no_dates = True
            return redirect(url_for('my_bookings', no_dates = no_dates))
    
        original_date_cin_old = datetime.strptime(cin_old, '%d-%m-%Y')
        formatted_date_str_cin_old = original_date_cin_old.strftime('%Y-%m-%d')
        original_date_cout_old = datetime.strptime(cout_old, '%d-%m-%Y')
        formatted_date_str_cout_old = original_date_cout_old.strftime('%Y-%m-%d')

        original_date_cin_new = datetime.strptime(cin_new, '%d-%m-%Y')
        formatted_date_str_cin_new = original_date_cin_new.strftime('%Y-%m-%d')
        original_date_cout_new = datetime.strptime(cout_new, '%d-%m-%Y')
        formatted_date_str_cout_new = original_date_cout_new.strftime('%Y-%m-%d')

        update_availability_dict(formatted_date_str_cin_old, formatted_date_str_cout_old, collection_rooms, room_type, 'increment')

        update_availability_dict(formatted_date_str_cin_new, formatted_date_str_cout_new, collection_rooms, room_type, 'decrement')

        db_val = get_db_on_hash(int(total_people))

        if db_val == 0:
            collection_booking_0.update_one({'_id':int(bid)}, {'$set':{'check_in': datetime.strptime(cin_new, '%d-%m-%Y'), 
                                                                       'check_out': datetime.strptime(cout_new, '%d-%m-%Y')}})
        else:
            collection_booking_1.update_one({'_id':int(bid)}, {'$set':{'check_in': datetime.strptime(cin_new, '%d-%m-%Y'), 
                                                                       'check_out': datetime.strptime(cout_new, '%d-%m-%Y')}})

        updBook = True
        return redirect(url_for('my_bookings',updBook=updBook))

@app.route('/delete_booking', methods=['POST', 'GET'])
def delete_booking():
    """
    function to app route delete booking

    """

    if request.method == "POST":
        cin = request.form.get('check_in')
        cout = request.form.get('check_out')
        bid = request.form.get('booking_id')
        room_type = request.form.get('room_type')
        total_people = request.form.get('total_people')

        original_date_cin = datetime.strptime(cin, '%d-%m-%Y')
        formatted_date_str_cin = original_date_cin.strftime('%Y-%m-%d')
        original_date_cout = datetime.strptime(cout, '%d-%m-%Y')
        formatted_date_str_cout = original_date_cout.strftime('%Y-%m-%d')

        update_availability_dict(formatted_date_str_cin, formatted_date_str_cout, collection_rooms, room_type, 'increment')

        db_val = get_db_on_hash(int(total_people))

        if db_val == 0:
            collection_booking_0.delete_one({'_id':int(bid)})
        else:
            collection_booking_1.delete_one({'_id':int(bid)})
        
        delYes = True
        return redirect(url_for('my_bookings', delYes=delYes))
    
@app.route('/update_password', methods=['GET','POST'])
def update_password():
    """
    function to app route update password page

    """

    return render_template('update_password.html')

@app.route('/room_options', methods=['GET','POST'])
def room_options():
    """
    function to app route room options page

    """

    room_data = collection_rooms.find({})

    return render_template('room_options.html', room_data = list(room_data))

@app.route('/meal_options', methods=['GET','POST'])
def meal_options():
    """
    function to app route meal options page

    """

    meal_data_col = collection_meals.find({})
    meal_data = list(meal_data_col)
    return render_template('meal_options.html', meal_data=meal_data)

@app.route('/about_us', methods=['GET','POST'])
def about():
    """
    function to app route about us page

    """
    return render_template('about_us.html')


if __name__ == '__main__':
    app.run(debug=True)