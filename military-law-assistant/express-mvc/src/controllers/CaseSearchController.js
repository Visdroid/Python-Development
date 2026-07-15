const CaseSearchRecord = require('../models/CaseSearchRecord');

async function create(req, res) {
  try {
    const { query, source, resultsCount } = req.body;
    if (!query) {
      return res.status(400).json({ error: 'query is required.' });
    }

    const record = await CaseSearchRecord.create({ query, source, resultsCount });
    return res.status(201).json({ id: record._id, createdAt: record.createdAt });
  } catch (error) {
    console.error('[CaseSearchController.create]', error.message);
    return res.status(500).json({ error: 'Failed to save case search record.' });
  }
}

async function list(req, res) {
  try {
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const skip = (page - 1) * limit;

    const [records, total] = await Promise.all([
      CaseSearchRecord.find().sort({ createdAt: -1 }).skip(skip).limit(limit).lean(),
      CaseSearchRecord.countDocuments()
    ]);

    return res.json({ total, page, limit, records });
  } catch (error) {
    console.error('[CaseSearchController.list]', error.message);
    return res.status(500).json({ error: 'Failed to fetch case search records.' });
  }
}

module.exports = { create, list };
