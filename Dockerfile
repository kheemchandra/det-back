FROM python:3.11.3 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV APP_HOME /root
WORKDIR $APP_HOME

# Copy all your application files to the working directory
COPY . $APP_HOME/

EXPOSE 8080
# Adjust this command to point to your main application file
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
