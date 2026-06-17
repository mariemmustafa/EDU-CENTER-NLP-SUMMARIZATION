const rateLimit = require('express-rate-limit');
const config = require('../config/env');
const logger = require('../utils/logger');

const limiter = rateLimit({
    windowMs: config.rateLimitWindowMs,
    max: config.rateLimitMax,
    standardHeaders: true,
    legacyHeaders: false,
    message: {
        status: 'error',
        message: 'Too many requests, please try again later.',
    },
    handler: (req, res, next, options) => {
        logger.warn('Rate limit exceeded', {
            ip: req.ip,
            requestId: req.id,
        });
        res.status(options.statusCode).json(options.message);
    },
    skip: (_req) => config.nodeEnv === 'development' && config.rateLimitMax === 0,
});

module.exports = limiter;
