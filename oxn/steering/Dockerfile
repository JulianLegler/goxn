FROM python:3.12-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    iproute2 \
    stress-ng


# Install general dependencies
RUN pip install flask requests

# Copy the application
COPY . /app
WORKDIR /app


# Run the application
CMD ["python", "steering_container.py"]

# Expose the port
EXPOSE 5000

