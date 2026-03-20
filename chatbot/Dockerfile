# Rasa Server Dockerfile
FROM rasa/rasa:3.6.20

# Set working directory
WORKDIR /app

# Copy Rasa project files
COPY config.yml .
COPY domain.yml .
COPY credentials.yml .
COPY endpoints.yml .
COPY data/ ./data/

# Copy the trained model
# NOTE: You must ensure the models/ folder has at least one model
COPY models/ ./models/

# Expose Rasa port
EXPOSE 5005

# Run Rasa server with CORS enabled for all origins
CMD ["run", "--enable-api", "--cors", "*", "--port", "5005"]
