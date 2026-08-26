export interface OnceSchedule {
  kind: "once";
  at: string;
}

export type Schedule = OnceSchedule;

export interface Job {
  id: string;
  name: string;
  schedule: Schedule;
}
