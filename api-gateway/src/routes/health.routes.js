const { Router } = require('express');

const router = Router();

router.get('/', (_req, res) => {
    res.json({
        status: 'healthy',
        service: 'api-gateway',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
    });
});

module.exports = router;
