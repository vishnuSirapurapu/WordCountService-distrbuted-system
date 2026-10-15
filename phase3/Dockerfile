# Use a lightweight Python image for the client and server containers.
FROM python:3.9-slim

# Install the Python packages required by the project.
# matplotlib and numpy are used to analyze and plot latency measurements.
RUN pip install --no-cache-dir rpyc redis matplotlib numpy

# Keep the container alive when no other command is supplied.
# Docker Compose overrides this command for the client and server.
CMD ["/bin/bash", "-c", "while true; do sleep 3600; done"]