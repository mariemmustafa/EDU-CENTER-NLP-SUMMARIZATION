const cleanText = (rawText) => {
    if (!rawText || typeof rawText !== 'string') {
        return '';
    }

    return rawText
        .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .replace(/[ \t]+/g, ' ')
        .replace(/\n{3,}/g, '\n\n')
        .replace(/^ +| +$/gm, '')
        .trim();
};

module.exports = { cleanText };
