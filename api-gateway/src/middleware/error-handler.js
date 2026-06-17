const logger = require('../utils/logger');
const { deleteFile } = require('../utils/file-cleanup');

const errorHandler = (err, req, res, _next) => {
    if (req.file) {
        deleteFile(req.file.path);
    }

    const statusCode = err.statusCode || 500;
    const message = statusCode === 500 ? 'Internal server error' : err.message;

    logger.error('Request failed', {
        requestId: req.id,
        statusCode,
        error: err.message,
        stack: err.stack,
        path: req.path,
        method: req.method,
    });

    if (!res.headersSent) {
        res.status(statusCode).json({
            status: 'error',
            message,
            requestId: req.id,
        });
    }
};

module.exports = errorHandler;
