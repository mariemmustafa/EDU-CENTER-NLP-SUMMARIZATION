const { createLogger, format, transports } = require('winston');
const config = require('../config/env');

const logger = createLogger({
    level: config.logLevel,
    format: format.combine(
        format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
        format.errors({ stack: true }),
        format.json()
    ),
    defaultMeta: { service: 'api-gateway' },
    transports: [
        new transports.Console({
            format: config.nodeEnv === 'development'
                ? format.combine(format.colorize(), format.simple())
                : format.json(),
        }),
    ],
});

module.exports = logger;
