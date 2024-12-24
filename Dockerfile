# Use a Python base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy project files to the container
COPY . /app

# Ensure necessary directories exist
RUN mkdir -p logs data .secrets

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
	
# Install necessary system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1 \
    fonts-liberation \
    && apt-get clean

RUN apt-get install -y \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxtst6 \
    libxrandr2 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2

# Install Rust for building Python dependencies with native Rust extensions
RUN apt-get update && apt-get install -y curl && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    . $HOME/.cargo/env && rustup update stable

# Persist Rust environment
ENV PATH="/root/.cargo/bin:$PATH"

	
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Expose a port for OAuth redirect
EXPOSE 8080

# Define the default command to run your app
CMD ["python", "-u", "-W", "ignore", "main.py"]
