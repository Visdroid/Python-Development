require('dotenv').config();
const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const { connectDatabase } = require('./config/db');

const healthRouter = require('./routes/health');
const chatsRouter = require('./routes/chats');
const caseSearchesRouter = require('./routes/caseSearches');
const resourceClicksRouter = require('./routes/resourceClicks');

const app = express();

// Allow Flask frontend (and any configured origin) to call this API
const allowedOrigins = (process.env.CORS_ORIGIN || 'http://127.0.0.1:5000').split(',').map(o => o.trim());
app.use(cors({
  origin: (origin, callback) => {
    if (!origin || allowedOrigins.includes(origin)) {
      return callback(null, true);
    }
    callback(new Error(`CORS: origin ${origin} is not allowed`));
  },
  methods: ['GET', 'POST', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json({ limit: '1mb' }));
app.use(morgan('dev'));

// Routes — all mounted under /api
app.use('/api/health', healthRouter);
app.use('/api/chats', chatsRouter);
app.use('/api/case-searches', caseSearchesRouter);
app.use('/api/resource-clicks', resourceClicksRouter);

// 404 catch-all
app.use((req, res) => {
  res.status(404).json({ error: `Route ${req.method} ${req.path} not found.` });
});

// Global error handler
app.use((err, req, res, _next) => {
  console.error('[GlobalError]', err.message);
  res.status(500).json({ error: err.message || 'Internal server error.' });
});

const PORT = parseInt(process.env.PORT || '4000', 10);

(async () => {
  try {
    await connectDatabase();
    console.log('[DB] Connected to MongoDB');
    app.listen(PORT, () => {
      console.log(`[Server] Express MVC running on http://localhost:${PORT}`);
      console.log(`[Health] http://localhost:${PORT}/api/health`);
    });
  } catch (err) {
    console.error('[Startup] Failed:', err.message);
    process.exit(1);
  }
})();
