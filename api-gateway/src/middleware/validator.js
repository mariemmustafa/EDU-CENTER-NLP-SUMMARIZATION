const { body, validationResult } = require('express-validator');

const summarizeValidationRules = [
    body('start_page')
        .optional()
        .isInt({ min: 1 }).withMessage('start_page must be a positive integer'),
    body('end_page')
        .optional()
        .isInt({ min: 1 }).withMessage('end_page must be a positive integer'),
    body('start_page').custom((value, { req }) => {
        if (value && req.body.end_page && parseInt(value, 10) > parseInt(req.body.end_page, 10)) {
            throw new Error('start_page must be less than or equal to end_page');
        }
        return true;
    }),
];

const validate = (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        return res.status(400).json({
            status: 'error',
            message: 'Validation failed',
            errors: errors.array().map((e) => e.msg),
        });
    }
    next();
};

module.exports = { summarizeValidationRules, validate };
