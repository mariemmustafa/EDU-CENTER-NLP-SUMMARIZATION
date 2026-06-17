const app = require('./src/app');
const config = require('./src/config/env');
const logger = require('./src/utils/logger');

const server = app.listen(config.port, () => {
    logger.info(`API Gateway running on port ${config.port}`, {
        environment: config.nodeEnv,
        nlpServiceUrl: config.nlpServiceUrl,
    });
});

const shutdown = (signal) => {
    logger.info(`${signal} received, shutting down gracefully`);
    server.close(() => {
        logger.info('Server closed');
        process.exit(0);
    });
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

module.exports = server;
