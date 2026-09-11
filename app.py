import os
import time
from flask import Flask
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask import render_template,request,redirect,url_for,flash 
from flask_login import LoginManager, login_user, login_required, current_user, logout_user 
from datetime import datetime,date 
from werkzeug.utils import secure_filename 


app = Flask(__name__)                                                          

#CONFIGURE DATABASE 
app.config['SECRET_KEY']='trekking-secret-key'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///trekking.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']= False 
app.config['UPLOAD_FOLDER'] = 'static/uploads' 

db.init_app(app)

#CONFIGURE LOGIN_MANAGER
login_manager=LoginManager()  
login_manager.init_app(app)
login_manager.login_view='login'

#DATABASE_LOADER
from models import User, Trek, Booking

#USER_LOADER
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()

    admin= User.query.filter_by(email='admin@trek.com').first()
    if not admin:
        admin=User(
            name='Admin',
            email='admin@trek.com',
            password=generate_password_hash('admin123'),
            role='admin',
            status='approved'
        )
        
        db.session.add(admin)
        db.session.commit()
        print("Admin account created!")

#INDEX_HOME_ROUTE
@app.route('/')
def home():
    featured_treks = Trek.query.limit(6).all()
    return render_template('index.html',treks=featured_treks)

#USER_REGISTER_ROUTE
@app.route('/register-user',methods=['GET','POST'])
def register_user():
    if request.method == 'POST':
        name=request.form['name']
        email=request.form['email']
        phone=request.form['phone']
        password=generate_password_hash(request.form['password'])

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash ("Email already registered. Please use another email.", "danger")
            return redirect('/register-user')
        
        user = User(
            name=name,
            email=email,
            phone=phone,
            password=password,
            role='user',
            status='approved'
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.","success")

        return redirect('/login')
    return render_template('auth/register_user.html')

#STAFF_REGISTRATION_ROUTE
@app.route('/register-staff',methods=['GET','POST'])
def register_staff():

    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        phone=request.form['phone']
        password=generate_password_hash(request.form['password'])

        existing_user=User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please use another email.","danger")
            return redirect('/register-staff')
        
        staff=User(
            name=name,
            email=email,
            phone=phone,
            password=password,
            role='staff',
            status='pending'
        )

        db.session.add(staff)
        db.session.commit()
        flash("Registration successful. Waiting for admin approval.","success")

        return redirect('/login')
    return render_template('auth/register_staff.html')

#LOGIN_ROUTE
@app.route('/login',methods=['GET','POST'])
def login():

    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']
        user=User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password,password):
            # Check blacklist FIRST
            if user.status=='blacklisted':
                flash("Your account is blacklisted.","danger")
                return redirect('/login')
           
            # Then check staff approval
            if user.role=='staff' and user.status != 'approved':
                flash("Staff account waiting for admin approval.","warning")
                return redirect('/login')
            
            login_user(user)

            if user.role=='admin':
                return redirect('/admin-dashboard')
            elif user.role=='staff':
                return redirect('/staff-dashboard')
            else:
                return redirect('/user-dashboard')
            
        flash ("Invalid email or password.","danger")
        return redirect('/login')
     
    return render_template('auth/login.html')   

#ADMIN_DASHBOARD
@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.role!='admin':
        return "Access Denied"
    total_treks=Trek.query.count()
    total_users=User.query.filter_by(role='user').count()
    total_staff=User.query.filter_by(role='staff').count()
    total_bookings=Booking.query.count()

    return render_template(
        'admin/dashboard.html',
        total_treks=total_treks,
        total_users=total_users,
        total_staff=total_staff,
        total_bookings=total_bookings
    )



#STAFF_DASHBOARD
@app.route('/staff-dashboard')
@login_required
def staff_dashboard():
    if current_user.role!='staff':
        return "Access Denied"
    assigned_treks=Trek.query.filter_by( assigned_staff_id=current_user.id).all()

    return render_template('staff/dashboard.html',treks=assigned_treks)


#USER_DASHBOARD
@app.route('/user-dashboard')
@login_required
def user_dashboard():

    if current_user.role != 'user':
        return "Access Denied"

    difficulty = request.args.get('difficulty')
    location = request.args.get('location')

    query = Trek.query.filter_by(status='open')

    if difficulty:
        query = query.filter_by(difficulty=difficulty)

    if location:
        query = query.filter(Trek.location.contains(location))

    open_treks = query.all()

    return render_template('user/dashboard.html',treks=open_treks)

#LOGOUT_ROUTE
@app.route('/logout')
@login_required
def logout():
    logout_user()

    flash("Logged out successfully.","info")
    return redirect('/login')

#ADD_TREK_ROUTE
@app.route('/admin/add-trek', methods=['GET', 'POST'])
@login_required
def add_trek():

    if current_user.role != 'admin':
        return "Access Denied"

    if request.method == 'POST':

        start_date = datetime.strptime(request.form['start_date'],'%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'],'%Y-%m-%d').date()

        slots = int(request.form['available_slots'] ) 
        duration = int(request.form['duration'])

        if duration <= 0:
            flash("Duration must be greater than 0.","danger")
            return redirect('/admin/add-trek')

        # Validation 1: Past date
        if start_date < date.today():
            flash("Start date cannot be in the past.","danger")

            return redirect('/admin/add-trek')

        # Validation 2: End date
        if end_date < start_date:
            flash("End date must be after start date.","danger")

            return redirect('/admin/add-trek')

        # Validation 3: Slots
        if slots < 0:
            flash("Available slots cannot be negative.","danger")

            return redirect('/admin/add-trek')
        
        # Image Uploads : Image
        image = request.files.get('image')
        filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)

            image.save( os.path.join(app.config['UPLOAD_FOLDER'],filename))

        trek = Trek(

            trek_name=request.form['trek_name'],
            location=request.form['location'],
            difficulty=request.form['difficulty'],
            duration=duration,
            available_slots=slots,
            start_date=start_date,
            end_date=end_date,
            description=request.form['description'],
            image=filename

        )

        db.session.add(trek)

        db.session.commit()

        flash("Trek added successfully.","success")

        return redirect('/admin-treks')

    return render_template('admin/add_trek.html')

#TREKS_ROUTE
@app.route('/admin-treks')
@login_required
def admin_treks():
    if current_user.role!='admin':
        return "Access Denied"
    
    treks=Trek.query.all()

    return render_template('admin/treks.html',treks=treks)

#APPROVE_STAFF_ROUTE
@app.route('/admin/staff')
@login_required
def admin_staff():
    if current_user.role !='admin':
        return "Access Denied"
    
    staff_members=User.query.filter_by(role='staff').all()
    
    return render_template('admin/staff.html',staff_members=staff_members)

#APPROVAL_ROUTE
@app.route('/approve-staff/<int:staff_id>')
@login_required
def approve_staff(staff_id):
    if current_user.role !='admin':
        return "Access Denied"
    
    staff=User.query.get(staff_id)

    if staff:
        staff.status='approved'
        db.session.commit()

        flash("Staff approved successfully.","success")

    return redirect('/admin/staff') 

#EDIT_TREK_ROUTE
@app.route('/edit-trek/<int:trek_id>', methods=['GET', 'POST'])
@login_required
def edit_trek(trek_id):

    if current_user.role != 'admin':
        return "Access Denied"

    trek = Trek.query.get_or_404(trek_id)

    if request.method == 'POST':

        start_date = datetime.strptime(request.form['start_date'],'%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'],'%Y-%m-%d').date()

        slots = int(request.form['available_slots'])

        duration = int(request.form['duration'])
        if duration <= 0:
            flash("Duration must be greater than 0.","danger")
            return redirect(f'/edit-trek/{trek.id}')

        # Validation 1: End date
        if end_date < start_date:
            flash("End date must be after start date.","danger")

            return redirect(f'/edit-trek/{trek.id}')

        # Validation 2: Slots
        if slots < 0:
            flash("Available slots cannot be negative.","danger")

            return redirect(f'/edit-trek/{trek.id}')
        
        image=request.files.get('image')
        if image and image.filename:
            filename=(str(int(time.time() )) + "_" + secure_filename(image.filename) )
            image.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            trek.image=filename

        trek.trek_name = request.form['trek_name']
        trek.location = request.form['location']
        trek.difficulty = request.form['difficulty']
        trek.duration = duration

        trek.available_slots = slots
        trek.start_date = start_date
        trek.end_date = end_date
        trek.description = request.form['description']

        db.session.commit()

        flash("Trek updated successfully.","success")

        return redirect('/admin-treks')

    return render_template('admin/edit_trek.html',trek=trek)

#DELETE_TREK_ROUTE
@app.route('/delete-trek/<int:trek_id>')
@login_required
def delete_trek(trek_id):

    if current_user.role != 'admin':
        return "Access Denied"

    trek = Trek.query.get_or_404(trek_id)

    bookings=Booking.query.filter_by(trek_id=trek.id).all()

    for booking in bookings:
        db.session.delete(booking)

    db.session.delete(trek)
    db.session.commit()

    flash("Trek deleted successfully.","danger")

    return redirect('/admin-treks')

#ASSIGN_STAFF_ROUTE
@app.route('/assign-staff/<int:trek_id>', methods=['GET', 'POST'])
@login_required
def assign_staff(trek_id):

    if current_user.role != 'admin':
        return "Access Denied"

    trek = Trek.query.get_or_404(trek_id)

    staff_members = User.query.filter_by(
        role='staff',
        status='approved'
    ).all()

    if request.method == 'POST':

        trek.assigned_staff_id = int(
            request.form['staff_id']
        )

        db.session.commit()

        flash("Staff assigned successfully.","success")

        return redirect('/admin-treks')

    return render_template(
        'admin/assign_staff.html',
        trek=trek,
        staff_members=staff_members
    )

#MANAGE_TREK_ROUTE
@app.route('/manage-trek/<int:trek_id>', methods=['GET','POST'])
@login_required
def manage_trek(trek_id):
    if current_user.role!='staff':
        return "Access Denied"
    trek=Trek.query.get_or_404(trek_id)

    #security_check
    if trek.assigned_staff_id != current_user.id:
        flash("You are not assigned to this trek.",
              "danger")
        
        return redirect('/staff-dashboard')
    
    if request.method == "POST":
        trek.available_slots = int(request.form['available_slots'])
        trek.status = request.form['status']

        if trek.status == 'completed':
            bookings = Booking.query.filter_by(trek_id=trek.id,status='booked').all()

            for booking in bookings:
                booking.status='completed'
                
        db.session.commit()

        flash("Trek updated successfully.","success")

        return redirect('/staff-dashboard')
    return render_template('staff/manage_trek.html',trek=trek)

#USER'S_BOOKING_ROUTE
@app.route('/book-trek/<int:trek_id>')
@login_required
def book_trek(trek_id):
    if current_user.role != 'user':
        return "Access Denied"

    trek = Trek.query.get_or_404(trek_id)

    #Rule 1: Trek_must_be_open
    if trek.status != 'open':
        flash("Booking not allowed. Trek is not open.",
              "danger")
        return redirect('/user-dashboard')

    #Rule 2: Prevent_overbooking
    if trek.available_slots <= 0:
        flash("No slots available for this trek.",
              "danger")

        return redirect('/user-dashboard')

    #Rule 3: Prevent duplicate booking
    existing_booking = Booking.query.filter_by(
        user_id=current_user.id,
        trek_id=trek.id,
        status='booked'
    ).first()

    if existing_booking:
        flash("You have already booked this trek.",
              "warning")

        return redirect('/user-dashboard')

    booking = Booking(
        user_id=current_user.id,
        trek_id=trek.id,
        status='booked'
    )

    db.session.add(booking)
    trek.available_slots -= 1
    db.session.commit()
    flash("Trek booked successfully.",
          "success")

    return redirect('/my-bookings')

#USER'S_MY_BOOKING_ROUTE
@app.route('/my-bookings')
@login_required
def my_bookings():

    if current_user.role != 'user':
        return "Access Denied"

    bookings = Booking.query.filter_by(user_id=current_user.id).all()

    return render_template('user/bookings.html',bookings=bookings)

#CANCEL_BOOKING_ROUTE
@app.route('/cancel-booking/<int:booking_id>')
@login_required
def cancel_booking(booking_id):

    if current_user.role != 'user':
        return "Access Denied"

    booking = Booking.query.get_or_404(booking_id)

    # Security Check
    if booking.user_id != current_user.id:
        flash("Unauthorized access.","danger")

        return redirect('/my-bookings')

    # Already cancelled
    if booking.status == 'cancelled':
        flash("Booking already cancelled.","warning")

        return redirect('/my-bookings')

    booking.status = 'cancelled'
    booking.trek.available_slots += 1

    db.session.commit()

    flash("Booking cancelled successfully.","success")

    return redirect('/my-bookings')

#STAFF's_ADD_PARTCIPANT_LIST_ROUTE
@app.route('/participants/<int:trek_id>')
@login_required
def participants(trek_id):

    if current_user.role != 'staff':
        return "Access Denied"

    trek = Trek.query.get_or_404(trek_id)

    if trek.assigned_staff_id != current_user.id:
        flash("You are not assigned to this trek.","danger")
        return redirect('/staff-dashboard')

    bookings = Booking.query.filter_by(trek_id=trek.id).all()

    return render_template(
        'staff/participants.html',trek=trek,bookings=bookings)

#ADMIN's view all BOOKING ROUTE
@app.route('/admin/bookings')
@login_required
def admin_bookings():

    if current_user.role != 'admin':
        return "Access Denied"

    bookings = Booking.query.all()

    return render_template('admin/bookings.html',bookings=bookings)

#AMDIN's User Management Page(Blacklist User/Blacklist Staff)
@app.route('/admin/users')
@login_required
def admin_users():

    if current_user.role != 'admin':
        return "Access Denied"

    users = User.query.filter(User.role != 'admin').all()

    return render_template('admin/users.html',users=users)

#ADMIN's_Blacklist Route
@app.route('/blacklist-user/<int:user_id>')
@login_required
def blacklist_user(user_id):

    if current_user.role != 'admin':
        return "Access Denied"

    user = User.query.get_or_404(user_id)

    if user.role != 'admin':
        user.status = 'blacklisted'
        db.session.commit()

        flash("Account blacklisted successfully.","warning")

    return redirect('/admin/users')

#ADMIN's_Unblock Route
@app.route('/unblacklist-user/<int:user_id>')
@login_required
def unblacklist_user(user_id):

    if current_user.role != 'admin':
        return "Access Denied"

    user = User.query.get_or_404(user_id)

    if user.role != 'admin':

        if user.role == 'staff':
            user.status = 'approved'

        elif user.role == 'user':
            user.status = 'approved'

        db.session.commit()

        flash("Account unblocked successfully.","success")

    return redirect('/admin/users')

#ADMIN_SEARCH_ROUTE
@app.route('/admin/search', methods=['GET', 'POST'])
@login_required
def admin_search():

    if current_user.role != 'admin':
        return "Access Denied"

    users = []
    treks = []

    if request.method == 'POST':

        keyword = request.form['keyword']

        # Search_by_Name
        users = User.query.filter(User.name.contains(keyword)).all()
        treks = Trek.query.filter(Trek.trek_name.contains(keyword)).all()

        # Search_by_ID: if input is numeric
        if keyword.isdigit():
            user_by_id = User.query.filter_by(id=int(keyword)).all()
            trek_by_id = Trek.query.filter_by(id=int(keyword)).all()

            users.extend(user_by_id)
            treks.extend(trek_by_id)

            # Remove_duplicate_users
            users = list(
                {user.id: user for user in users}.values())

            # Remove_duplicate_treks
            treks = list(
                {trek.id: trek for trek in treks}.values())

    return render_template('admin/search.html',users=users,treks=treks)

#USER's_TREK_HISTORY_ROUTE
@app.route('/trek-history')
@login_required
def trek_history():

    if current_user.role != 'user':
        return "Access Denied"

    history = Booking.query.join(Trek).filter(
        Booking.user_id == current_user.id,
        Trek.status == 'completed').all()

    return render_template('user/history.html',history=history )

# USER's EDIT_PROFILE ROUTE
@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():

    if current_user.role != 'user':
        return "Access Denied"

    if request.method == 'POST':

        new_email = request.form['email']

        # Check if email already belongs to another user
        existing_user = User.query.filter(
            User.email == new_email,
            User.id != current_user.id).first()

        if existing_user:
            flash("Email already exists. Please use another email.","danger")

            return redirect('/edit-profile')

        current_user.name = request.form['name']
        current_user.email = new_email
        current_user.phone = request.form['phone']

        db.session.commit()

        flash(
            "Profile updated successfully.",
            "success"
        )

        return redirect('/user-dashboard')

    return render_template('user/edit_profile.html')


if __name__ == '__main__':
    app.run(debug=True)
    

