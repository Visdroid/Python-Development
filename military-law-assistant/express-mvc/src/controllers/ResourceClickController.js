const ResourceClick = require('../models/ResourceClick');

async function create(req, res) {
  try {
    const { label, url } = req.body;
    if (!url) {
      return res.status(400).json({ error: 'url is required.' });
    }

    const record = await ResourceClick.create({ label, url });
    return res.status(201).json({ id: record._id, createdAt: record.createdAt });
  } catch (error) {
    console.error('[ResourceClickController.create]', error.message);
    return res.status(500).json({ error: 'Failed to save resource click.' });
  }
}

async function list(req, res) {
  try {
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const skip = (page - 1) * limit;

    const [records, total] = await Promise.all([
      ResourceClick.find().sort({ createdAt: -1 }).skip(skip).limit(limit).lean(),
      ResourceClick.countDocuments()
    ]);

    return res.json({ total, page, limit, records });
  } catch (error) {
    console.error('[ResourceClickController.list]', error.message);
    return res.status(500).json({ error: 'Failed to fetch resource clicks.' });
  }
}

module.exports = { create, list };
