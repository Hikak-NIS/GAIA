import { StrictMode } from "react";
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
import {
  AlertsPage,
  Irrigation,
  MapPage,
  Metrics,
  Observations,
  Overview,
  Reports,
  Simulation,
  TerritoryLayout,
} from "./Territory";
import { PlantProfiles } from "./foundation/Profiles";
import { Zones } from "./foundation/Zones";
import { Devices } from "./foundation/Devices";
import { Plants, PlantDetail } from "./foundation/Plants";
import "./styles.css";
import "./foundation/styles.css";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<AuthPage />} />
      <Route path="/register" element={<AuthPage register />} />
      <Route path="/app" element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="new" element={<NewTerritory />} />
        <Route path="profile" element={<Profile />} />
        <Route path="plant-profiles" element={<PlantProfiles />} />
        <Route path="territories/:tid" element={<TerritoryLayout />}>
          <Route index element={<Overview />} />
          <Route path="zones" element={<Zones />} />
          <Route path="devices" element={<Devices />} />
          <Route path="plants" element={<Plants />} />
          <Route path="plants/:pid" element={<PlantDetail />} />
          <Route path="map" element={<MapPage />} />
          <Route path="metrics" element={<Metrics />} />
          <Route path="simulation" element={<Simulation />} />
          <Route path="irrigation" element={<Irrigation />} />
          <Route path="observations" element={<Observations />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="reports" element={<Reports />} />
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
