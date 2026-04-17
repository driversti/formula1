import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles/index.css";

// If the 404 fallback redirected us with ?redirect=<path>, restore that URL
// before rendering so React Router matches the right route.
const params = new URLSearchParams(window.location.search);
const redirect = params.get("redirect");
if (redirect) {
  window.history.replaceState({}, "", redirect);
}

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("#root element missing in index.html");
}
createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
