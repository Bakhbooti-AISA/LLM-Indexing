const express = require("express");
const router = express.Router();
const connectToDatabase = require("../db");

router.get("/", async (req, res) => {
  const { db } = await connectToDatabase();
  const articles = await db.collection("articles").find({}, { projection: { _id: 1, title: 1 } }).toArray();
  res.json(articles.map(a => ({ id: a._id, title: a.title })));
});

router.get("/:id", async (req, res) => {
  const { db } = await connectToDatabase();
  const article = await db.collection("articles").findOne({ _id: req.params.id });
  if (!article) return res.status(404).json({ message: "Not found" });
  res.json(article);
});

module.exports = router;
