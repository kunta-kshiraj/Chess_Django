# FROM python:3.12.6
# COPY requirements.txt ./
# RUN pip3 install --user -r requirements.txt
# COPY . ./
# RUN chmod +x docker_run_server.sh
# EXPOSE 80
# ENTRYPOINT ["/bin/sh", "./docker_run_server.sh"]

# Use the official Python base image
FROM python:3.12.6
# Install Redis server and supervisord
RUN apt-get update && apt-get install -y \
redis-server \
supervisor \
&& rm -rf /var/lib/apt/lists/*
# Set the working directory
WORKDIR /app
# Copy the requirements file
COPY requirements.txt /app/
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the application code
COPY . /app
# Make the docker_run_server.sh script executable
RUN chmod +x docker_run_server.sh
# Copy the supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
# Expose the port Daphne will run on
EXPOSE 80
# Set the entrypoint to your existing script
ENTRYPOINT ["./docker_run_server.sh"]