import { useState } from "react";
import Welcome from "./pages/Welcome";
import Home from "./pages/Home";

export default function App() {
  const [showWelcome, setShowWelcome] = useState(true);

  if (showWelcome) {
    return <Welcome onEnter={() => setShowWelcome(false)} />;
  }

  return <Home />;
}