import type { MapPoint } from "./types";

type Event = {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  date: string;
  categories: { id: string; title: string }[];
  sources: { url: string }[];
};
export type Events = { items: Event[]; note: string; fetched_at: string };
export const eventPoints = (events?: Events): MapPoint[] =>
  events?.items.map((e) => ({
    ...e,
    detail: `${e.categories.map((c) => c.title).join(", ")} · ${e.date}`,
    url: e.sources[0]?.url,
  })) ?? [];
