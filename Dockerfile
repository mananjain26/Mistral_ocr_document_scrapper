# Use the latest Python (or 3.12 if needed)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
COPY . .

# Install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Streamlit config (optional)
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_PORT=7860

# Expose Streamlit port
EXPOSE 7860

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.enableCORS=false"]
