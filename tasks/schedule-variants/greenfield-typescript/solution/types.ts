export interface OnceSchedule {
  kind: "once";
  at: string;
}

export interface IntervalSchedule {
  kind: "interval";
  startAt: string;
  everyMinutes: number;
}

export type Schedule = OnceSchedule | IntervalSchedule;

export interface Job {
  id: string;
  name: string;
  schedule: Schedule;
}
