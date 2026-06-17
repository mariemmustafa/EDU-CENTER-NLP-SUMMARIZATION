const { extractText } = require('../services/document-extractor');
const { cleanText } = require('../services/text-cleaner');
const { summarize } = require('../services/nlp-client');
const { deleteFile } = require('../utils/file-cleanup');
const logger = require('../utils/logger');

const handleSummarize = async (req, res, next) => {
    const { file } = req;
    const startPage = req.body.start_page ? parseInt(req.body.start_page, 10) : undefined;
    const endPage = req.body.end_page ? parseInt(req.body.end_page, 10) : undefined;

    try {
        if (!file) {
            const error = new Error('Document file is required');
            error.statusCode = 400;
            throw error;
        }

        logger.info('Summarization started', {
            requestId: req.id,
            fileName: file.originalname,
            fileSize: file.size,
            mimetype: file.mimetype,
            startPage,
            endPage,
        });

        const rawText = await extractText(file.path, file.mimetype, startPage, endPage);
        const cleanedText = cleanText(rawText);

        if (!cleanedText.length) {
            const error = new Error('No text content found in the document');
            error.statusCode = 422;
            throw error;
        }

        const result = await summarize(cleanedText, req.id);

        logger.info('Summarization completed', {
            requestId: req.id,
            originalLength: result.original_length,
            summaryLength: result.summary_length,
        });

        res.json({
            status: 'success',
            request_id: req.id,
            ...result,
        });
    } catch (error) {
        next(error);
    } finally {
        deleteFile(file?.path);
    }
};

module.exports = { handleSummarize };
