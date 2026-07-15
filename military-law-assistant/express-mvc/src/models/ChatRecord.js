const mongoose = require('mongoose');

const ChatRecordSchema = new mongoose.Schema(
  {
    question: { type: String, required: true, trim: true },
    answer: { type: String, required: true, trim: true },
    language: {
      code: { type: String, default: 'en' },
      name: { type: String, default: 'English' }
    },
    categories: [{ type: String }],
    references: [
      {
        label: { type: String },
        source_url: { type: String },
        document_url: { type: String }
      }
    ]
  },
  { timestamps: true }
);

module.exports = mongoose.model('ChatRecord', ChatRecordSchema);
