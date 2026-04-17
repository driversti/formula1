import { Outlet } from "react-router-dom";
import { SiteHeader } from "./SiteHeader";

export function AppShell() {
  return (
    <>
      <SiteHeader />
      <Outlet />
    </>
  );
}
