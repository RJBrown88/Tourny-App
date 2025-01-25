# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Create the instance folder if it doesn't exist
RUN mkdir -p instance

# Set permissions for the SQLite database file (if it exists)
RUN chmod 666 /app/instance/tournament.db || echo "Database file not found, permissions not set."

# Expose port 5000 (Flask's default port)
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run the Flask application
CMD ["flask", "run", "--host=0.0.0.0"]