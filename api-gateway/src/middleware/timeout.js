const config = require('../config/env');

const timeout = (req, res, next) => {
    const timer = setTimeout(() => {
        if (!res.headersSent) {
            res.status(504).json({
                status: 'error',
                message: 'Request timed out',
            });
        }
    }, config.requestTimeoutMs);

    res.on('finish', () => clearTimeout(timer));
    res.on('close', () => clearTimeout(timer));
    next();
};

module.exports = timeout;
