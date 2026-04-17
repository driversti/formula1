import { Outlet } from "react-router-dom";
import { SiteHeader } from "./SiteHeader";
import { SiteFooter } from "./SiteFooter";

export function AppShell() {
  return (
    <>
      <SiteHeader />
      <Outlet />
      <SiteFooter />
    </>
  );
}
