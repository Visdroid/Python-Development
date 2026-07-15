const mongoose = require('mongoose');

async function connectDatabase() {
  const mongoUri = process.env.MONGODB_URI;
  if (!mongoUri) {
    throw new Error('MONGODB_URI is required.');
  }

  await mongoose.connect(mongoUri, {
    autoIndex: true
  });
}

module.exports = { connectDatabase };
