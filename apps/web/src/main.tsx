import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { client } from "./api";
import {
  AppLayout,
  AuthPage,
  DashboardPage,
  Landing,
  NewTerritory,
  Profile,
  Settings,
} from "./pages";
import { Observations } from "./Territory";
import { GrowLayout, GrowOverview } from "./earth/Grow";
import {
  EventsPage,
  OrganizationsPage,
  IntegrationsPage,
} from "./earth/DirectoryPages";
import { PlantProfiles } from "./foundation/Profiles";
import { Zones } from "./foundation/Zones";
import { Devices } from "./foundation/Devices";
import { Plants, PlantDetail } from "./foundation/Plants";
import { GlobalLayout } from "./global/GlobalLayout";
const GlobalPage = lazy(() => import("./earth/PlanetPage"));
const ExplorePage = lazy(() => import("./earth/ExplorePage"));
const AccessPage = lazy(() => import("./global/AccessPage"));
import "./styles.css";
import "./foundation/styles.css";
import "./earth/earth.css";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<AuthPage />} />
      <Route path="/register" element={<AuthPage register />} />
      <Route path="/global" element={<GlobalLayout />}>
        <Route
          path="territories"
          element={
            <Suspense fallback={<p>Загружаем анализ…</p>}>
              <ExplorePage key="land" />
            </Suspense>
          }
        />
        <Route
          path="ocean"
          element={
            <Suspense fallback={<p>Загружаем Ocean…</p>}>
              <ExplorePage key="ocean" ocean />
            </Suspense>
          }
        />
        <Route path="events" element={<EventsPage />} />
        <Route path="organizations" element={<OrganizationsPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route
          index
          element={
            <Suspense fallback={<p role="status">Загружаем карту…</p>}>
              <GlobalPage />
            </Suspense>
          }
        />
        <Route
          path="access"
          element={
            <Suspense
              fallback={<p role="status">Загружаем управление доступом…</p>}
            >
              <AccessPage />
            </Suspense>
          }
        />
      </Route>
      <Route path="/app" element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="new" element={<NewTerritory />} />
        <Route path="profile" element={<Profile />} />
        <Route path="plant-profiles" element={<PlantProfiles />} />
        <Route path="territories/:tid" element={<GrowLayout />}>
          <Route index element={<GrowOverview />} />
          <Route path="zones" element={<Zones />} />
          <Route path="devices" element={<Devices />} />
          <Route path="plants" element={<Plants />} />
          <Route path="plants/:pid" element={<PlantDetail />} />
          <Route path="map" element={<GrowOverview mapOnly />} />
          <Route path="metrics" element={<GrowOverview />} />
          <Route path="simulation" element={<Navigate to=".." replace />} />
          <Route
            path="irrigation"
            element={<Navigate to="../devices" replace />}
          />
          <Route path="observations" element={<Observations />} />
          <Route path="alerts" element={<Navigate to=".." replace />} />
          <Route path="reports" element={<GrowOverview />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
