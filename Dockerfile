# Use an official Python runtime as the base image
FROM python:latest

# Set the working directory in the container
WORKDIR /app
ENV PYTHONPATH=/app/src
# Copy project metadata and source for packaging
COPY pyproject.toml .
COPY src ./src

# Install the required packages
RUN pip install --no-cache-dir .

# Copy the rest of the application code into the container
COPY . .
EXPOSE 5001
CMD ["python","-u","-m","nhl_excite_o_meter"]
