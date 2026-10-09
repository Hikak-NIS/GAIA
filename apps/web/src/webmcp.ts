import { api, client, endpoint } from "./api";
import type { Dashboard, Rule } from "./types";

type ToolDefinition = {
  name: string;
  title: string;
  description: string;
  inputSchema: Record<string, unknown>;
  annotations: { readOnlyHint: boolean; untrustedContentHint: boolean };
  execute(input: unknown): unknown | Promise<unknown>;
};

declare global {
  interface Document {
    readonly modelContext?: {
      registerTool(
        tool: ToolDefinition,
        options?: { signal?: AbortSignal },
      ): void | Promise<void>;
    };
  }
}

export function registerGaiaTools(territoryId: string) {
  const context = document.modelContext;
  if (!context?.registerTool) return () => undefined;
  const lifecycle = new AbortController();
  const register = (tool: ToolDefinition) => {
    void Promise.resolve(
      context.registerTool(tool, { signal: lifecycle.signal }),
    ).catch(() => undefined);
  };

  register({
    name: "read_gaia_territory_status",
    title: "Прочитать состояние территории",
    description:
      "Возвращает текущие показатели, состояние симуляции, насоса и активные причины предупреждений.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, untrustedContentHint: false },
    async execute() {
      const dashboard = await api<Dashboard>(
        endpoint(territoryId, "dashboard"),
      );
      return {
        territory: dashboard.territory.name,
        status: dashboard.status,
        soilMoisturePct: dashboard.reading?.soil_moisture_pct ?? null,
        pumpOn: dashboard.zone.pump_on,
        reservoirLiters: dashboard.simulation.reservoir_l,
        alertReasons: dashboard.reasons,
      };
    },
  });

  register({
    name: "start_gaia_drought_demo",
    title: "Запустить демонстрацию засухи",
    description:
      "Настраивает безопасный автополив с порогом 30% и целью 45%, затем запускает симуляцию засухи ×60.",
    inputSchema: {
      type: "object",
      properties: {
        seed: { type: "integer", minimum: 0, maximum: 2147483647, default: 42 },
      },
      additionalProperties: false,
    },
    annotations: { readOnlyHint: false, untrustedContentHint: false },
    async execute(input) {
      const value =
        typeof input === "object" && input !== null && "seed" in input
          ? (input as { seed?: unknown }).seed
          : 42;
      const seed =
        typeof value === "number" &&
        Number.isInteger(value) &&
        value >= 0 &&
        value <= 2147483647
          ? value
          : 42;
      const rule: Rule = {
        mode: "automatic",
        trigger_pct: 30,
        target_pct: 45,
        max_duration_s: 1200,
        cooldown_s: 1800,
        daily_limit_l: 30,
        min_reservoir_l: 5,
        block_rain: false,
        rain_threshold_pct: 60,
      };
      await api(endpoint(territoryId, "irrigation/rules"), "PUT", rule);
      await api(endpoint(territoryId, "simulations"), "POST", {
        action: "start",
        scenario: "drought",
        speed: 60,
        seed,
      });
      await client.invalidateQueries({ queryKey: ["dashboard", territoryId] });
      return {
        started: true,
        scenario: "drought",
        speed: 60,
        seed,
        triggerPct: 30,
        targetPct: 45,
      };
    },
  });
  return () => lifecycle.abort();
}
