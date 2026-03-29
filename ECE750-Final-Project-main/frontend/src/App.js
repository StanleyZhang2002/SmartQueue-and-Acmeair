import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import CounterStatus from "./components/CounterStatus";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<CounterStatus />} />
      </Routes>
    </Router>
  );
}

export default App;
