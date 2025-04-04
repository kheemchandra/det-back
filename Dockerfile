FROM python:3.11

# Install dependencies for building SQLite
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install newer version of SQLite
WORKDIR /tmp
RUN wget https://www.sqlite.org/2023/sqlite-autoconf-3420000.tar.gz \
    && tar -xzf sqlite-autoconf-3420000.tar.gz \
    && cd sqlite-autoconf-3420000 \
    && ./configure --prefix=/usr/local \
    && make \
    && make install \
    && cd .. \
    && rm -rf sqlite-autoconf-3420000* \
    && ldconfig

# Set environment variables for SQLite
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
ENV PATH=/usr/local/bin:$PATH

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV APP_HOME /root
WORKDIR $APP_HOME

# Copy all your application files to the working directory
COPY . $APP_HOME/

EXPOSE 8080
# Adjust this command to point to your main application file
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
