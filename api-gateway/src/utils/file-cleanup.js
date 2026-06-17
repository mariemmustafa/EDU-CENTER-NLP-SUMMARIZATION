const fs = require('fs');
const logger = require('./logger');

const deleteFile = (filePath) => {
    if (!filePath) return;

    fs.unlink(filePath, (err) => {
        if (err && err.code !== 'ENOENT') {
            logger.warn('Failed to delete temp file', { filePath, error: err.message });
        } else {
            logger.debug('Temp file deleted', { filePath });
        }
    });
};

module.exports = { deleteFile };
