FROM bengreenier/docker-xvfb:stable
WORKDIR /app/ChatGPTBot
COPY ./../*.py .
RUN apt-get update -y \
  && apt-get install --no-install-recommends -y mesa-utils python3-pip git build-essential \
  && rm -rf /var/lib/apt/lists/* \
  && pip3 install --compile httpx[socks] toml emoji loguru \
  && pip3 install git+http://github.com/acheong08/ChatGPT.git \
  && python3 -m playwright install \
