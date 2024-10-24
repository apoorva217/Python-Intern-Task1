from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models import db, User, Author, Blog  

# Initialize the Flask app
app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:Apoorva@localhost:5432/test"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'aB3dE4gH5iJ6kL7mN8oPqRsTuVwXyZ12'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize the database and JWT manager
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# Register endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data or 'is_author' not in data:
        return jsonify({'message': 'Missing username, password, or author status'}), 400
    
    username = data['username']
    password = data['password']
    is_author = data['is_author']  # Expecting a boolean

    # Checking if username already exists
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400
    
    # Creating new user
    new_user = User(username=username)
    new_user.set_password(password)  # hashing password
    db.session.add(new_user)
    db.session.commit()

    # If the user is an author, adding them to the `authors` table
    breakpoint()
    if is_author:
        new_author = Author(user_id=new_user.user_id, author_name=username)
        db.session.add(new_author)
        db.session.commit()

    return jsonify({'message': 'User registered successfully', 'is_author': is_author}), 201


# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'message': 'Missing username or password'}), 400
    
    username = data['username']
    password = data['password']
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        access_token = create_access_token(identity=user.user_id)  
        refresh_token = create_refresh_token(identity=user.user_id) 
        return jsonify({'message': 'Login Successful',
                         'access_token': access_token,
                         'refresh_token': refresh_token}), 200
    else:
        return jsonify({'message': 'Invalid username and password'}), 401

#Update Author endpoint
@app.route('/update_author', methods=['PUT'])
@jwt_required()
def update_author():
    current_user_id = get_jwt_identity()
    author = Author.query.filter_by(user_id=current_user_id).first()

    if not author:
        return jsonify({'message': 'Author not found'}), 404
    
    data = request.get_json()
    author_name = data.get('author_name')
    bio = data.get('bio')
    profile_pic = data.get('profile_pic')

    #Update author details
    if author_name:
        author.author_name = author_name
    if bio:
        author.bio = bio
    if profile_pic:
        author.profile_pic = profile_pic

    db.session.commit()
    return jsonify({'message': 'Author details updated successfully!'}), 200

@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user_id)
    return jsonify({'access_token': new_access_token}), 200

# Get user name endpoint
@app.route('/get_name', methods=['GET'])
@jwt_required()
def get_name():
    user_id = get_jwt_identity()
    user = User.query.filter_by(user_id=user_id).first() 
    if user:
        return jsonify({'message': 'User found', 'username': user.username})
    else:
        return jsonify({'message': 'User not found'}), 404
    

# Displaying all blog_posts with pagination
@app.route('/posts', methods=['GET'])
def get_posts():
    try:
        post_id = request.args.get('id', type=int)
        author = request.args.get('author', type=int)  # Ensure author is treated as an integer
        page = request.args.get('page', default=1, type=int)  # Default to page 1

        # Setting per_page to 5 to ensure 5 posts per page
        per_page = 5  

        # If the post_id is provided, return the single post
        if post_id: 
            post = Blog.query.get_or_404(post_id)  
            return jsonify({
                'blog_id': post.blog_id,  
                'title': post.title,
                'picture': post.picture,
                'description': post.description,
                'author_id': post.author_id,
                'created_at': post.created_at
            }), 200
        
        # Building the query to fetch blog posts
        query = Blog.query 
        if author:
            query = query.filter(Blog.author_id == author)

        # Implementing pagination with 5 posts per page
        posts = query.paginate(page=page, per_page=per_page, error_out=False)
        
        if not posts.items:
            return jsonify({"message": "No posts found"}), 404
        
        # Return the paginated response
        return jsonify({
            'total': posts.total,          # Total number of posts
            'page': posts.page,            # Current page number
            'per_page': posts.per_page,    # Number of posts per page
            'posts': [{
                'blog_id': post.blog_id,  
                'title': post.title,
                'picture': post.picture,
                'description': post.description,
                'author_id': post.author_id,
                'created_at': post.created_at
            } for post in posts.items]  # List of posts for the current page
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Displaying single blog_posts
@app.route('/posts/<int:post_id>', methods=['GET'])
def get_single_post(post_id):
    try:
        # Fetching the post by ID or return a 404 error if not found
        post = Blog.query.get_or_404(post_id)  
        
        # Return the post details in a consistent format
        return jsonify({
            'total': 1,  # Since it's a single post
            'posts': [{
                'blog_id': post.blog_id,  
                'title': post.title,
                'picture': post.picture,
                'description': post.description,
                'author_id': post.author_id,
                'created_at': post.created_at
            }]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Create blog post endpoint
@app.route('/posts', methods=['POST'])
@jwt_required()
def create_post():
    try:
        current_user_id = get_jwt_identity()      
        
        # Check if the user is an author
        author = db.session.query(Author).filter_by(user_id=current_user_id).first()
        
        if not author:  # Only authors can create posts
            return jsonify({"message": "You are not authorized to create a post"}), 403

        data = request.get_json()

        # Validate required fields in the request
        if not data or 'title' not in data or 'picture' not in data or 'description' not in data:
            return jsonify({"message": "Missing required fields"}), 400

        # Create a new blog post
        new_post = Blog(
            title=data.get('title'),
            picture=data.get('picture'),
            description=data.get('description'),
            author_id=author.author_id,  # Use author_id from the Author table
            created_at=datetime.now() 
        )
        db.session.add(new_post)
        db.session.commit()  # Commit the transaction to the database
        return jsonify({"message": "Post created successfully!"}), 201  # Return success response
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Return error response in case of failure

    
# Update blog post endpoint
@app.route('/posts/<int:id>', methods=['PUT'])
@jwt_required()
def update_post(id):
    try:
        # Fetch the post by ID
        post = Blog.query.get_or_404(id)
        current_user_id = get_jwt_identity()

        author = Author.query.filter_by(user_id=current_user_id).first()

        # Check if the current user is the author of the post
        if not author or post.author_id != author.author_id:
            return jsonify({"message": "You are not authorized to update this post"}), 403
            
        # Get the data from the request
        data = request.get_json()

        # Check if the current user is an author
        author = db.session.query(Author).filter_by(user_id=current_user_id).first()
        
        # Debugging prints
        print(f"Current User ID: {current_user_id}")
        print(f"Post Author ID: {post.author_id}")
        print(f"Is Author: {author}")


        # Validate required fields
        if not data or 'title' not in data or 'picture' not in data or 'description' not in data:
            return jsonify({"message": "Missing required fields"}), 400

        # Update the post details
        post.title = data['title']
        post.picture = data['picture']
        post.description = data['description']
        
        # Commit the changes to the database
        db.session.commit()
        return jsonify({"message": "Post updated successfully!"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Delete blog post endpoint
@app.route('/posts/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_post(id):
    try:
        # Fetch the post by ID
        post = Blog.query.get_or_404(id)
        current_user_id = get_jwt_identity()

        # Fetch the current user's author record
        author = db.session.query(Author).filter_by(user_id=current_user_id).first()

        # Check if the author exists and if they are the owner of the post
        if not author or post.author_id != author.author_id:
            return jsonify({"message": "You are not authorized to delete this post"}), 403
        
        # Delete the post
        db.session.delete(post)
        db.session.commit()
        return jsonify({"message": "Post deleted successfully!"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({"message": "Logged out successfully."}), 200

if __name__ == '__main__':
    app.run(debug=True)
