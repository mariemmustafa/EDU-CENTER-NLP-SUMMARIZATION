const { Router } = require('express');

const router = Router();

const apiSpec = {
    openapi: '3.0.3',
    info: {
        title: 'Text Summarization API',
        version: '1.0.0',
        description:
            'API Gateway for the Text Summarization Platform. Upload a PDF and get a summary of selected pages.',
    },
    servers: [
        { url: '/api/v1', description: 'API v1' },
    ],
    paths: {
        '/summarize': {
            post: {
                summary: 'Summarize PDF pages',
                description:
                    'Upload a PDF file and specify a page range to receive a summarized version of the content.',
                security: [{ ApiKeyAuth: [] }],
                requestBody: {
                    required: true,
                    content: {
                        'multipart/form-data': {
                            schema: {
                                type: 'object',
                                required: ['file', 'start_page', 'end_page'],
                                properties: {
                                    file: {
                                        type: 'string',
                                        format: 'binary',
                                        description: 'PDF file to summarize',
                                    },
                                    start_page: {
                                        type: 'integer',
                                        minimum: 1,
                                        description: 'First page to include',
                                    },
                                    end_page: {
                                        type: 'integer',
                                        minimum: 1,
                                        description: 'Last page to include',
                                    },
                                },
                            },
                        },
                    },
                },
                responses: {
                    200: {
                        description: 'Summarization successful',
                        content: {
                            'application/json': {
                                schema: {
                                    type: 'object',
                                    properties: {
                                        status: { type: 'string', example: 'success' },
                                        request_id: { type: 'string' },
                                        original_length: { type: 'integer' },
                                        summary_length: { type: 'integer' },
                                        compression_ratio: { type: 'number' },
                                        summary_text: { type: 'string' },
                                    },
                                },
                            },
                        },
                    },
                    400: { description: 'Validation error or invalid file' },
                    401: { description: 'Missing API key' },
                    403: { description: 'Invalid API key' },
                    422: { description: 'No text found in selected pages' },
                    429: { description: 'Rate limit exceeded' },
                    500: { description: 'Internal server error' },
                },
            },
        },
        '/docs': {
            get: {
                summary: 'API Documentation',
                description: 'Returns this OpenAPI specification',
                responses: {
                    200: { description: 'OpenAPI JSON spec' },
                },
            },
        },
    },
    components: {
        securitySchemes: {
            ApiKeyAuth: {
                type: 'apiKey',
                in: 'header',
                name: 'x-api-key',
            },
        },
    },
};

router.get('/', (_req, res) => {
    res.json(apiSpec);
});

module.exports = router;
