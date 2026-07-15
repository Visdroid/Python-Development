const mongoose = require('mongoose');

const ResourceClickSchema = new mongoose.Schema(
  {
    label: { type: String, trim: true, default: 'External link' },
    url: { type: String, required: true, trim: true }
  },
  { timestamps: true }
);

module.exports = mongoose.model('ResourceClick', ResourceClickSchema);
