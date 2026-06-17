const config = require('../config/env');
const logger = require('../utils/logger');

const apiKeyAuth = (req, res, next) => {
    // Skip auth if no API key is configured (development mode)
    if (!config.apiKey) {
        return next();
    }

    const providedKey = req.headers['x-api-key'];

    if (!providedKey) {
        logger.warn('Missing API key', {
            ip: req.ip,
            path: req.path,
            requestId: req.id,
        });
        return res.status(401).json({
            status: 'error',
            message: 'API key is required. Provide it via the x-api-key header.',
        });
    }

    if (providedKey !== config.apiKey) {
        logger.warn('Invalid API key', {
            ip: req.ip,
            path: req.path,
            requestId: req.id,
        });
        return res.status(403).json({
            status: 'error',
            message: 'Invalid API key.',
        });
    }

    next();
};

module.exports = apiKeyAuth;
