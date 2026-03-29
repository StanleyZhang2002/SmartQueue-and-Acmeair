// backend/mape/plan.js
exports.handlePlan = (req, res) => {
  // Later: read metrics from database or simulation
  res.json({ message: "Planning metrics done", queueLength: 5 });
};
