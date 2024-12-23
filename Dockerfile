# Use a Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy project files to the container
COPY . /app

# Ensure necessary directories exist
RUN mkdir -p logs data

# Debug Python and pip versions
RUN python --version
RUN pip --version

# Check the contents of requirements.txt
RUN cat requirements.txt

# upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
	rustc \
    cargo \
	curl \
    && apt-get clean
	


# Install Rust for building Python dependencies with native Rust extensions
RUN apt-get update && apt-get install -y curl && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    source $HOME/.cargo/env && rustup update stable
	
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Expose a port if your app provides a web interface (e.g., Flask, FastAPI)
# EXPOSE 8080

# Define the default command to run your app
CMD ["python", "main.py"]
