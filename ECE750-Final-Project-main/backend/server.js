// backend/server.js
const express = require("express");
const cors = require("cors");
const monitor = require("./mape/monitor");
const analyze = require("./mape/analyze");
const plan = require("./mape/plan");
const execute = require("./mape/execute");

const app = express();
app.use(cors());
app.use(express.json());

// Example API endpoints
app.get("/api/monitor", monitor.handleMonitor);
app.get("/api/analyze", analyze.handleAnalyze);
app.post("/api/plan", plan.handlePlan);
app.post("/api/execute", execute.handleExecute);

// Start server
const PORT = 5000;
app.listen(PORT, () => {
  console.log(`SmartQueue backend running on port ${PORT}`);
});
