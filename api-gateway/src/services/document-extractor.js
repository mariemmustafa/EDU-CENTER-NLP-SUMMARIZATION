const fs = require('fs');
const path = require('path');
const pdfParse = require('pdf-parse');
const officeParser = require('officeparser');
const logger = require('../utils/logger');

/**
 * Extract text from various document formats
 * @param {string} filePath Absolute path to the file
 * @param {string} mimetype Mimetype of the file
 * @param {number} [startPage] Start page (only for PDF/PPTX)
 * @param {number} [endPage] End page (only for PDF/PPTX)
 * @returns {Promise<string>} Extracted text
 */
const extractText = async (filePath, mimetype, startPage, endPage) => {
    const extension = path.extname(filePath).toLowerCase();
    
    logger.info('Starting text extraction', { filePath, mimetype, extension });

    if (mimetype === 'application/pdf') {
        return extractFromPdf(filePath, startPage, endPage);
    }

    if (mimetype === 'text/plain' || extension === '.txt') {
        return fs.readFileSync(filePath, 'utf-8');
    }

    // DOCX, PPTX, etc. using officeparser
    try {
        const text = await new Promise((resolve, reject) => {
            officeParser.parseOffice(filePath, (data, err) => {
                if (err) return reject(err);
                resolve(data);
            });
        });
        
        // Note: officeparser doesn't support page-level extraction for PPTX/DOCX out of the box in this way,
        // so we return the full text for those for now.
        return text;
    } catch (error) {
        logger.error('Office extraction failed', { error: error.message, filePath });
        throw new Error(`Failed to extract text from office document: ${error.message}`);
    }
};

const extractFromPdf = async (filePath, startPage, endPage) => {
    const dataBuffer = fs.readFileSync(filePath);

    const options = {
        pagerender: function (pageData) {
            return pageData.getTextContent().then((textContent) => {
                const text = textContent.items.map((item) => item.str).join(' ');
                return text + '\f';
            });
        },
    };

    const data = await pdfParse(dataBuffer, options);
    const totalPages = data.numpages;

    const actualStart = startPage || 1;
    const actualEnd = endPage || totalPages;

    if (actualStart > totalPages) {
        const error = new Error(`start_page (${actualStart}) exceeds total pages (${totalPages})`);
        error.statusCode = 400;
        throw error;
    }

    const adjustedEnd = Math.min(actualEnd, totalPages);
    const allText = data.text;
    const pages = allText.split(/\f/);

    const selectedPages = pages.slice(actualStart - 1, adjustedEnd);
    const extractedText = selectedPages.join('\n');

    return extractedText;
};

module.exports = { extractText };
