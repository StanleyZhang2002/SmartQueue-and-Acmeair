// backend/mape/monitor.js
const db = require("../db/database");
exports.handleMonitor = (req, res) => {
  // Later: read metrics from database or simulation
  res.json({ message: "Monitoring metrics collected", queueLength: 5 });
};
