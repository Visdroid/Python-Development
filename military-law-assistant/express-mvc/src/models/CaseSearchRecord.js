const mongoose = require('mongoose');

const CaseSearchRecordSchema = new mongoose.Schema(
  {
    query: { type: String, required: true, trim: true },
    source: { type: String, default: null },
    resultsCount: { type: Number, default: 0 }
  },
  { timestamps: true }
);

module.exports = mongoose.model('CaseSearchRecord', CaseSearchRecordSchema);
