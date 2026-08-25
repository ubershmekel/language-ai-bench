export type OnceSchedule = { kind: "once"; at: string };
export type IntervalSchedule = {
  kind: "interval";
  startAt: string;
  everyMinutes: number;
};
export type Schedule = OnceSchedule | IntervalSchedule;
export type Job = { id: string; name: string; schedule: Schedule };
