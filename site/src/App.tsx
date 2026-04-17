import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import Seasons from "./routes/Seasons";
import Season from "./routes/Season";
import Race from "./routes/Race";
import Tyres from "./routes/Tyres";
import Driver from "./routes/Driver";
import Legal from "./routes/Legal";
import NotFound from "./routes/NotFound";

const basename = import.meta.env.BASE_URL.replace(/\/$/, "");

const router = createBrowserRouter(
  [
    {
      element: <AppShell />,
      children: [
        { path: "/", element: <Seasons /> },
        { path: "/season/:year", element: <Season />, errorElement: <NotFound /> },
        { path: "/race/:slug", element: <Race />, errorElement: <NotFound /> },
        { path: "/race/:slug/tyres", element: <Tyres />, errorElement: <NotFound /> },
        { path: "/race/:slug/driver/:tla", element: <Driver />, errorElement: <NotFound /> },
        { path: "/legal", element: <Legal /> },
        { path: "*", element: <NotFound /> },
      ],
    },
  ],
  { basename: basename || "/" },
);

export default function App() {
  return <RouterProvider router={router} />;
}
