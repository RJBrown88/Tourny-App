from app import app, db, User
from werkzeug.security import generate_password_hash

# Create an application context
with app.app_context():
    # Delete the existing admin user (if it exists)
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user:
        db.session.delete(admin_user)
        db.session.commit()
        print("Existing admin user deleted.")

    # Create a new admin user with the correct hashed password
    hashed_password = generate_password_hash('42465freszrd')
    admin_user = User(username='admin', password=hashed_password, role='admin')

    # Add to the database
    db.session.add(admin_user)
    db.session.commit()

    print("Admin user created successfully!")