from passlib.hash import sha256_crypt

import secrets
from datetime import datetime, timedelta


def is_duplicate_entry(collection_users, username, email):
    """
    function to check duplicate entries of username and email

    params:
    username: username
    email: Email ID
    collections_users: users collection
    """

    # Check if the username or email already exists in the database
    return collection_users.count_documents({'$or': [{'username': username}, {'email': email}]}) > 0

def hash_password(password):
    """
    function to generate password hash

    params:
    password: password input
    """
    # Hash the password using passlib's sha256_crypt
    return sha256_crypt.hash(password)

def verify_password(input_password, hashed_password):
    """
    function to verify input password with hashed password

    params:
    input_password: password input
    hashed_password: hash of password in database
    """
    # Verify the input password against the stored hashed password
    return sha256_crypt.verify(input_password, hashed_password)

def get_next_id(collection):
    """
    function to get the next id for inserting new data

    params:
    collection: name of the collection
    """

    last_id = collection.find_one(sort=[('_id', -1)])

    if last_id is None:
        new_id = 1
        return new_id

    else:
        new_id = int(last_id['_id']) + 1
        return new_id

def generate_verification_token():
    """
    function to generate new verification token for email verification
    """

    return secrets.token_urlsafe(32)


def update_availability(collection_rooms, availability, room_type):
    """
    function to update room availability on initializing a new room type

    params:
    collection_rooms: rooms collection
    availability: availability count for room
    room_type: type of room
    """

    # Connect to MongoDB

    # Get today's date
    today = datetime.today().date()

    # Initialize dictionary to store date availability
    dates_availability = {}
    for i in range(90):
        date = today + timedelta(days=i)
        date_str = date.strftime('%d-%m-%Y')
        dates_availability[str(date_str)] = availability

    # Update MongoDB document


    query = {"Room Type": room_type}  # Query to find the document
    update_query = {"$set": {"Availability": dates_availability}}  # Update query
    collection_rooms.update_one(query, update_query, upsert=True)  # Upsert=True to insert



def update_existing_availability(collection, max_rooms, room_type):
    """
    function to update availability of existing rooms
    
    params:
    collection: rooms collection
    max_rooms: availability count for room
    room_type: type of room
    """

    # Get today's date
    today = datetime.today().strftime('%d-%m-%Y')

    # Create a list of dates starting from today till 90 days
    dates = [(datetime.strptime(today, '%d-%m-%Y') + timedelta(days=i)).strftime('%d-%m-%Y') for i in range(90)]

    # Fetch the existing document
    existing_doc = collection.find_one({"Room Type": room_type})

    # If document exists
    if existing_doc:
        # Remove past dates before today's date (including today)
        existing_doc['Availability'] = {date: existing_doc['Availability'][date] for date in existing_doc['Availability'] if datetime.strptime(date, '%d-%m-%Y') >= datetime.strptime(today, '%d-%m-%Y')}

        # Add new dates and maximum rooms value
        for date in dates:
            if date not in existing_doc['Availability']:
                existing_doc['Availability'][date] = max_rooms

        # Update the document in the collection
        collection.replace_one({"_id": existing_doc["_id"]}, existing_doc)


def update_admin_all_availability_dates(diff, collection_rooms, room_type_old):
    """
    function to update room availability upon update of room counts by admin

    params:
    diff: difference between old room availability count and new room availability count
    collection_rooms: rooms collection
    room_type_old: room type
    """

    room_collection = collection_rooms.find({'Room Type': room_type_old}, {'Availability':1, '_id':0})

    document = next(room_collection)
    old_availability = list(document['Availability'].values())
    old_keys = list(document['Availability'].keys())

    new_availability = [x + diff for x in old_availability]

    new_result = dict(zip(old_keys, new_availability))

    collection_rooms.update_one({'Room Type': room_type_old}, {"$set": {"Availability": new_result}})

def get_dates_between(checkin_date_str, checkout_date_str):
    """
    function to get range of dates between check-in date and check-out date

    params:
    check_date_str: check-in date of type string (dd-mm-yyyy)
    checkout_date_str: check-out date of type string (dd-mm-yyyy)
    """

    # Parse checkin and checkout dates
    checkin_date = datetime.strptime(checkin_date_str, '%d-%m-%Y')
    checkout_date = datetime.strptime(checkout_date_str, '%d-%m-%Y')
    # Generate the list of dates between checkin and checkout
    dates_between = []
    current_date = checkin_date
    while current_date <= checkout_date:
        dates_between.append(current_date.strftime('%d-%m-%Y'))
        current_date += timedelta(days=1)

    return dates_between


def get_db_on_hash(people_count):
    """
    function to hash bookings data based on the people count. If even, record is stored in booking_0, else booking_1.

    params:
    people_count: total people in the booking
    """
    if people_count % 2 == 0:
        return 0
    return 1

def decrement_availability(availability_dict):
    """
    function to decrement availability count

    params:
    availability_dict: Availability dictionary with date key and availability count as value

    """
    
    for date in availability_dict:
        availability_dict[date] -= 1
    return availability_dict


def increment_availability(availability_dict):
    """
    function to increment availability count

    params:
    availability_dict: Availability dictionary with date key and availability count as value

    """

    for date in availability_dict:
        availability_dict[date] += 1
    return availability_dict


def update_availability_dict(cin, cout, collection_rooms, room_type, operation):
    """
    function to update availability dictionary within a given date range

    params:
    cin: check-in date
    cout: check-out date
    collection_rooms: rooms collection
    room_type: type of room
    operation: increment or decrement
    """
    
    ip_date_list = []
    for date in [cin, cout]:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
        converted_date = parsed_date.strftime("%d-%m-%Y")
        ip_date_list.append(converted_date)


    date_list = get_dates_between(ip_date_list[0], ip_date_list[1])

    date_list = date_list[:-1]

    col_rooms = collection_rooms.find({'Room Type': room_type}, {'price':1, 'Availability':1, '_id':0})
    doc_list_rooms = list(col_rooms)
    
    filtered_availability = {}

    for date in date_list:
        if date in doc_list_rooms[0]['Availability']:
            filtered_availability[date] = doc_list_rooms[0]['Availability'][date]
            print('in loop')
            print(filtered_availability)

    if operation == 'increment':
        updated_availability = increment_availability(filtered_availability)
    else:
        updated_availability = decrement_availability(filtered_availability)
    update_dict = {'Availability.' + k: v for k, v in updated_availability.items()}

    collection_rooms.update_one({'Room Type':room_type}, {'$set': update_dict}, upsert=False)
