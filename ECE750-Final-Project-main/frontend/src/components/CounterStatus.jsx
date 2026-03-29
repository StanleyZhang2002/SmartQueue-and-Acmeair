import { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [metrics, setMetrics] = useState({});

  useEffect(() => {
    axios.get("http://localhost:5000/api/monitor").then((res) => {
      setMetrics(res.data);
    });
  }, []);

  return (
    <div>
      <h1>SmartQueue Dashboard</h1>
      <p>Queue length: {metrics.queueLength}</p>
    </div>
  );
}

export default App;
