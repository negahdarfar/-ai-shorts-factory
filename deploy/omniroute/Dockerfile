FROM node:22-bookworm-slim

ENV NODE_ENV=production \
    DATA_DIR=/data \
    PORT=20128

RUN npm install --global omniroute@latest \
    && npm cache clean --force

WORKDIR /data
VOLUME ["/data"]
EXPOSE 20128

CMD ["omniroute", "--port", "20128", "--no-open"]
