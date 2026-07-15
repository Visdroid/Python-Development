const mongoose = require('mongoose');

function health(req, res) {
  const dbState = ['disconnected', 'connected', 'connecting', 'disconnecting'];
  res.json({
    status: 'ok',
    service: 'military-law-assistant-express-mvc',
    db: dbState[mongoose.connection.readyState] || 'unknown',
    timestamp: new Date().toISOString()
  });
}

module.exports = { health };
