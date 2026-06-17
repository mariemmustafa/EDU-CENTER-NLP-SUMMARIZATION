const dotenv = require('dotenv');
const path = require('path');

dotenv.config({ path: path.resolve(__dirname, '../../.env') });

const config = {
  port: parseInt(process.env.PORT, 10) || 3000,
  nlpServiceUrl: process.env.NLP_SERVICE_URL || 'http://localhost:8000',
  maxFileSizeMb: parseInt(process.env.MAX_FILE_SIZE_MB, 10) || 10,
  logLevel: process.env.LOG_LEVEL || 'info',
  requestTimeoutMs: parseInt(process.env.REQUEST_TIMEOUT_MS, 10) || 30000,
  nodeEnv: process.env.NODE_ENV || 'development',
  allowedOrigins: process.env.ALLOWED_ORIGINS
    ? process.env.ALLOWED_ORIGINS.split(',').map((s) => s.trim())
    : ['*'],
  apiKey: process.env.API_KEY || '',
  rateLimitWindowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS, 10) || 60000,
  rateLimitMax: parseInt(process.env.RATE_LIMIT_MAX, 10) || 30,
};

module.exports = config;

