import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Home from "./routes/Home";
import Driver from "./routes/Driver";
import NotFound from "./routes/NotFound";

const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/driver/:tla", element: <Driver />, errorElement: <NotFound /> },
  { path: "*", element: <NotFound /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
