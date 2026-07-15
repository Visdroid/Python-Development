const ChatRecord = require('../models/ChatRecord');

async function create(req, res) {
  try {
    const { question, answer, language, categories, references } = req.body;
    if (!question || !answer) {
      return res.status(400).json({ error: 'question and answer are required.' });
    }

    const record = await ChatRecord.create({ question, answer, language, categories, references });
    return res.status(201).json({ id: record._id, createdAt: record.createdAt });
  } catch (error) {
    console.error('[ChatController.create]', error.message);
    return res.status(500).json({ error: 'Failed to save chat record.' });
  }
}

async function list(req, res) {
  try {
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const skip = (page - 1) * limit;

    const [records, total] = await Promise.all([
      ChatRecord.find().sort({ createdAt: -1 }).skip(skip).limit(limit).lean(),
      ChatRecord.countDocuments()
    ]);

    return res.json({ total, page, limit, records });
  } catch (error) {
    console.error('[ChatController.list]', error.message);
    return res.status(500).json({ error: 'Failed to fetch chat records.' });
  }
}

async function remove(req, res) {
  try {
    const result = await ChatRecord.findByIdAndDelete(req.params.id);
    if (!result) {
      return res.status(404).json({ error: 'Record not found.' });
    }
    return res.json({ deleted: req.params.id });
  } catch (error) {
    console.error('[ChatController.remove]', error.message);
    return res.status(500).json({ error: 'Failed to delete record.' });
  }
}

module.exports = { create, list, remove };
