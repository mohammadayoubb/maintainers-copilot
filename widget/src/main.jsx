import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

// This is the React entrypoint for the standalone widget.
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
