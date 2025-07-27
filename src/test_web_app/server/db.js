// /api/db.js
const { MongoClient } = require("mongodb");
require("dotenv").config();


const uri = process.env.MONGODB_URI;
let cachedClient = null;
let cachedDb = null;

module.exports = async function connectToDatabase() {
  if (cachedClient && cachedDb) {
    return { client: cachedClient, db: cachedDb };
  }

  const client = new MongoClient(uri);
  await client.connect();

  const db = client.db(); // default DB in URI
  cachedClient = client;
  cachedDb = db;

  return { client, db };
};
