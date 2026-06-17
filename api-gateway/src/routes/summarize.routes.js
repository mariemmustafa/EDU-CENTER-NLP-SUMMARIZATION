const { Router } = require('express');
const upload = require('../config/multer');
const { summarizeValidationRules, validate } = require('../middleware/validator');
const { handleSummarize } = require('../controllers/summarize.controller');

const router = Router();

router.post(
    '/',
    upload.single('file'),
    summarizeValidationRules,
    validate,
    handleSummarize
);

module.exports = router;
