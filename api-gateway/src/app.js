const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const config = require('./config/env');
const requestId = require('./middleware/request-id');
const timeout = require('./middleware/timeout');
const rateLimiter = require('./middleware/rate-limiter');
const apiKeyAuth = require('./middleware/api-key-auth');
const errorHandler = require('./middleware/error-handler');
const summarizeRoutes = require('./routes/summarize.routes');
const healthRoutes = require('./routes/health.routes');
const docsRoutes = require('./routes/docs.routes');

const app = express();

// Security
app.use(helmet());
app.use(cors({
    origin: config.allowedOrigins.includes('*') ? '*' : config.allowedOrigins,
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'x-api-key', 'Authorization'],
    credentials: true,
}));

// Parsing
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));

// Request utilities
app.use(requestId);
app.use(timeout);

// Public routes (no auth required)
app.use('/health', healthRoutes);
app.use('/api/v1/docs', docsRoutes);

// Protected routes (rate limit + API key)
app.use('/api/v1', rateLimiter);
app.use('/api/v1', apiKeyAuth);
app.use('/api/v1/summarize', summarizeRoutes);

// Error handling
app.use(errorHandler);

module.exports = app;

