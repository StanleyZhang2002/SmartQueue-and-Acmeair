const sqlite3 = require("sqlite3").verbose();
const db = new sqlite3.Database("./smartqueue.db");

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    queueLength INTEGER,
    waitTime REAL
  )`);
});

module.exports = db;
