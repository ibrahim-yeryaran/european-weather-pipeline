# Custom Airflow image with our Python dependencies baked in.
# Building deps into the image (instead of installing them at container
# startup) makes startup fast and the environment reproducible.

FROM apache/airflow:2.9.1

# Copy only the requirements first. Docker caches this layer, so deps are
# re-installed ONLY when requirements.txt changes — not on every code edit.
COPY requirements.txt /requirements.txt

# The base image runs as the 'airflow' user; pip installs into its environment.
RUN pip install --no-cache-dir -r /requirements.txt
