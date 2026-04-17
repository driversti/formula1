import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Home from "./routes/Home";
import Driver from "./routes/Driver";
import NotFound from "./routes/NotFound";

// When deployed at a subpath (e.g. /formula1/ on GitHub Pages) the router
// must strip that prefix before matching — otherwise every URL falls through
// to <NotFound />. import.meta.env.BASE_URL is provided by Vite.
// basename must not have a trailing slash.
const basename = import.meta.env.BASE_URL.replace(/\/$/, "");

const router = createBrowserRouter(
  [
    { path: "/", element: <Home /> },
    { path: "/driver/:tla", element: <Driver />, errorElement: <NotFound /> },
    { path: "*", element: <NotFound /> },
  ],
  { basename: basename || "/" },
);

export default function App() {
  return <RouterProvider router={router} />;
}
