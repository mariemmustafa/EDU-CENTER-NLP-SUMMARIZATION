const axios = require('axios');
const FormData = require('form-data');
const config = require('../config/env');
const logger = require('../utils/logger');

const nlpClient = axios.create({
    baseURL: config.nlpServiceUrl,
    timeout: config.requestTimeoutMs - 2000,
});

const summarize = async (text, requestId) => {
    logger.info('Sending text as file to NLP service', {
        requestId,
        textLength: text.length,
    });

    const startTime = Date.now();
    
    const formData = new FormData();
    // Simulate a file upload from the extracted text
    formData.append('file', Buffer.from(text, 'utf-8'), {
        filename: 'document.txt',
        contentType: 'text/plain'
    });
    
    if (requestId) {
        formData.append('request_id', requestId);
    }

    const response = await nlpClient.post('/api/v1/summarize', formData, {
        headers: formData.getHeaders()
    });

    const duration = Date.now() - startTime;

    logger.info('NLP service responded', {
        requestId,
        durationMs: duration,
        summaryLength: response.data.summary_length,
    });

    return response.data;
};

module.exports = { summarize };
