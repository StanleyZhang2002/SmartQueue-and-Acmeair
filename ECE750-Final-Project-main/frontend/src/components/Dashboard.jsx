import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Dashboard() {
  const [metrics, setMetrics] = useState({});

  useEffect(() => {
    axios.get("http://localhost:5000/metrics")
      .then(res => setMetrics(res.data))
      .catch(console.error);
  }, []);

  return (
    <div>
      <h1>SmartQueue Dashboard</h1>
      <p>Average Wait Time: {metrics.avg_wait_time}</p>
      <p>Queue Length: {metrics.queue_length}</p>
      <p>Policy: {metrics.policy}</p>
    </div>
  );
}
