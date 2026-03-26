FROM python:3.12.13-slim

# Plotly needs Chromium to save PDFs and Chromium needs the following
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy our code
WORKDIR /headway-analysis
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN yes | plotly_get_chrome 

# Launch Jupyter server
EXPOSE 8888
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
